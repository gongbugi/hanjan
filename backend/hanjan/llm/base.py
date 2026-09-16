from dataclasses import dataclass
from typing import Generic, Literal, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
Task = Literal["vision", "text"]


class LLMError(Exception):
    pass


class QuotaExceeded(LLMError):
    """하루 한도 소진 또는 제공자 429. 예비 제공자로 넘어갈 수 있다."""


class LLMUnavailable(LLMError):
    """이 작업에 쓸 모델이 설정되지 않았거나 제공자에 닿지 않는다. 예비로 넘어갈 수 있다."""


class LLMBadOutput(LLMError):
    """스키마에 맞지 않는 출력. 품질 문제라 예비로 넘기지 않고 드러낸다."""


@dataclass(frozen=True)
class LLMResult(Generic[T]):
    data: T
    provider: str
    model: str


class LLM(Protocol):
    provider: str

    def model_for(self, task: Task) -> str | None: ...

    def generate(
        self,
        *,
        task: Task,
        prompt: str,
        schema: type[T],
        image: bytes | None = None,
        image_mime: str = "image/jpeg",
    ) -> LLMResult[T]: ...
