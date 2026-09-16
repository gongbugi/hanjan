"""지표가 프로필의 숫자를 잃지 않는지 본다."""

import pytest
from fastapi.testclient import TestClient

from hanjan.main import create_app
from hanjan.metrics import UNMATCHED
from tests.conftest import make_settings


@pytest.fixture
def metrics_client(fake_llm, fake_embedder):
    app = create_app(make_settings(), llm=fake_llm, embedder=fake_embedder)
    with TestClient(app) as c:
        yield c


def test_request_is_counted_with_route_template(metrics_client):
    metrics_client.get("/healthz")
    body = metrics_client.get("/metrics").text
    assert 'hanjan_http_requests_total{method="GET",path="/healthz",status="200"}' in body
    assert 'hanjan_http_request_duration_seconds_count{method="GET",path="/healthz"}' in body


def test_unmatched_path_does_not_become_a_label(metrics_client):
    metrics_client.get("/wp-admin/setup-config.php")
    body = metrics_client.get("/metrics").text
    assert "wp-admin" not in body  # 스캐너 경로가 시계열을 늘리면 안 된다
    assert f'path="{UNMATCHED}"' in body


def test_buckets_keep_the_profile_numbers(metrics_client):
    """0.5(방문자 목표)·10(외부 확인 타임아웃)·30(AI 경로)이 사라지면 나중에 못 되살린다."""
    metrics_client.get("/healthz")
    body = metrics_client.get("/metrics").text
    for edge in ("0.5", "10.0", "30.0"):
        assert f'le="{edge}"' in body


def test_metrics_path_is_not_in_the_public_schema(metrics_client):
    assert "/metrics" not in metrics_client.get("/openapi.json").json()["paths"]


def test_token_guards_metrics_when_set(fake_llm, fake_embedder):
    app = create_app(make_settings(metrics_token="s3cret"), llm=fake_llm, embedder=fake_embedder)
    with TestClient(app) as c:
        assert c.get("/metrics").status_code == 401
        assert c.get("/metrics", headers={"Authorization": "Bearer nope"}).status_code == 401
        assert c.get("/metrics", headers={"Authorization": "Bearer s3cret"}).status_code == 200
