import pytest

from hanjan.embedding.e5 import as_passage, as_query
from hanjan.embedding.fake import FakeEmbedder


def dot(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_prefix_is_added_exactly_once():
    assert as_passage("원두 A") == "passage: 원두 A"
    assert as_passage("passage: 원두 A") == "passage: 원두 A"
    assert as_query("  산미  ") == "query: 산미"


def test_mixed_up_prefix_is_rejected():
    with pytest.raises(ValueError):
        as_passage("query: 원두")
    with pytest.raises(ValueError):
        as_query("passage: 원두")


def test_fake_embedder_is_normalized_and_follows_word_overlap():
    e = FakeEmbedder(dim=384)
    a, b, c = e.embed_passages(
        ["에티오피아 워시드 자스민 레몬", "에티오피아 워시드 자스민 베르가못", "브라질 내추럴 초콜릿 견과"]
    )
    assert dot(a, a) == pytest.approx(1.0)
    assert dot(a, b) > dot(a, c)


@pytest.mark.slow
def test_real_e5_small_ko_loads_with_the_configured_dimension():
    """실모델 스모크. 순위는 단언하지 않는다.

    "산미가 밝고 꽃향이 나는 원두" 질의에 에티오피아(레몬·자스민) 0.476 vs 브라질(초콜릿·견과) 0.472로
    차이가 0.004뿐이었다 (2026-09-15 실측, 1건). 이런 단언은 모델 갱신에 흔들린다 — 품질은 실제 기록으로 따로 잰다.
    """
    pytest.importorskip("sentence_transformers")
    from hanjan.embedding.e5 import E5Embedder

    e = E5Embedder("dragonkue/multilingual-e5-small-ko", 384)
    passage = "원두 예가체프. 산지 에티오피아. 가공 워시드. 컵노트 레몬, 자스민"
    a, b = e.embed_passages([passage, passage])
    query = e.embed_query("에티오피아 워시드")

    assert len(query) == 384
    assert dot(a, a) == pytest.approx(1.0, abs=1e-3)
    assert dot(a, b) == pytest.approx(1.0, abs=1e-3)
