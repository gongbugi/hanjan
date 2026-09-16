from hanjan.llm.base import LLM, LLMResult, LLMUnavailable, QuotaExceeded, T, Task
from hanjan.quota import QuotaGuard


class QuotaGuardedLLM:
    """호출 전에 모델별 하루 한도를 먼저 차감한다. 한도를 넘으면 제공자를 부르지 않는다."""

    def __init__(self, inner: LLM, guard: QuotaGuard):
        self.inner = inner
        self.guard = guard
        self.provider = inner.provider

    def model_for(self, task: Task) -> str | None:
        return self.inner.model_for(task)

    def generate(self, *, task: Task, prompt: str, schema: type[T], image=None, image_mime="image/jpeg"):
        model = self.inner.model_for(task)
        if model is None:
            raise LLMUnavailable(f"{self.provider}: '{task}' 작업 모델이 설정되지 않음")
        self.guard.consume(model)
        return self.inner.generate(task=task, prompt=prompt, schema=schema, image=image, image_mime=image_mime)


class FallbackLLM:
    """주 제공자가 한도·연결 문제로 막히면 예비 제공자로. 출력 품질 문제(LLMBadOutput)는 넘기지 않는다."""

    def __init__(self, primary: LLM, fallback: LLM | None):
        self.primary = primary
        self.fallback = fallback
        self.provider = primary.provider

    def model_for(self, task: Task) -> str | None:
        return self.primary.model_for(task) or (self.fallback.model_for(task) if self.fallback else None)

    def generate(
        self, *, task: Task, prompt: str, schema: type[T], image=None, image_mime="image/jpeg"
    ) -> LLMResult[T]:
        try:
            return self.primary.generate(
                task=task, prompt=prompt, schema=schema, image=image, image_mime=image_mime
            )
        except (QuotaExceeded, LLMUnavailable) as first:
            if self.fallback is None or self.fallback.model_for(task) is None:
                raise
            try:
                return self.fallback.generate(
                    task=task, prompt=prompt, schema=schema, image=image, image_mime=image_mime
                )
            except (QuotaExceeded, LLMUnavailable) as second:
                raise type(second)(f"주 제공자: {first} / 예비 제공자: {second}") from second
