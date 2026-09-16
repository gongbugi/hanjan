from datetime import date, datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from hanjan.flavor import FLAVOR_TAG_KEYS, MAX_TAGS_PER_BREW
from hanjan.llm.schemas import BeanDraft

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class FlavorTagOut(BaseModel):
    key: str
    group: str
    group_label: str
    label: str


# --- 그라인더 ---
class GrinderIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)


class GrinderOut(ORMModel):
    id: int
    name: str
    notes: str | None
    created_at: datetime


# --- 원두 ---
class BeanIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    roaster: str | None = Field(default=None, max_length=200)
    country: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    variety: str | None = Field(default=None, max_length=100)
    processing: str | None = Field(default=None, max_length=100)
    roast_level: str | None = Field(default=None, max_length=100)
    bag_flavor_notes: list[str] = Field(default_factory=list, max_length=20)


class BeanOut(ORMModel):
    id: int
    name: str
    roaster: str | None
    country: str | None
    region: str | None
    variety: str | None
    processing: str | None
    roast_level: str | None
    bag_flavor_notes: list[str]
    created_at: datetime


class BeanSummary(ORMModel):
    id: int
    name: str
    roaster: str | None


class BeanStatsOut(BaseModel):
    bean: BeanOut
    brew_count: int
    avg_rating: float | None


class BeanDraftOut(BaseModel):
    draft: BeanDraft
    filled_fields: int
    provider: str
    model: str


# --- 입도 ---
class HistogramBinOut(BaseModel):
    lo_mm: float
    hi_mm: float
    count: int
    area_share: float


class GrindStats(ORMModel):
    """분석 결과와 저장된 측정이 함께 갖는 값. 두 곳에 같은 필드를 다시 적지 않는다."""

    particle_count: int
    mm_per_px: float
    d10_mm: float
    d50_mm: float
    d90_mm: float
    count_d50_mm: float
    min_detectable_mm: float
    clump_suspects: int
    histogram: list[HistogramBinOut]
    warnings: list[str]


class GrindAnalysisOut(GrindStats):
    # 개수 기준 D10·D90은 분석 결과에만 있다 — DB에는 중앙값(count_d50_mm)만 남긴다
    count_d10_mm: float
    count_d90_mm: float


class GrindMeasurementOut(GrindStats):
    id: int
    brew_id: int | None
    grinder_id: int
    clicks: int
    created_at: datetime


class CalibrationRowOut(BaseModel):
    clicks: int
    n: int
    d50_median_mm: float
    d50_min_mm: float
    d50_max_mm: float


class CalibrationOut(BaseModel):
    grinder_id: int
    rows: list[CalibrationRowOut]
    monotonic: bool


class ClickSuggestionOut(BaseModel):
    grinder_id: int
    target_d50_mm: float
    clicks: int | None
    reason: str


# --- 추출 기록 ---
class BrewIn(BaseModel):
    bean_id: int
    grinder_id: int | None = None
    brewed_on: date | None = None
    grind_clicks: int | None = Field(default=None, ge=0, le=300)
    water_temp_c: int | None = Field(default=None, ge=60, le=100)
    dose_g: float | None = Field(default=None, gt=0, le=100)
    water_g: float | None = Field(default=None, gt=0, le=3000)
    brew_time_s: int | None = Field(default=None, ge=0, le=3600)
    rating: int = Field(ge=1, le=5)
    flavor_tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_BREW)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("flavor_tags")
    @classmethod
    def _known_tags(cls, value: list[str]) -> list[str]:
        unknown = [t for t in value if t not in FLAVOR_TAG_KEYS]
        if unknown:
            raise ValueError(f"정해진 맛 태그가 아니에요: {unknown}")
        return list(dict.fromkeys(value))


class BrewOut(ORMModel):
    id: int
    bean: BeanSummary
    grinder_id: int | None
    brewed_on: date
    grind_clicks: int | None
    water_temp_c: int | None
    dose_g: float | None
    water_g: float | None
    brew_time_s: int | None
    rating: int
    flavor_tags: list[str]
    note: str | None
    created_at: datetime
    measurements: list[GrindMeasurementOut]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ratio(self) -> float | None:
        """원두 1g당 물 g."""
        if self.dose_g and self.water_g:
            return round(self.water_g / self.dose_g, 1)
        return None


class TagSuggestIn(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class TagSuggestOut(BaseModel):
    tags: list[str]
    dropped: list[str]
    provider: str
    model: str


# --- 신상·추천 ---
class CatalogBeanOut(ORMModel):
    id: int
    source_name: str
    source_url: str
    title: str
    price: str | None
    available: bool
    status: str
    country: str | None
    processing: str | None
    normalized: dict[str, Any] | None
    first_seen_at: datetime
    last_seen_at: datetime


class SimilarBeanOut(BaseModel):
    bean: BeanOut
    similarity: float
    brew_count: int
    avg_rating: float | None


class StartGrindOut(BaseModel):
    d50_mm: float
    grinder_id: int
    clicks: int | None
    reason: str


class RecommendationItemOut(BaseModel):
    kind: Literal["my_bean", "catalog"]
    ref_id: int
    title: str
    similarity: float
    reason: str
    reason_source: Literal["llm", "template"]
    evidence_brew_ids: list[int]
    start_grind: StartGrindOut | None
    source_url: str | None = None


class RecommendationSnapshotOut(ORMModel):
    id: int
    created_at: datetime
    embedding_model: str
    llm_model: str | None
    profile_brew_ids: list[int]
    items: list[RecommendationItemOut]


class CollectResultOut(BaseModel):
    fetched: int
    new: int
    updated: int
    normalized: int
    skipped: int
    failed: int
    pending: int
    errors: list[str]


class MeOut(BaseModel):
    uid: str
    is_admin: bool
