"""맛 태그 목록 — SCA 커피 테이스터 플레이버 휠의 분류를 따른 고정 목록.

LLM은 이 목록 밖의 태그를 만들 수 없다. 모델이 목록 밖 값을 내면 코드가 버린다.
태그가 자유롭게 늘어나면 기록 간 비교와 추천 검색이 망가지기 때문이다.
"""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class FlavorTag:
    key: str
    group: str
    label: str


GROUP_LABELS: dict[str, str] = {
    "floral": "꽃",
    "fruity": "과일",
    "sour_fermented": "산미·발효",
    "green_vegetative": "풀·채소",
    "other": "기타",
    "roasted": "로스팅",
    "spices": "향신료",
    "nutty_cocoa": "견과·코코아",
    "sweet": "단맛",
}

FLAVOR_TAGS: tuple[FlavorTag, ...] = (
    FlavorTag("floral.black_tea", "floral", "홍차"),
    FlavorTag("floral.floral", "floral", "꽃향"),
    FlavorTag("fruity.berry", "fruity", "베리"),
    FlavorTag("fruity.dried_fruit", "fruity", "말린 과일"),
    FlavorTag("fruity.other_fruit", "fruity", "사과·복숭아 같은 과일"),
    FlavorTag("fruity.citrus", "fruity", "시트러스"),
    FlavorTag("sour_fermented.sour", "sour_fermented", "밝은 산미"),
    FlavorTag("sour_fermented.fermented", "sour_fermented", "발효·와인"),
    FlavorTag("green_vegetative.olive_oil", "green_vegetative", "올리브오일"),
    FlavorTag("green_vegetative.raw", "green_vegetative", "덜 익은 맛"),
    FlavorTag("green_vegetative.vegetative", "green_vegetative", "풀·채소"),
    FlavorTag("green_vegetative.beany", "green_vegetative", "콩 비린내"),
    FlavorTag("other.papery_musty", "other", "종이·묵은 냄새"),
    FlavorTag("other.chemical", "other", "화학적인 맛"),
    FlavorTag("roasted.pipe_tobacco", "roasted", "파이프 담배"),
    FlavorTag("roasted.tobacco", "roasted", "담배"),
    FlavorTag("roasted.burnt", "roasted", "탄 맛"),
    FlavorTag("roasted.cereal", "roasted", "곡물"),
    FlavorTag("spices.pungent", "spices", "톡 쏘는 향"),
    FlavorTag("spices.pepper", "spices", "후추"),
    FlavorTag("spices.brown_spice", "spices", "계피·정향"),
    FlavorTag("nutty_cocoa.nutty", "nutty_cocoa", "견과"),
    FlavorTag("nutty_cocoa.cocoa", "nutty_cocoa", "코코아·초콜릿"),
    FlavorTag("sweet.brown_sugar", "sweet", "흑설탕·캐러멜"),
    FlavorTag("sweet.vanilla", "sweet", "바닐라"),
    FlavorTag("sweet.overall_sweet", "sweet", "전반적인 단맛"),
    FlavorTag("sweet.sweet_aromatics", "sweet", "달콤한 향"),
)

FLAVOR_TAG_KEYS: frozenset[str] = frozenset(t.key for t in FLAVOR_TAGS)
_BY_KEY = {t.key: t for t in FLAVOR_TAGS}

MAX_TAGS_PER_BREW = 6


def label_of(key: str) -> str:
    tag = _BY_KEY.get(key)
    return tag.label if tag else key


def filter_known(tags: Iterable[str], limit: int = MAX_TAGS_PER_BREW) -> tuple[list[str], list[str]]:
    """목록에 있는 태그만 순서대로 남긴다. (남긴 것, 버린 것)"""
    kept: list[str] = []
    dropped: list[str] = []
    for raw in tags:
        tag = raw.strip()
        if tag in FLAVOR_TAG_KEYS:
            if tag not in kept and len(kept) < limit:
                kept.append(tag)
        else:
            dropped.append(tag)
    return kept, dropped
