"""공개 조회 API. 전부 GET이고, LLM을 부르지 않는다 (방문자가 무료 할당량을 쓰지 않게)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from hanjan.api.deps import EmbedderDep, SessionDep
from hanjan.flavor import FLAVOR_TAGS, GROUP_LABELS
from hanjan.grind.calibration import suggest_clicks
from hanjan.models import Bean, Brew, CatalogBean, Grinder, RecommendationSnapshot
from hanjan.schemas import (
    BeanOut,
    BeanStatsOut,
    BrewOut,
    CalibrationOut,
    CalibrationRowOut,
    CatalogBeanOut,
    ClickSuggestionOut,
    FlavorTagOut,
    GrinderOut,
    Page,
    RecommendationSnapshotOut,
    SimilarBeanOut,
)
from hanjan.services.grind import calibration_for
from hanjan.services.recommend import similar_beans

router = APIRouter(prefix="/api", tags=["public"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def _bean_stats(session, bean_ids: list[int]) -> dict[int, tuple[int, float | None]]:
    if not bean_ids:
        return {}
    rows = session.execute(
        select(Brew.bean_id, func.count(Brew.id), func.avg(Brew.rating))
        .where(Brew.bean_id.in_(bean_ids))
        .group_by(Brew.bean_id)
    ).all()
    return {bean_id: (count, round(float(avg), 2)) for bean_id, count, avg in rows}


@router.get("/flavor-tags", response_model=list[FlavorTagOut])
def flavor_tags():
    return [
        FlavorTagOut(key=t.key, group=t.group, group_label=GROUP_LABELS[t.group], label=t.label)
        for t in FLAVOR_TAGS
    ]


@router.get("/beans", response_model=Page[BeanOut])
def list_beans(session: SessionDep, limit: Limit = 20, offset: Offset = 0):
    total = session.scalar(select(func.count()).select_from(Bean)) or 0
    beans = session.scalars(select(Bean).order_by(Bean.id.desc()).limit(limit).offset(offset)).all()
    return Page[BeanOut](
        items=[BeanOut.model_validate(b) for b in beans], total=total, limit=limit, offset=offset
    )


@router.get("/beans/{bean_id}", response_model=BeanStatsOut)
def get_bean(bean_id: int, session: SessionDep):
    bean = session.get(Bean, bean_id)
    if bean is None:
        raise HTTPException(404, f"원두 {bean_id}번이 없어요")
    count, avg = _bean_stats(session, [bean_id]).get(bean_id, (0, None))
    return BeanStatsOut(bean=BeanOut.model_validate(bean), brew_count=count, avg_rating=avg)


@router.get("/beans/{bean_id}/similar", response_model=list[SimilarBeanOut])
def get_similar_beans(
    bean_id: int,
    session: SessionDep,
    embedder: EmbedderDep,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
):
    if session.get(Bean, bean_id) is None:
        raise HTTPException(404, f"원두 {bean_id}번이 없어요")
    results = similar_beans(session, embedder, bean_id, limit)
    stats = _bean_stats(session, [b.id for b, _ in results])
    return [
        SimilarBeanOut(
            bean=BeanOut.model_validate(bean),
            similarity=similarity,
            brew_count=stats.get(bean.id, (0, None))[0],
            avg_rating=stats.get(bean.id, (0, None))[1],
        )
        for bean, similarity in results
    ]


@router.get("/brews", response_model=Page[BrewOut])
def list_brews(session: SessionDep, bean_id: int | None = None, limit: Limit = 20, offset: Offset = 0):
    query = select(Brew)
    count_query = select(func.count()).select_from(Brew)
    if bean_id is not None:
        query = query.where(Brew.bean_id == bean_id)
        count_query = count_query.where(Brew.bean_id == bean_id)
    brews = session.scalars(
        query.options(selectinload(Brew.bean), selectinload(Brew.measurements))
        .order_by(Brew.brewed_on.desc(), Brew.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return Page[BrewOut](
        items=[BrewOut.model_validate(b) for b in brews],
        total=session.scalar(count_query) or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/brews/{brew_id}", response_model=BrewOut)
def get_brew(brew_id: int, session: SessionDep):
    brew = session.scalar(
        select(Brew)
        .options(selectinload(Brew.bean), selectinload(Brew.measurements))
        .where(Brew.id == brew_id)
    )
    if brew is None:
        raise HTTPException(404, f"추출 기록 {brew_id}번이 없어요")
    return BrewOut.model_validate(brew)


@router.get("/grinders", response_model=list[GrinderOut])
def list_grinders(session: SessionDep):
    return [GrinderOut.model_validate(g) for g in session.scalars(select(Grinder).order_by(Grinder.id))]


@router.get("/grinders/{grinder_id}/calibration", response_model=CalibrationOut)
def get_calibration(grinder_id: int, session: SessionDep):
    if session.get(Grinder, grinder_id) is None:
        raise HTTPException(404, f"그라인더 {grinder_id}번이 없어요")
    cal = calibration_for(session, grinder_id)
    return CalibrationOut(
        grinder_id=grinder_id,
        rows=[CalibrationRowOut(**row.__dict__) for row in cal.rows],
        monotonic=cal.monotonic,
    )


@router.get("/grinders/{grinder_id}/suggest", response_model=ClickSuggestionOut)
def suggest_grinder_clicks(
    grinder_id: int, session: SessionDep, target_d50_mm: Annotated[float, Query(gt=0, le=3)]
):
    if session.get(Grinder, grinder_id) is None:
        raise HTTPException(404, f"그라인더 {grinder_id}번이 없어요")
    s = suggest_clicks(calibration_for(session, grinder_id), target_d50_mm)
    return ClickSuggestionOut(grinder_id=grinder_id, target_d50_mm=target_d50_mm, clicks=s.clicks, reason=s.reason)


@router.get("/catalog", response_model=Page[CatalogBeanOut])
def list_catalog(
    session: SessionDep, include_unavailable: bool = False, limit: Limit = 20, offset: Offset = 0
):
    where = [CatalogBean.status == "normalized"]
    if not include_unavailable:
        where.append(CatalogBean.available.is_(True))
    items = session.scalars(
        select(CatalogBean).where(*where).order_by(CatalogBean.first_seen_at.desc(), CatalogBean.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    total = session.scalar(select(func.count()).select_from(CatalogBean).where(*where)) or 0
    return Page[CatalogBeanOut](
        items=[CatalogBeanOut.model_validate(i) for i in items], total=total, limit=limit, offset=offset
    )


@router.get("/recommendations/latest", response_model=RecommendationSnapshotOut | None)
def latest_recommendations(session: SessionDep):
    snapshot = session.scalar(
        select(RecommendationSnapshot).order_by(RecommendationSnapshot.id.desc()).limit(1)
    )
    return RecommendationSnapshotOut.model_validate(snapshot) if snapshot else None
