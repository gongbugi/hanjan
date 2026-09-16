from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수 `HANJAN_*` 로 주입한다. list/dict 값은 JSON 문자열로 넣는다."""

    model_config = SettingsConfigDict(env_prefix="HANJAN_", env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "postgresql+psycopg://hanjan:hanjan@localhost:5432/hanjan"
    cors_origins: list[str] = ["http://localhost:5173"]

    # --- 인증: 쓰기는 관리자만 (허용 목록) ---
    auth_mode: Literal["firebase", "dev"] = "dev"
    firebase_project_id: str | None = None
    admin_uids: list[str] = ["dev-admin-uid"]
    # dev 모드 전용: 토큰 문자열 -> uid
    dev_tokens: dict[str, str] = {"dev-admin": "dev-admin-uid", "dev-user": "dev-user-uid"}

    # --- LLM: Gemini 무료 등급 + Groq 예비 ---
    llm_mode: Literal["gemini", "fake"] = "fake"
    gemini_api_key: str | None = None
    # 봉투 인식 모델은 eval/bean_extract 비교 결과로 고정한다
    gemini_vision_model: str = "gemini-3.8-flash"
    gemini_text_model: str = "gemini-3.5-flash-lite"
    groq_api_key: str | None = None
    # 모델 ID를 모르면 비워둔다 — 비어 있으면 그 작업은 예비로 넘어가지 않는다
    groq_text_model: str | None = None
    groq_vision_model: str | None = None
    # 모델 ID -> 하루 요청 상한 (태평양 자정 기준). 없는 모델은 검사하지 않는다
    llm_daily_limits: dict[str, int] = {}

    # --- 임베딩: 로컬 e5-small-ko ---
    embedding_mode: Literal["e5", "fake"] = "fake"
    embedding_model: str = "dragonkue/multilingual-e5-small-ko"
    embedding_dim: int = 384
    embedding_cache_dir: str | None = None

    # --- 관측 ---
    # 지표 경로에 요구할 토큰. 공개 엣지가 모든 경로를 넘기므로 운영에서는 반드시 둔다
    metrics_token: str | None = None

    # --- 입도 측정 ---
    grind_marker_mm: float = 20.0
    max_upload_mb: int = 15

    # --- 신상 수집 ---
    roasters_file: str = "roasters.yaml"
    collector_user_agent: str = "hanjan-bot/0.1 (+https://github.com/gongbugi/hanjan)"
    collector_delay_seconds: float = 2.0

    @model_validator(mode="after")
    def _guard_prod(self) -> "Settings":
        if self.env != "prod":
            return self
        problems = []
        if self.auth_mode != "firebase":
            problems.append("운영에서 auth_mode=dev 금지")
        if not self.firebase_project_id:
            problems.append("firebase_project_id 필요")
        if not self.admin_uids or "dev-admin-uid" in self.admin_uids:
            problems.append("admin_uids에 실제 Firebase uid 필요")
        if self.llm_mode == "fake" or not self.gemini_api_key:
            problems.append("운영에서 가짜 LLM 금지 (gemini_api_key 필요)")
        if self.embedding_mode == "fake":
            problems.append("운영에서 가짜 임베딩 금지")
        if not self.metrics_token:
            problems.append("metrics_token 필요 (지표 경로가 공개로 열린다)")
        if any("*" in o for o in self.cors_origins):
            problems.append("CORS 와일드카드 금지 — Pages 주소만 적는다")
        if problems:
            raise ValueError("운영 설정 오류: " + " / ".join(problems))
        return self
