import pytest
from pydantic import ValidationError

from hanjan.flavor import FLAVOR_TAG_KEYS, MAX_TAGS_PER_BREW, filter_known
from hanjan.schemas import BrewIn


def test_filter_known_drops_invented_tags_and_dedupes():
    kept, dropped = filter_known(["fruity.berry", "fruity.mango", "fruity.berry", " sweet.vanilla "])
    assert kept == ["fruity.berry", "sweet.vanilla"]
    assert dropped == ["fruity.mango"]


def test_filter_known_caps_the_count():
    kept, _ = filter_known(sorted(FLAVOR_TAG_KEYS))
    assert len(kept) == MAX_TAGS_PER_BREW


def test_brew_rejects_unknown_tag():
    with pytest.raises(ValidationError, match="정해진 맛 태그"):
        BrewIn(bean_id=1, rating=4, flavor_tags=["fruity.mango"])


@pytest.mark.parametrize("rating", [0, 6])
def test_brew_rating_is_1_to_5(rating):
    with pytest.raises(ValidationError):
        BrewIn(bean_id=1, rating=rating)
