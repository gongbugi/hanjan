"""검색 문서. 기록 하나 = 문서 하나 (짧은 구조화 데이터라 청킹하지 않는다)."""

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from hanjan.embedding.base import Embedder
from hanjan.flavor import label_of
from hanjan.models import Bean, Brew, CatalogBean, Document


def _sentences(*parts: str | None) -> str:
    return ". ".join(p for p in parts if p)


def _origin(country: str | None, region: str | None) -> str | None:
    joined = " ".join(x for x in (country, region) if x)
    return f"산지 {joined}" if joined else None


def bean_text(bean: Bean, brews: list[Brew]) -> str:
    tags = sorted({t for b in brews for t in b.flavor_tags})
    return _sentences(
        f"원두 {bean.name}",
        bean.roaster and f"로스터리 {bean.roaster}",
        _origin(bean.country, bean.region),
        bean.variety and f"품종 {bean.variety}",
        bean.processing and f"가공 {bean.processing}",
        bean.roast_level and f"로스팅 {bean.roast_level}",
        bean.bag_flavor_notes and f"컵노트 {', '.join(bean.bag_flavor_notes)}",
        tags and f"내가 느낀 맛 {', '.join(label_of(t) for t in tags)}",
    )


def catalog_text(item: CatalogBean) -> str:
    n = item.normalized or {}
    return _sentences(
        f"원두 {n.get('name') or item.title}",
        f"로스터리 {n.get('roaster') or item.source_name}",
        _origin(n.get("country"), n.get("region")),
        n.get("variety") and f"품종 {n['variety']}",
        n.get("processing") and f"가공 {n['processing']}",
        n.get("roast_level") and f"로스팅 {n['roast_level']}",
        n.get("flavor_notes") and f"컵노트 {', '.join(n['flavor_notes'])}",
    )


def upsert_document(session: Session, embedder: Embedder, *, kind: str, ref_id: int, content: str) -> bool:
    """내용이 그대로면 다시 임베딩하지 않는다 (2코어 VM에서 CPU를 아낀다). 새로 만들었으면 True."""
    existing = session.scalar(
        select(Document).where(
            Document.kind == kind, Document.ref_id == ref_id, Document.model_id == embedder.model_id
        )
    )
    if existing is not None and existing.content == content:
        return False
    vector = embedder.embed_passages([content])[0]
    stmt = insert(Document).values(
        kind=kind, ref_id=ref_id, model_id=embedder.model_id, content=content, embedding=vector
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_documents_ref_model",
        set_={"content": stmt.excluded.content, "embedding": stmt.excluded.embedding, "updated_at": func.now()},
    )
    session.execute(stmt)
    return True


def refresh_bean_document(session: Session, embedder: Embedder, bean_id: int) -> None:
    bean = session.get(Bean, bean_id)
    if bean is None:
        return
    brews = list(session.scalars(select(Brew).where(Brew.bean_id == bean_id)))
    upsert_document(session, embedder, kind="bean", ref_id=bean_id, content=bean_text(bean, brews))


def delete_documents(session: Session, *, kind: str, ref_id: int) -> None:
    session.execute(delete(Document).where(Document.kind == kind, Document.ref_id == ref_id))
