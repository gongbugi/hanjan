import io

import pytest
from PIL import Image
from sqlalchemy import select

from hanjan.llm.base import QuotaExceeded
from hanjan.models import Document

pytestmark = pytest.mark.db


def png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(buf, "PNG")
    return buf.getvalue()


def seed(client, admin):
    grinder = client.post("/api/admin/grinders", json={"name": "알리 핸드밀 (모델 모름)"}, headers=admin).json()
    bean = client.post(
        "/api/admin/beans",
        json={"name": "구지 워시드", "country": "Ethiopia", "processing": "Washed", "bag_flavor_notes": ["레몬"]},
        headers=admin,
    ).json()
    return grinder, bean


def test_bean_and_brew_flow(client, admin, session):
    grinder, bean = seed(client, admin)
    response = client.post(
        "/api/admin/brews",
        json={
            "bean_id": bean["id"],
            "grinder_id": grinder["id"],
            "grind_clicks": 18,
            "water_temp_c": 92,
            "dose_g": 15,
            "water_g": 240,
            "brew_time_s": 150,
            "rating": 5,
            "flavor_tags": ["fruity.citrus", "floral.floral"],
            "note": "레몬, 자스민",
        },
        headers=admin,
    )
    assert response.status_code == 201, response.text
    brew = response.json()
    assert brew["ratio"] == 16.0
    assert brew["bean"]["name"] == "구지 워시드"
    assert brew["brewed_on"]

    # 공개 조회는 토큰 없이
    assert client.get(f"/api/brews/{brew['id']}").status_code == 200
    page = client.get("/api/brews", params={"limit": 1}).json()
    assert (page["total"], len(page["items"])) == (1, 1)
    stats = client.get(f"/api/beans/{bean['id']}").json()
    assert (stats["brew_count"], stats["avg_rating"]) == (1, 5.0)

    # 내가 느낀 맛이 검색 문서에 들어가고, 벡터를 만든 모델이 기록된다
    doc = session.scalars(select(Document).where(Document.kind == "bean", Document.ref_id == bean["id"])).one()
    assert "시트러스" in doc.content
    assert doc.model_id == "fake-hash-embedder"


def test_unknown_flavor_tag_is_rejected(client, admin):
    _, bean = seed(client, admin)
    response = client.post(
        "/api/admin/brews", json={"bean_id": bean["id"], "rating": 4, "flavor_tags": ["fruity.mango"]}, headers=admin
    )
    assert response.status_code == 422


def test_bean_with_brews_cannot_be_deleted(client, admin):
    _, bean = seed(client, admin)
    brew = client.post("/api/admin/brews", json={"bean_id": bean["id"], "rating": 3}, headers=admin).json()

    assert client.delete(f"/api/admin/beans/{bean['id']}", headers=admin).status_code == 409
    assert client.delete(f"/api/admin/brews/{brew['id']}", headers=admin).status_code == 204
    assert client.delete(f"/api/admin/beans/{bean['id']}", headers=admin).status_code == 204


def test_extract_returns_a_draft_without_saving(client, admin):
    response = client.post(
        "/api/admin/beans/extract", files={"file": ("bag.png", png(), "image/png")}, headers=admin
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["draft"]["country"] == "Ethiopia"
    assert body["filled_fields"] == 5
    assert body["provider"] == "fake"
    assert client.get("/api/beans").json()["total"] == 0


def test_suggested_tags_outside_the_list_are_dropped(client, admin, fake_llm):
    fake_llm.set_handler("TagSuggestion", lambda prompt, image: {"tags": ["fruity.citrus", "fruity.mango"]})

    body = client.post("/api/admin/brews/suggest-tags", json={"note": "레몬"}, headers=admin).json()

    assert body["tags"] == ["fruity.citrus"]
    assert body["dropped"] == ["fruity.mango"]


def test_quota_exhaustion_is_429(client, admin, fake_llm):
    fake_llm.error = QuotaExceeded("gemini-3.5-flash-lite: 오늘 한도 소진")

    response = client.post("/api/admin/brews/suggest-tags", json={"note": "레몬"}, headers=admin)

    assert response.status_code == 429
    assert "한도" in response.json()["detail"]


def test_readyz_checks_the_database(client):
    assert client.get("/readyz").json() == {"status": "ready"}
