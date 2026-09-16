import io
import re
from datetime import UTC, datetime

import httpx
import numpy as np
import pytest
from alembic import command
from PIL import Image
from sqlalchemy import select

from hanjan.collect.run import collect
from hanjan.collect.sources import Fetcher, SourceConfig
from hanjan.grind.synthetic import synthetic_grind_image
from hanjan.llm.base import QuotaExceeded
from hanjan.llm.fake import FakeLLM
from hanjan.models import CatalogBean
from hanjan.quota import QuotaGuard

pytestmark = pytest.mark.db

ETH = {
    "title": "에티오피아 예가체프 워시드",
    "handle": "yirga",
    "body_html": "<p>에티오피아 워시드. 컵노트 레몬, 자스민</p>",
    "variants": [{"price": "19000", "available": True}],
}
BRA = {
    "title": "브라질 산토스 내추럴",
    "handle": "santos",
    "body_html": "<p>브라질 내추럴. 컵노트 초콜릿, 견과</p>",
    "variants": [{"price": "15000", "available": True}],
}
BAG = {"title": "드립백 10개입", "handle": "bag", "body_html": "드립백", "variants": [{"price": "12000"}]}
SOURCES = [SourceConfig(name="테스트 로스터리", kind="shopify", url="https://roaster.test")]


def shopify(products):
    def handler(request: httpx.Request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, json={"products": products})

    return Fetcher(httpx.Client(transport=httpx.MockTransport(handler)), "hanjan-bot/test", 0)


def catalog_item(session, handle: str) -> CatalogBean:
    session.expire_all()
    return session.scalars(
        select(CatalogBean).where(CatalogBean.source_url == f"https://roaster.test/products/{handle}")
    ).one()


# --- F5 수집 ---
def test_collect_normalizes_skips_non_beans_and_marks_sold_out(session, fake_llm, fake_embedder):
    first = collect(session, sources=SOURCES, fetcher=shopify([ETH, BRA, BAG]), llm=fake_llm, embedder=fake_embedder)
    assert (first.new, first.normalized, first.skipped, first.pending) == (3, 2, 1, 0)
    eth = catalog_item(session, "yirga")
    assert (eth.country, eth.processing, eth.status) == ("Ethiopia", "Washed", "normalized")
    assert catalog_item(session, "bag").status == "skipped"

    second = collect(session, sources=SOURCES, fetcher=shopify([ETH, BAG]), llm=fake_llm, embedder=fake_embedder)
    assert (second.new, second.normalized) == (0, 0)  # 내용이 그대로면 다시 정리하지 않는다
    assert catalog_item(session, "santos").available is False


def test_quota_exhaustion_leaves_items_pending_for_the_next_run(session, fake_embedder):
    llm = FakeLLM(error=QuotaExceeded("오늘 한도 소진"))

    result = collect(session, sources=SOURCES, fetcher=shopify([ETH, BRA]), llm=llm, embedder=fake_embedder)

    assert (result.normalized, result.pending) == (0, 2)
    assert any("정리 중단" in e for e in result.errors)


def test_empty_listing_does_not_mark_everything_sold_out(session, fake_llm, fake_embedder):
    collect(session, sources=SOURCES, fetcher=shopify([ETH]), llm=fake_llm, embedder=fake_embedder)

    result = collect(session, sources=SOURCES, fetcher=shopify([]), llm=fake_llm, embedder=fake_embedder)

    assert "상품 0개" in result.errors[0]
    assert catalog_item(session, "yirga").available is True


# --- F4 추천 ---
def png(img) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, "PNG")
    return buf.getvalue()


