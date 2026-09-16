import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from hanjan.config import Settings
from hanjan.embedding.fake import FakeEmbedder
from hanjan.llm.fake import FakeLLM
from hanjan.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ.get("HANJAN_TEST_DATABASE_URL")
TABLES = (
    "recommendation_snapshots, llm_usage, documents, catalog_beans, grind_measurements, brews, beans, grinders"
)


def make_settings(**overrides) -> Settings:
    values = {
        "env": "test",
        # DB 없는 테스트용 주소 — 엔진은 첫 쿼리 전까지 연결하지 않는다
        "database_url": TEST_DATABASE_URL or "postgresql+psycopg://nobody:nobody@127.0.0.1:1/nodb",
        "auth_mode": "dev",
        "admin_uids": ["dev-admin-uid"],
        "llm_mode": "fake",
        "embedding_mode": "fake",
        "cors_origins": ["http://localhost:5173"],
        "collector_delay_seconds": 0,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def admin() -> dict[str, str]:
    return {"Authorization": "Bearer dev-admin"}


@pytest.fixture
def user() -> dict[str, str]:
    return {"Authorization": "Bearer dev-user"}


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def app_without_db(fake_llm, fake_embedder):
    return create_app(make_settings(), llm=fake_llm, embedder=fake_embedder)


@pytest.fixture(scope="session")
def database():
    if not TEST_DATABASE_URL:
        pytest.skip("HANJAN_TEST_DATABASE_URL이 없어 DB 테스트를 건너뜀")
    from alembic import command
    from alembic.config import Config

    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")  # 마이그레이션 자체를 테스트 DB 구성에 쓴다
    yield engine, cfg
    engine.dispose()


@pytest.fixture
def db_app(database, fake_llm, fake_embedder):
    engine, _ = database
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    app = create_app(make_settings(), llm=fake_llm, embedder=fake_embedder)
    yield app
    app.state.engine.dispose()


@pytest.fixture
def client(db_app):
    with TestClient(db_app) as c:
        yield c


@pytest.fixture
def session(db_app):
    with db_app.state.sessions() as s:
        yield s
