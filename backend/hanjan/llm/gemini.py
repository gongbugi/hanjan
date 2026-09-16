import httpx
from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from hanjan.llm.base import LLMBadOutput, LLMError, LLMResult, LLMUnavailable, QuotaExceeded, T, Task


class GeminiLLM:
    """Gemini API. 무료 등급 입력은 구글 제품 개선에 쓰일 수 있다 — 송장 등 개인정보가 섞인 사진을 보내지 않는다."""

    provider = "gemini"

    def __init__(self, api_key: str, vision_model: str, text_model: str, client: genai.Client | None = None):
        self._client = client or genai.Client(api_key=api_key)
        self._models: dict[str, str] = {"vision": vision_model, "text": text_model}

    def model_for(self, task: Task) -> str | None:
        return self._models.get(task)

    def generate(
        self, *, task: Task, prompt: str, schema: type[T], image=None, image_mime="image/jpeg"
    ) -> LLMResult[T]:
        model = self._models[task]
        contents: list = []
        if image is not None:
            contents.append(types.Part.from_bytes(data=image, mime_type=image_mime))
        contents.append(prompt)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.2,
        )
        try:
            response = self._client.models.generate_content(model=model, contents=contents, config=config)
        except errors.APIError as e:
            if e.code == 429:
                raise QuotaExceeded(f"gemini {model}: 429 {e.message}") from e
            if e.code == 404 or (e.code is not None and e.code >= 500):
                # 404는 대개 모델 ID 폐기 — 예비로 넘기고 설정을 고치라는 신호
                raise LLMUnavailable(f"gemini {model}: {e.code} {e.message}") from e
            raise LLMError(f"gemini {model}: {e.code} {e.message}") from e
        except httpx.HTTPError as e:
            raise LLMUnavailable(f"gemini {model}: 연결 실패 {e}") from e

        text = response.text
        if not text:
            raise LLMBadOutput(f"gemini {model}: 빈 응답 (안전 필터로 막혔을 수 있음)")
        try:
            data = schema.model_validate_json(text)
        except ValidationError as e:
            raise LLMBadOutput(f"gemini {model}: 스키마 불일치 — {e}") from e
        return LLMResult(data=data, provider=self.provider, model=model)
