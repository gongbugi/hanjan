"""F4 추천 — RAG.

검색(Retrieval): 내 높은 평가 기록으로 취향 벡터를 만들고, SQL 필터 + pgvector 코사인 거리로 후보를 찾는다.
증강(Augmented): 후보와 근거 기록을 프롬프트에 넣는다.
생성(Generation): LLM은 추천 이유 문장만 쓴다.
검증: 이유가 인용한 기록 id가 실제 근거 목록에 있는지 코드가 확인하고, 아니면 템플릿 문장으로 바꾼다.
"""

import math
from collections import Counter
from dataclasses import dataclass, field
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hanjan.embedding.base import Embedder
from hanjan.flavor import label_of
from hanjan.grind.calibration import suggest_clicks
from hanjan.llm import prompts
from hanjan.llm.base import LLM, LLMError
from hanjan.llm.schemas import ReasonBatch
from hanjan.models import Bean, Brew, CatalogBean, Document, GrindMeasurement, RecommendationSnapshot
from hanjan.services.grind import calibration_for

HIGH_RATING = 4
MAX_REASON_CHARS = 300
EVIDENCE_PER_CANDIDATE = 3


def _doc_on(model, kind: str, model_id: str):
    """문서 조인 조건. 세 곳에서 같은 조건을 쓴다 — model_id를 빠뜨리면 다른 모델의 벡터와 섞인다."""
    return (Document.kind == kind) & (Document.ref_id == model.id) & (Document.model_id == model_id)


def _normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _cosine(a: list[float], b: list[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b, strict=True)))  # 둘 다 정규화돼 있다


@dataclass
class ProfileBrew:
    brew: Brew
    vector: list[float]


@dataclass
class Candidate:
    kind: str
    ref_id: int
    title: str
    similarity: float
    content: str
    vector: list[float]
    source_url: str | None = None
    evidence: list[Brew] = field(default_factory=list)

    @property
    def candidate_id(self) -> str:
        return f"{self.kind}:{self.ref_id}"


def load_profile(session: Session, embedder: Embedder) -> list[ProfileBrew]:
    brews = list(session.scalars(select(Brew).where(Brew.rating >= HIGH_RATING).order_by(Brew.id)))
    if not brews:
        return []
    docs = session.scalars(
        select(Document).where(
            Document.kind == "bean",
            Document.model_id == embedder.model_id,  # 다른 모델로 만든 벡터와 섞지 않는다
            Document.ref_id.in_({b.bean_id for b in brews}),
        )
    )
    vectors = {d.ref_id: [float(x) for x in d.embedding] for d in docs}
    return [ProfileBrew(b, vectors[b.bean_id]) for b in brews if b.bean_id in vectors]


def profile_vector(profile: list[ProfileBrew]) -> list[float] | None:
    if not profile:
        return None
    acc = [0.0] * len(profile[0].vector)
    for p in profile:
        weight = p.brew.rating - (HIGH_RATING - 1)  # 4점=1, 5점=2
        for i, x in enumerate(p.vector):
            acc[i] += weight * x
    return _normalize(acc)


def similar_beans(session: Session, embedder: Embedder, bean_id: int, limit: int = 5) -> list[tuple[Bean, float]]:
    base = session.scalar(
        select(Document).where(
            Document.kind == "bean", Document.ref_id == bean_id, Document.model_id == embedder.model_id
        )
    )
    if base is None:
        return []
    distance = Document.embedding.cosine_distance([float(x) for x in base.embedding])
    rows = session.execute(
        select(Bean, distance.label("distance"))
        .join(Document, _doc_on(Bean, "bean", embedder.model_id))
        .where(Bean.id != bean_id)
        .order_by(distance)
        .limit(limit)
    ).all()
    return [(bean, round(1 - float(d), 4)) for bean, d in rows]


def _evidence(profile: list[ProfileBrew], vector: list[float]) -> list[Brew]:
    scored = sorted(profile, key=lambda p: (-_cosine(p.vector, vector), -p.brew.rating))
    return [p.brew for p in scored[:EVIDENCE_PER_CANDIDATE]]


def _start_grind(session: Session, brews: list[Brew]) -> dict | None:
    ids = [b.id for b in brews]
    if not ids:
        return None
    measurements = list(session.scalars(select(GrindMeasurement).where(GrindMeasurement.brew_id.in_(ids))))
    if not measurements:
        return None
    target = median(m.d50_mm for m in measurements)
    grinder_id = Counter(m.grinder_id for m in measurements).most_common(1)[0][0]
    suggestion = suggest_clicks(calibration_for(session, grinder_id), target)
    return {
        "d50_mm": round(target, 3),
        "grinder_id": grinder_id,
        "clicks": suggestion.clicks,
        "reason": f"근거 기록의 입도 중앙값은 D50 {target:.2f}mm예요. {suggestion.reason}",
    }


