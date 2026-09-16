"""Prometheus 노출 — 서비스 프로필의 SLI를 코드로 옮긴 곳.

프로필: 방문자 조회 p95 500ms · 에러는 5xx와 타임아웃 10초 · AI 경로 30초.
그 숫자를 히스토그램 버킷에 그대로 넣는다. 버킷에 없는 값은 나중에 못 되살린다.

⚠️ 목표 판정은 여기서 하지 않는다. 클러스터 밖 외부 확인이 한다 —
   VM과 함께 죽는 지표로는 "죽었다"를 잴 수 없기 때문이다.
"""

import secrets
import time

from fastapi import APIRouter, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# 0.5 = 방문자 조회 목표, 10 = 외부 확인 타임아웃, 30 = AI 경로 허용치
BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)

METRICS_PATH = "/metrics"
# 라우트에 걸리지 않은 요청. 원시 경로를 라벨로 쓰면 스캐너 한 번에 시계열이 무한히 늘어난다
UNMATCHED = "<unmatched>"

REQUESTS = Counter(
    "hanjan_http_requests_total",
    "HTTP 요청 수 (status로 5xx를 센다)",
    ["method", "path", "status"],
)
DURATION = Histogram(
    "hanjan_http_request_duration_seconds",
    "HTTP 처리 시간",
    ["method", "path"],
    buckets=BUCKETS,
)


class MetricsMiddleware:
    """요청 수·처리 시간을 잰다. 경로 라벨은 반드시 라우트 템플릿으로 쓴다."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    @staticmethod
    def _template(scope: Scope) -> str:
        # FastAPI가 라우팅하면서 scope["route"]에 APIRoute를 넣어 준다 (fastapi/routing.py).
        # ⚠️ Starlette만 쓰면 이 키가 없다 — 그때는 UNMATCHED로 떨어진다.
        # 앱의 라우트 목록을 직접 걷는 방법은 쓰지 않는다: FastAPI 0.141은 include_router한 라우터를
        # _IncludedRouter(path도 endpoint도 없는 객체)로 감싸서 목록만 봐서는 경로를 알 수 없다.
        return getattr(scope.get("route"), "path", None) or UNMATCHED

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") == METRICS_PATH:
            await self.app(scope, receive, send)
            return

        status = 500  # 응답 시작 메시지가 없으면 예외로 끝난 것이다
        started = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - started
            method = scope.get("method", "-")
            path = self._template(scope)
            REQUESTS.labels(method=method, path=path, status=str(status)).inc()
            DURATION.labels(method=method, path=path).observe(elapsed)


router = APIRouter(tags=["metrics"])


# OpenAPI에 넣지 않는다 — 프론트 타입 생성 대상이 아니고, 스키마가 바뀌면 CI 드리프트 검사가 운다
@router.get(METRICS_PATH, include_in_schema=False)
def metrics(request: Request) -> Response:
    """설정에 토큰이 있으면 그 토큰을 요구한다. 공개 엣지가 이 경로까지 통째로 넘길 수 있어서다."""
    expected = request.app.state.settings.metrics_token
    if expected:
        given = request.headers.get("Authorization", "")
        if not secrets.compare_digest(given, f"Bearer {expected}"):
            raise HTTPException(401, "지표는 토큰이 필요해요")
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
