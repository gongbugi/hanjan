"""Groq — Gemini가 막혔을 때의 예비 제공자. OpenAI 호환 엔드포인트를 그대로 부른다.

한국어 봉투 인식 품질은 검증 전이다. 비전 모델 ID를 비워두면 봉투 인식은 예비로 넘어가지 않는다.
"""

import base64
import json

import httpx
from pydantic import ValidationError

from hanjan.llm.base import LLMBadOutput, LLMError, LLMResult, LLMUnavailable, QuotaExceeded, T, Task

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqLLM:
    provider = "groq"

    def __init__(
        self,
        api_key: str,
        text_model: str | None,
        vision_model: str | None,
        client: httpx.Client | None = None,
    ):
        self._key = api_key
        self._models: dict[str, str | None] = {"text": text_model, "vision": vision_model}
        self._client = client or httpx.Client(timeout=60)

    def model_for(self, task: Task) -> str | None:
        return self._models.get(task)

    def generate(
        self, *, task: Task, prompt: str, schema: type[T], image=None, image_mime="image/jpeg"
    ) -> LLMResult[T]:
        model = self._models.get(task)
        if not model:
            raise LLMUnavailable(f"groq: '{task}' 작업 모델이 설정되지 않음")
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        instruction = f"{prompt}\n\n다음 JSON 스키마에 맞는 JSON 객체 하나로만 답한다.\n{schema_json}"
        content: str | list[dict] = instruction
        if image is not None:
            b64 = base64.b64encode(image).decode()
            content = [
                {"type": "text", "text": instruction},
                {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{b64}"}},
            ]
        body = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        try:
            r = self._client.post(GROQ_CHAT_URL, json=body, headers={"Authorization": f"Bearer {self._key}"})
        except httpx.HTTPError as e:
            raise LLMUnavailable(f"groq {model}: 연결 실패 {e}") from e
        if r.status_code == 429:
            raise QuotaExceeded(f"groq {model}: 429")
        if r.status_code == 404 or r.status_code >= 500:
            raise LLMUnavailable(f"groq {model}: {r.status_code}")
        if r.status_code >= 400:
            raise LLMError(f"groq {model}: {r.status_code} {r.text[:300]}")
        try:
            text = r.json()["choices"][0]["message"]["content"]
            data = schema.model_validate_json(text)
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as e:
            raise LLMBadOutput(f"groq {model}: 응답 형식 불일치 — {e}") from e
        return LLMResult(data=data, provider=self.provider, model=model)