def _template_reason(brew: Brew) -> str:
    tags = ", ".join(label_of(t) for t in brew.flavor_tags[:3])
    text = f"'{brew.bean.name}' 기록({brew.rating}점)과 비슷한 원두예요"
    return text + (f". 그때 느낀 맛: {tags}" if tags else "")


def _my_bean_candidates(session: Session, embedder: Embedder, vector: list[float], limit: int) -> list[Candidate]:
    distance = Document.embedding.cosine_distance(vector)
    rows = session.execute(
        select(Bean, Document.content, Document.embedding, distance.label("distance"))
        .join(Document, _doc_on(Bean, "bean", embedder.model_id))
        .order_by(distance)
        .limit(limit)
    ).all()
    return [
        Candidate("my_bean", bean.id, bean.name, round(1 - float(d), 4), content, [float(x) for x in emb])
        for bean, content, emb, d in rows
    ]


def _catalog_candidates(
    session: Session,
    embedder: Embedder,
    vector: list[float],
    limit: int,
    country: str | None,
    processing: str | None,
) -> list[Candidate]:
    distance = Document.embedding.cosine_distance(vector)
    # 하이브리드: 정확히 맞아야 하는 조건(판매 중·산지·가공)은 SQL로, 취향 유사도는 벡터로 — 한 쿼리
    stmt = (
        select(CatalogBean, Document.content, Document.embedding, distance.label("distance"))
        .join(Document, _doc_on(CatalogBean, "catalog", embedder.model_id))
        .where(CatalogBean.available.is_(True), CatalogBean.status == "normalized")
    )
    if country:
        stmt = stmt.where(func.lower(CatalogBean.country) == country.lower())
    if processing:
        stmt = stmt.where(func.lower(CatalogBean.processing) == processing.lower())
    rows = session.execute(stmt.order_by(distance).limit(limit * 3)).all()

    owned = {name.strip().lower() for name in session.scalars(select(Bean.name))}
    candidates = []
    for item, content, emb, d in rows:
        name = ((item.normalized or {}).get("name") or item.title).strip().lower()
        if name in owned:
            continue  # 이미 기록한 원두는 신상 추천에서 뺀다
        candidates.append(
            Candidate(
                "catalog",
                item.id,
                item.title,
                round(1 - float(d), 4),
                content,
                [float(x) for x in emb],
                source_url=item.source_url,
            )
        )
    return candidates[:limit]


def refresh_recommendations(
    session: Session,
    embedder: Embedder,
    llm: LLM,
    *,
    limit: int = 5,
    country: str | None = None,
    processing: str | None = None,
) -> RecommendationSnapshot:
    profile = load_profile(session, embedder)
    vector = profile_vector(profile)
    candidates: list[Candidate] = []
    if vector is not None:
        candidates = _my_bean_candidates(session, embedder, vector, limit) + _catalog_candidates(
            session, embedder, vector, limit, country, processing
        )
        for c in candidates:
            c.evidence = _evidence(profile, c.vector)

    reasons = {}
    llm_model = None
    if candidates:
        payload = [
            {
                "candidate_id": c.candidate_id,
                "title": c.title,
                "description": c.content[:800],
                "evidence": [
                    {
                        "brew_id": b.id,
                        "bean": b.bean.name,
                        "rating": b.rating,
                        "flavors": [label_of(t) for t in b.flavor_tags],
                    }
                    for b in c.evidence
                ],
            }
            for c in candidates
        ]
        try:
            result = llm.generate(task="text", prompt=prompts.reason_prompt(payload), schema=ReasonBatch)
            llm_model = result.model
            reasons = {item.candidate_id: item for item in result.data.items}
        except LLMError:
            reasons = {}  # 한도 소진 등 — 추천 자체는 템플릿 문장으로 계속 낸다

    items = []
    for c in candidates:
        if not c.evidence:
            continue
        allowed = {b.id for b in c.evidence}
        r = reasons.get(c.candidate_id)
        valid = (
            r is not None
            and r.reason.strip()
            and len(r.reason) <= MAX_REASON_CHARS
            and r.evidence_brew_ids
            and set(r.evidence_brew_ids) <= allowed
        )
        if valid:
            reason, source = r.reason.strip(), "llm"
            evidence_ids = list(dict.fromkeys(r.evidence_brew_ids))
        else:
            reason, source = _template_reason(c.evidence[0]), "template"
            evidence_ids = [c.evidence[0].id]
        evidence_brews = [b for b in c.evidence if b.id in evidence_ids]
        items.append(
            {
                "kind": c.kind,
                "ref_id": c.ref_id,
                "title": c.title,
                "similarity": c.similarity,
                "reason": reason,
                "reason_source": source,
                "evidence_brew_ids": evidence_ids,
                "start_grind": _start_grind(session, evidence_brews),
                "source_url": c.source_url,
            }
        )

    snapshot = RecommendationSnapshot(
        embedding_model=embedder.model_id,
        llm_model=llm_model,
        profile_brew_ids=[p.brew.id for p in profile],
        items=items,
    )
    session.add(snapshot)
    session.commit()
    return snapshot
