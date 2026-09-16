"""쓰기 API. 라우터 단위로 require_admin이 걸려 있어서 여기 추가하는 모든 경로는 자동으로 관리자 전용이다.

GET이 아닌 API는 전부 이 파일에 둔다 — tests/test_route_protection.py가 이 규칙을 검사한다.
"""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from hanjan.api.deps import EmbedderDep, LLMDep, SessionDep, SettingsDep, require_admin
from hanjan.collect.run import collect
from hanjan.collect.sources import load_sources
from hanjan.config import Settings
from hanjan.grind.analyze import analyze_grind
from hanjan.images import decode_grayscale, prepare_for_llm, read_upload
from hanjan.models import Bean, Brew, Grinder, GrindMeasurement
from hanjan.schemas import (
    BeanDraftOut,
    BeanIn,
    BeanOut,
    BrewIn,
    BrewOut,
    CollectResultOut,
    GrindAnalysisOut,
    GrinderIn,
    GrinderOut,
    GrindMeasurementOut,
    RecommendationSnapshotOut,
    TagSuggestIn,
    TagSuggestOut,
)
from hanjan.services.beans import extract_bean_draft, filled_fields, suggest_tags
from hanjan.services.documents import delete_documents, refresh_bean_document
from hanjan.services.grind import save_measurement
from hanjan.services.recommend import refresh_recommendations

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _get(session: Session, model, obj_id: int, label: str):
    obj = session.get(model, obj_id)
    if obj is None:
        raise HTTPException(404, f"{label} {obj_id}번이 없어요")
    return obj


def _load_brew(session: Session, brew_id: int) -> BrewOut:
    brew = session.scalar(
        select(Brew)
        .options(selectinload(Brew.bean), selectinload(Brew.measurements))
        .where(Brew.id == brew_id)
        .execution_options(populate_existing=True)
    )
    return BrewOut.model_validate(brew)


# --- 원두 (F1) ---
@router.post("/beans/extract", response_model=BeanDraftOut)
def extract_bean(file: Annotated[UploadFile, File()], settings: SettingsDep, llm: LLMDep):
    """봉투 사진 → 원두 정보 초안. 저장하지 않는다 — 사람이 확인·수정한 뒤 POST /beans로 저장한다."""
    image = prepare_for_llm(read_upload(file, settings.max_upload_mb))
    draft, result = extract_bean_draft(llm, image)
    return BeanDraftOut(draft=draft, filled_fields=filled_fields(draft), provider=result.provider, model=result.model)


@router.post("/beans", response_model=BeanOut, status_code=201)
def create_bean(body: BeanIn, session: SessionDep, embedder: EmbedderDep):
    bean = Bean(**body.model_dump())
    session.add(bean)
    session.flush()
    refresh_bean_document(session, embedder, bean.id)
    session.commit()
    return BeanOut.model_validate(bean)


@router.put("/beans/{bean_id}", response_model=BeanOut)
def update_bean(bean_id: int, body: BeanIn, session: SessionDep, embedder: EmbedderDep):
    bean = _get(session, Bean, bean_id, "원두")
    for key, value in body.model_dump().items():
        setattr(bean, key, value)
    session.flush()
    refresh_bean_document(session, embedder, bean_id)
    session.commit()
    session.refresh(bean)
    return BeanOut.model_validate(bean)


@router.delete("/beans/{bean_id}", status_code=204)
def delete_bean(bean_id: int, session: SessionDep):
    bean = _get(session, Bean, bean_id, "원두")
    if session.scalar(select(func.count()).select_from(Brew).where(Brew.bean_id == bean_id)):
        raise HTTPException(409, "추출 기록이 있는 원두는 지울 수 없어요")
    delete_documents(session, kind="bean", ref_id=bean_id)
    session.delete(bean)
    session.commit()
    return Response(status_code=204)


# --- 그라인더 ---
@router.post("/grinders", response_model=GrinderOut, status_code=201)
def create_grinder(body: GrinderIn, session: SessionDep):
    grinder = Grinder(**body.model_dump())
    session.add(grinder)
    session.commit()
    return GrinderOut.model_validate(grinder)


@router.put("/grinders/{grinder_id}", response_model=GrinderOut)
def update_grinder(grinder_id: int, body: GrinderIn, session: SessionDep):
    grinder = _get(session, Grinder, grinder_id, "그라인더")
    for key, value in body.model_dump().items():
        setattr(grinder, key, value)
    session.commit()
    return GrinderOut.model_validate(grinder)


# --- 추출 기록 (F2) ---
def _check_brew_refs(session: Session, body: BrewIn) -> None:
    if session.get(Bean, body.bean_id) is None:
        raise HTTPException(422, f"원두 {body.bean_id}번이 없어요")
    if body.grinder_id is not None and session.get(Grinder, body.grinder_id) is None:
        raise HTTPException(422, f"그라인더 {body.grinder_id}번이 없어요")


@router.post("/brews", response_model=BrewOut, status_code=201)
def create_brew(body: BrewIn, session: SessionDep, embedder: EmbedderDep):
    _check_brew_refs(session, body)
    data = body.model_dump()
    if data["brewed_on"] is None:
        data.pop("brewed_on")  # DB 기본값(오늘)
    brew = Brew(**data)
    session.add(brew)
    session.flush()
    refresh_bean_document(session, embedder, brew.bean_id)  # 맛 태그가 검색 문서에 들어간다
    session.commit()
    return _load_brew(session, brew.id)


