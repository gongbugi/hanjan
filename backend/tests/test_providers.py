import json
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from hanjan.llm.base import LLMBadOutput, LLMUnavailable, QuotaExceeded
from hanjan.llm.gemini import GeminiLLM
from hanjan.llm.groq import GroqLLM
from hanjan.llm.schemas import TagSuggestion


# --- Gemini ---
class FakeModels:
    def __init__(self, outcome):
        self.outcome = outcome
        self.kwargs: dict = {}

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return SimpleNamespace(text=self.outcome)


def gemini(outcome):
    models = FakeModels(outcome)
    return GeminiLLM("key", "vision-model", "text-model", client=SimpleNamespace(models=models)), models


def test_gemini_parses_structured_json_and_requests_schema():
    llm, models = gemini('{"tags": ["fruity.berry"]}')

    result = llm.generate(task="text", prompt="p", schema=TagSuggestion)

    assert result.data.tags == ["fruity.berry"]
    assert (result.provider, result.model) == ("gemini", "text-model")
    assert models.kwargs["config"].response_mime_type == "application/json"
    assert models.kwargs["config"].response_schema is not None


def test_gemini_sends_the_image_before_the_prompt_to_the_vision_model():
    llm, models = gemini('{"tags": []}')

    llm.generate(task="vision", prompt="p", schema=TagSuggestion, image=b"\xff\xd8jpeg", image_mime="image/jpeg")

    assert models.kwargs["model"] == "vision-model"
    assert models.kwargs["contents"][0].inline_data.mime_type == "image/jpeg"
    assert models.kwargs["contents"][1] == "p"


@pytest.mark.parametrize(("code", "expected"), [(429, QuotaExceeded), (404, LLMUnavailable), (503, LLMUnavailable)])
def test_gemini_maps_api_errors(code, expected):
    llm, _ = gemini(errors.APIError(code, {"error": {"code": code, "message": "x", "status": "S"}}))
    with pytest.raises(expected):
        llm.generate(task="text", prompt="p", schema=TagSuggestion)


@pytest.mark.parametrize("text", ['{"labels": 1}', None, ""])
def test_gemini_unusable_output_is_bad_output(text):
    llm, _ = gemini(text)
    with pytest.raises(LLMBadOutput):
        llm.generate(task="text", prompt="p", schema=TagSuggestion)


# --- Groq ---
def groq(handler, *, vision_model: str | None = "vision-model"):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return GroqLLM("key", "text-model", vision_model, client=client)


def ok(content: str):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_groq_sends_openai_compatible_request_with_image():
    seen = {}

    def handler(request: httpx.Request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return ok('{"tags": ["fruity.citrus"]}')

    result = groq(handler).generate(task="vision", prompt="p", schema=TagSuggestion, image=b"abc")

    assert result.data.tags == ["fruity.citrus"]
    assert seen["auth"] == "Bearer key"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_groq_429_is_quota():
    with pytest.raises(QuotaExceeded):
        groq(lambda r: httpx.Response(429)).generate(task="text", prompt="p", schema=TagSuggestion)


def test_groq_without_vision_model_is_unavailable_for_vision():
    with pytest.raises(LLMUnavailable):
        groq(lambda r: ok("{}"), vision_model=None).generate(task="vision", prompt="p", schema=TagSuggestion)


def test_groq_non_json_is_bad_output():
    with pytest.raises(LLMBadOutput):
        groq(lambda r: ok("not json")).generate(task="text", prompt="p", schema=TagSuggestion)