def seed_records(client, admin) -> dict[str, int]:
    grinder = client.post("/api/admin/grinders", json={"name": "알리 핸드밀"}, headers=admin).json()
    eth = client.post(
        "/api/admin/beans",
        json={"name": "구지 워시드", "country": "에티오피아", "processing": "워시드", "bag_flavor_notes": ["레몬", "자스민"]},
        headers=admin,
    ).json()
    bra = client.post(
        "/api/admin/beans",
        json={"name": "산토스", "country": "브라질", "processing": "내추럴", "bag_flavor_notes": ["초콜릿", "견과"]},
        headers=admin,
    ).json()
    liked = client.post(
        "/api/admin/brews",
        json={
            "bean_id": eth["id"],
            "grinder_id": grinder["id"],
            "grind_clicks": 18,
            "rating": 5,
            "flavor_tags": ["fruity.citrus", "floral.floral"],
        },
        headers=admin,
    ).json()
    client.post(
        "/api/admin/brews", json={"bean_id": bra["id"], "rating": 2, "flavor_tags": ["nutty_cocoa.cocoa"]}, headers=admin
    )
    for d50, form, seed in [
        (0.5, {"grinder_id": grinder["id"], "clicks": 12}, 1),
        (0.7, {"brew_id": liked["id"]}, 2),
        (0.9, {"grinder_id": grinder["id"], "clicks": 24}, 3),
    ]:
        img, _ = synthetic_grind_image(np.full(350, d50), seed=seed)
        r = client.post(
            "/api/admin/grind/measurements", data=form, files={"file": ("g.png", png(img), "image/png")}, headers=admin
        )
        assert r.status_code == 201, r.text
    return {"eth": eth["id"], "bra": bra["id"], "liked": liked["id"], "grinder": grinder["id"]}


def test_refresh_recommends_the_similar_catalog_bean_with_checked_evidence(
    client, admin, session, fake_llm, fake_embedder
):
    ids = seed_records(client, admin)
    collect(session, sources=SOURCES, fetcher=shopify([ETH, BRA]), llm=fake_llm, embedder=fake_embedder)

    snapshot = client.post("/api/admin/recommendations/refresh", headers=admin).json()

    assert snapshot["profile_brew_ids"] == [ids["liked"]]
    catalog = [i for i in snapshot["items"] if i["kind"] == "catalog"]
    assert catalog[0]["title"] == "에티오피아 예가체프 워시드"
    assert catalog[0]["reason_source"] == "llm"
    assert catalog[0]["evidence_brew_ids"] == [ids["liked"]]
    assert catalog[0]["start_grind"]["clicks"] == 18
    assert catalog[0]["source_url"] == "https://roaster.test/products/yirga"
    # 공개 조회는 저장본만 읽는다 (LLM을 부르지 않는다)
    calls_before = len(fake_llm.calls)
    assert client.get("/api/recommendations/latest").json()["id"] == snapshot["id"]
    assert len(fake_llm.calls) == calls_before


def test_reason_citing_a_brew_outside_the_evidence_is_replaced(client, admin, session, fake_llm, fake_embedder):
    seed_records(client, admin)
    collect(session, sources=SOURCES, fetcher=shopify([ETH, BRA]), llm=fake_llm, embedder=fake_embedder)
    fake_llm.set_handler(
        "ReasonBatch",
        lambda prompt, image: {
            "items": [
                {"candidate_id": cid, "reason": "지어낸 근거", "evidence_brew_ids": [999]}
                for cid in re.findall(r'"candidate_id": "([^"]+)"', prompt)
            ]
        },
    )

    snapshot = client.post("/api/admin/recommendations/refresh", headers=admin).json()

    assert snapshot["items"]
    assert all(i["reason_source"] == "template" for i in snapshot["items"])
    assert all(999 not in i["evidence_brew_ids"] for i in snapshot["items"])


def test_without_high_rated_brews_there_is_nothing_to_recommend_and_no_llm_call(client, admin, fake_llm):
    snapshot = client.post("/api/admin/recommendations/refresh", headers=admin).json()
    assert snapshot["items"] == []
    assert fake_llm.calls == []


def test_similar_beans_endpoint(client, admin):
    ids = seed_records(client, admin)
    similar = client.get(f"/api/beans/{ids['eth']}/similar").json()
    assert [s["bean"]["id"] for s in similar] == [ids["bra"]]
    assert similar[0]["brew_count"] == 1


# --- 한도·마이그레이션 ---
def test_daily_quota_is_per_model_and_resets_at_pacific_midnight(db_app):
    guard = QuotaGuard(db_app.state.sessions, {"gemini-a": 2})
    before_midnight = datetime(2026, 9, 15, 6, 0, tzinfo=UTC)
    guard.consume("gemini-a", before_midnight)
    guard.consume("gemini-a", before_midnight)
    with pytest.raises(QuotaExceeded):
        guard.consume("gemini-a", before_midnight)
    guard.consume("model-without-limit", before_midnight)
    guard.consume("gemini-a", datetime(2026, 9, 15, 7, 0, tzinfo=UTC))


def test_models_match_the_migrations(database):
    _, cfg = database
    command.check(cfg)  # 모델을 바꾸고 마이그레이션을 안 만들면 여기서 실패한다
