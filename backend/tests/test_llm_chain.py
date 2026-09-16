import pytest

from hanjan.llm.base import LLMBadOutput, QuotaExceeded
from hanjan.llm.chain import FallbackLLM, QuotaGuardedLLM
from hanjan.llm.fake import FakeLLM
from hanjan.llm.schemas import BeanDraft, TagSuggestion

PROMPT = "<<NOTE>>\n레몬 같은 산미\n<<END>>"


def test_falls_back_when_primary_quota_is_exhausted():
    primary = FakeLLM(provider="gemini", error=QuotaExceeded("429"))
    fallback = FakeLLM(provider="groq")

    result = FallbackLLM(primary, fallback).generate(task="text", prompt=PROMPT, schema=TagSuggestion)

    assert result.provider == "groq"
    # 예비 제공자가 실제로 호출됐는지를 본다. (예전에는 가짜 LLM의 키워드 표가 만든 태그를 단언했는데,
    #  그건 우리 코드가 아니라 테스트 대역의 동작을 검사하는 것이었다)
    assert primary.calls == [("text", "TagSuggestion")]  # 주 제공자를 먼저 시도하고
    assert fallback.calls == [("text", "TagSuggestion")]  # 한도에 막힌 뒤 예비로 넘어간다


def test_bad_output_is_not_hidden_by_fallback():
    primary = FakeLLM(provider="gemini", error=LLMBadOutput("스키마 불일치"))
    fallback = FakeLLM(provider="groq")

    with pytest.raises(LLMBadOutput):
        FallbackLLM(primary, fallback).generate(task="text", prompt=PROMPT, schema=TagSuggestion)
    assert fallback.calls == []


def test_no_fallback_for_a_task_the_fallback_has_no_model_for():
    primary = FakeLLM(provider="gemini", error=QuotaExceeded("429"))
    fallback = FakeLLM(provider="groq", vision=False)

    with pytest.raises(QuotaExceeded):
        FallbackLLM(primary, fallback).generate(task="vision", prompt="봉투", schema=BeanDraft, image=b"x")


class RecordingGuard:
    def __init__(self, exhausted: set[str]):
        self.seen: list[str] = []
        self.exhausted = exhausted

    def consume(self, model: str) -> None:
        self.seen.append(model)
        if model in self.exhausted:
            raise QuotaExceeded(model)


def test_quota_is_checked_before_the_provider_is_called():
    inner = FakeLLM(provider="gemini")
    guard = RecordingGuard(exhausted={"gemini-text"})

    with pytest.raises(QuotaExceeded):
        QuotaGuardedLLM(inner, guard).generate(task="text", prompt=PROMPT, schema=TagSuggestion)

    assert guard.seen == ["gemini-text"]
    assert inner.calls == []