@router.put("/brews/{brew_id}", response_model=BrewOut)
def update_brew(brew_id: int, body: BrewIn, session: SessionDep, embedder: EmbedderDep):
    brew = _get(session, Brew, brew_id, "추출 기록")
    _check_brew_refs(session, body)
    old_bean_id = brew.bean_id
    for key, value in body.model_dump().items():
        if key == "brewed_on" and value is None:
            continue
        setattr(brew, key, value)
    session.flush()
    for bean_id in {old_bean_id, brew.bean_id}:
        refresh_bean_document(session, embedder, bean_id)
    session.commit()
    return _load_brew(session, brew_id)


@router.delete("/brews/{brew_id}", status_code=204)
def delete_brew(brew_id: int, session: SessionDep, embedder: EmbedderDep):
    brew = _get(session, Brew, brew_id, "추출 기록")
    bean_id = brew.bean_id
    session.delete(brew)
    session.flush()
    refresh_bean_document(session, embedder, bean_id)
    session.commit()
    return Response(status_code=204)


@router.post("/brews/suggest-tags", response_model=TagSuggestOut)
def suggest_brew_tags(body: TagSuggestIn, llm: LLMDep):
    kept, dropped, result = suggest_tags(llm, body.note)
    return TagSuggestOut(tags=kept, dropped=dropped, provider=result.provider, model=result.model)


# --- 입도 (F3) ---
def _analyze(file: UploadFile, settings: Settings, marker_mm: float | None, mm_per_px: float | None):
    gray = decode_grayscale(read_upload(file, settings.max_upload_mb))
    if mm_per_px is not None:
        return analyze_grind(gray, mm_per_px=mm_per_px)
    return analyze_grind(gray, marker_mm=marker_mm or settings.grind_marker_mm)


@router.post("/grind/analyze", response_model=GrindAnalysisOut)
def analyze_grind_preview(
    file: Annotated[UploadFile, File()],
    settings: SettingsDep,
    marker_mm: Annotated[float | None, Form()] = None,
    mm_per_px: Annotated[float | None, Form()] = None,
):
    """저장하지 않는 미리보기."""
    return GrindAnalysisOut(**asdict(_analyze(file, settings, marker_mm, mm_per_px)))


@router.post("/grind/measurements", response_model=GrindMeasurementOut, status_code=201)
def create_measurement(
    file: Annotated[UploadFile, File()],
    session: SessionDep,
    settings: SettingsDep,
    brew_id: Annotated[int | None, Form()] = None,
    grinder_id: Annotated[int | None, Form()] = None,
    clicks: Annotated[int | None, Form()] = None,
    marker_mm: Annotated[float | None, Form()] = None,
    mm_per_px: Annotated[float | None, Form()] = None,
):
    if brew_id is not None:
        brew = _get(session, Brew, brew_id, "추출 기록")
        grinder_id = grinder_id if grinder_id is not None else brew.grinder_id
        clicks = clicks if clicks is not None else brew.grind_clicks
    if grinder_id is None or clicks is None:
        raise HTTPException(422, "그라인더와 클릭 수가 필요해요 (추출 기록에 적혀 있으면 생략할 수 있어요)")
    if clicks < 0:
        raise HTTPException(422, "클릭 수는 0 이상이에요")
    if session.get(Grinder, grinder_id) is None:
        raise HTTPException(422, f"그라인더 {grinder_id}번이 없어요")
    analysis = _analyze(file, settings, marker_mm, mm_per_px)
    measurement = save_measurement(session, analysis, grinder_id=grinder_id, clicks=clicks, brew_id=brew_id)
    session.commit()
    return GrindMeasurementOut.model_validate(measurement)


@router.delete("/grind/measurements/{measurement_id}", status_code=204)
def delete_measurement(measurement_id: int, session: SessionDep):
    session.delete(_get(session, GrindMeasurement, measurement_id, "입도 측정"))
    session.commit()
    return Response(status_code=204)


# --- 신상 수집 (F5) · 추천 (F4) ---
@router.post("/catalog/collect", response_model=CollectResultOut)
def run_collect(request: Request, session: SessionDep, settings: SettingsDep, llm: LLMDep, embedder: EmbedderDep):
    try:
        sources = load_sources(settings.roasters_file)
    except FileNotFoundError as e:
        raise HTTPException(422, f"수집 대상 파일이 없어요: {settings.roasters_file}") from e
    with request.app.state.fetcher_factory() as fetcher:
        result = collect(session, sources=sources, fetcher=fetcher, llm=llm, embedder=embedder)
    return CollectResultOut(**asdict(result))


@router.post("/recommendations/refresh", response_model=RecommendationSnapshotOut)
def refresh(
    session: SessionDep,
    llm: LLMDep,
    embedder: EmbedderDep,
    country: str | None = None,
    processing: str | None = None,
):
    snapshot = refresh_recommendations(session, embedder, llm, country=country, processing=processing)
    return RecommendationSnapshotOut.model_validate(snapshot)
