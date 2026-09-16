"""모든 API를 훑어 쓰기 API가 전부 관리자 전용인지 검사한다. DB 없이 돈다.

myWeb은 경로·메서드를 if문으로 거르다 괄호 하나 때문에 쓰기 API가 인증 없이 열렸다.
새 API를 추가하면서 보호를 빼먹어도 이 테스트가 CI에서 잡는다.

⚠️ 경로 목록은 공개 계약인 OpenAPI 명세에서 뽑는다. 첫 버전은 app.routes를 훑었는데,
FastAPI 0.141은 포함된 라우터를 펼치지 않아서 검사 대상이 0개인 채로 '통과'했다.
그래서 대상 개수 자체도 단언한다. (include_in_schema=False로 숨긴 경로는 잡히지 않는다 — 이 레포는 만들지 않는다.)
"""

import re

from fastapi.testclient import TestClient

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
EXPECTED_ADMIN_OPERATIONS = 15


def _operations(app):
    for path, item in app.openapi()["paths"].items():
        for method in item:
            if method in HTTP_METHODS:
                yield method.upper(), path, re.sub(r"\{[^}]+\}", "1", path)


def _admin_operations(app):
    return [op for op in _operations(app) if op[1].startswith("/api/admin/")]


def test_the_check_is_not_vacuous(app_without_db):
    assert len(_admin_operations(app_without_db)) >= EXPECTED_ADMIN_OPERATIONS


def test_every_write_route_lives_under_admin(app_without_db):
    offenders = [
        f"{method} {path}"
        for method, path, _ in _operations(app_without_db)
        if method != "GET" and not path.startswith("/api/admin/")
    ]
    assert offenders == []


def test_admin_routes_reject_requests_without_token(app_without_db):
    client = TestClient(app_without_db)
    for method, path, concrete in _admin_operations(app_without_db):
        response = client.request(method, concrete)
        assert response.status_code == 401, f"{method} {path} → {response.status_code}"


def test_admin_routes_reject_signed_in_non_admin(app_without_db, user):
    client = TestClient(app_without_db)
    for method, path, concrete in _admin_operations(app_without_db):
        response = client.request(method, concrete, headers=user)
        assert response.status_code == 403, f"{method} {path} → {response.status_code}"


def test_invalid_token_is_401(app_without_db):
    client = TestClient(app_without_db)
    response = client.post("/api/admin/beans", headers={"Authorization": "Bearer forged"})
    assert response.status_code == 401


def test_me_needs_a_token_but_not_admin(app_without_db, user):
    client = TestClient(app_without_db)
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=user).json() == {"uid": "dev-user-uid", "is_admin": False}
