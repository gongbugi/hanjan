"""uvicorn hanjan.main:create_app --factory"""

from collections.abc import Callable
from contextlib import AbstractContextManager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from hanjan import __version__
from hanjan.api import admin, auth_routes, health, public
from hanjan.auth import TokenVerifier, build_verifier
from hanjan.collect.sources import Fetcher, open_fetcher
from hanjan.config import Settings
from hanjan.db import make_engine, make_sessionmaker
from hanjan.embedding import build_embedder
from hanjan.embedding.base import Embedder
from hanjan.grind.analyze import GrindAnalysisError
from hanjan.llm.base import LLM, LLMBadOutput, LLMError, LLMUnavailable, QuotaExceeded
from hanjan.llm.factory import build_llm
from hanjan.metrics import MetricsMiddleware
from hanjan.metrics import router as metrics_router


def create_app(
    settings: Settings | None = None,
    *,
    llm: LLM | None = None,
    embedder: Embedder | None = None,
    verifier: TokenVerifier | None = None,
    fetcher_factory: Callable[[], AbstractContextManager[Fetcher]] | None = None,
) -> FastAPI:
    settings = settings or Settings()
    engine = make_engine(settings.database_url)
    sessions = make_sessionmaker(engine)

    app = FastAPI(title="hanjan API", version=__version__)
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessions = sessions
    app.state.llm = llm or build_llm(settings, sessions)
    # e5 임베더는 여기서 모델을 메모리에 올린다 — k8s startupProbe가 이 시간을 기다려야 한다
    app.state.embedder = embedder or build_embedder(settings)
    app.state.verifier = verifier or build_verifier(settings)
    app.state.fetcher_factory = fetcher_factory or (lambda: open_fetcher(settings))

    # 나중에 추가한 미들웨어가 바깥쪽이다 — 지표는 CORS까지 포함한 전체 시간을 재야 한다
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # 정확한 주소만. 토큰은 헤더로 보내므로 쿠키(credentials)가 필요 없다
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def _error(status: int, prefix: str):
        def handler(request: Request, exc: Exception) -> JSONResponse:
            return JSONResponse(status_code=status, content={"detail": f"{prefix}{exc}"})

        return handler

    app.add_exception_handler(QuotaExceeded, _error(429, "AI 하루 한도를 넘었어요 — "))
    app.add_exception_handler(LLMUnavailable, _error(503, "AI 제공자에 닿지 않아요 — "))
    app.add_exception_handler(LLMBadOutput, _error(502, "AI 응답 형식이 맞지 않아요 — "))
    app.add_exception_handler(LLMError, _error(502, "AI 호출 실패 — "))
    app.add_exception_handler(GrindAnalysisError, _error(422, ""))

    app.include_router(health.router)
    app.include_router(metrics_router)
    app.include_router(public.router)
    app.include_router(auth_routes.router)
    app.include_router(admin.router)
    return app
