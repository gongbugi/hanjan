import pytest
from pydantic import ValidationError

from hanjan.config import Settings

PROD_OK = {
    "env": "prod",
    "auth_mode": "firebase",
    "firebase_project_id": "hanjan-prod",
    "admin_uids": ["firebase-uid-123"],
    "llm_mode": "gemini",
    "gemini_api_key": "key",
    "embedding_mode": "e5",
    "cors_origins": ["https://hanjan.pages.dev"],
    "metrics_token": "a-long-random-token",
}


def test_valid_production_settings():
    Settings(**PROD_OK)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"auth_mode": "dev"}, "auth_mode=dev"),
        ({"admin_uids": ["dev-admin-uid"]}, "admin_uids"),
        ({"llm_mode": "fake"}, "가짜 LLM"),
        ({"embedding_mode": "fake"}, "가짜 임베딩"),
        ({"cors_origins": ["*"]}, "와일드카드"),
        ({"metrics_token": None}, "metrics_token"),
    ],
)
def test_production_guard_blocks_unsafe_settings(override, message):
    with pytest.raises(ValidationError, match=message):
        Settings(**{**PROD_OK, **override})
