from sqlalchemy.orm import Session, sessionmaker

from hanjan.config import Settings
from hanjan.llm.base import LLM
from hanjan.llm.chain import FallbackLLM, QuotaGuardedLLM
from hanjan.quota import QuotaGuard


def build_llm(settings: Settings, sessions: sessionmaker[Session]) -> LLM:
    if settings.llm_mode == "fake":
        from hanjan.llm.fake import FakeLLM

        return FakeLLM()

    from hanjan.llm.gemini import GeminiLLM

    guard = QuotaGuard(sessions, settings.llm_daily_limits)
    primary = QuotaGuardedLLM(
        GeminiLLM(settings.gemini_api_key or "", settings.gemini_vision_model, settings.gemini_text_model),
        guard,
    )
    fallback = None
    if settings.groq_api_key and (settings.groq_text_model or settings.groq_vision_model):
        from hanjan.llm.groq import GroqLLM

        fallback = QuotaGuardedLLM(
            GroqLLM(settings.groq_api_key, settings.groq_text_model, settings.groq_vision_model), guard
        )
    return FallbackLLM(primary, fallback)
