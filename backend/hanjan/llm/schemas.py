"""LLM 구조화 출력 스키마.

기본값을 두지 않는다 — 모든 필드를 모델이 명시적으로 채우게 해야 "모름(null)"과 "안 적음"이 섞이지 않는다.
신뢰도 같은 필드도 두지 않는다. 신뢰도는 LLM에게 묻지 않고 코드가 센다.
"""

from pydantic import BaseModel


class BeanDraft(BaseModel):
    name: str | None
    roaster: str | None
    country: str | None
    region: str | None
    variety: str | None
    processing: str | None
    roast_level: str | None
    bag_flavor_notes: list[str]


class TagSuggestion(BaseModel):
    tags: list[str]


class CatalogNormalized(BaseModel):
    is_coffee_bean: bool
    name: str | None
    roaster: str | None
    country: str | None
    region: str | None
    variety: str | None
    processing: str | None
    roast_level: str | None
    flavor_notes: list[str]


class ReasonItem(BaseModel):
    candidate_id: str
    reason: str
    evidence_brew_ids: list[int]


class ReasonBatch(BaseModel):
    items: list[ReasonItem]
