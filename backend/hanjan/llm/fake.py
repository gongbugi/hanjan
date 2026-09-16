"""키 없이 돌리는 가짜 LLM. 테스트와 로컬 개발(`HANJAN_LLM_MODE=fake`)에서 쓴다.

기본 응답은 흉내일 뿐이다. 테스트는 handlers로 원하는 응답(엉뚱한 태그, 없는 근거 id 등)을 주입한다.

아래 표는 **테스트가 실제로 단언하는 것만** 남긴다: 수집 파이프라인 테스트가 산지·가공 추출과
"원두가 아닌 상품은 건너뛴다"를 확인한다. 그 밖의 그럴듯함은 넣지 않는다.
"""

import json
from collections.abc import Callable

from pydantic import ValidationError

from hanjan.llm.base import LLMBadOutput, LLMResult, LLMUnavailable, T, Task

Handler = Callable[[str, bytes | None], dict]


def between(prompt: str, start: str, end: str = "<<END>>") -> str:
    i = prompt.find(start)
    if i < 0:
        return ""
    i += len(start)
    j = prompt.find(end, i)
    return prompt[i : j if j >= 0 else None].strip()


_COUNTRIES = {
    "에티오피아": "Ethiopia",
    "ethiopia": "Ethiopia",
    "케냐": "Kenya",
    "kenya": "Kenya",
    "콜롬비아": "Colombia",
    "colombia": "Colombia",
    "과테말라": "Guatemala",
    "guatemala": "Guatemala",
    "브라질": "Brazil",
    "brazil": "Brazil",
}
_PROCESSING = {
    "워시드": "Washed",
    "washed": "Washed",
    "내추럴": "Natural",
    "natural": "Natural",
    "허니": "Honey",
    "honey": "Honey",
}
_NOT_BEAN = ("드립백", "캡슐", "머그", "필터", "굿즈", "drip bag")


def _bean_draft(prompt: str, image: bytes | None) -> dict:
    return {
        "name": "개발용 원두",
        "roaster": None,
        "country": "Ethiopia",
        "region": "Yirgacheffe",
        "variety": None,
        "processing": "Washed",
        "roast_level": None,
        "bag_flavor_notes": ["자스민", "레몬"],
    }


def _tags(prompt: str, image: bytes | None) -> dict:
    """메모를 읽지 않는다 — 목록 밖 태그를 버리는 건 코드(flavor.filter_known)의 일이고,
    그걸 검사하는 테스트는 handler를 직접 넣는다 (tests/test_api_records.py)."""
    return {"tags": ["fruity.citrus", "floral.floral"]}


def _catalog(prompt: str, image: bytes | None) -> dict:
    title = between(prompt, "상품명:", "\n")
    low = (title + " " + between(prompt, "<<PAGE>>")).lower()
    empty = {k: None for k in ("name", "roaster", "country", "region", "variety", "processing", "roast_level")}
    if any(word in low for word in _NOT_BEAN):
        return {"is_coffee_bean": False, **empty, "flavor_notes": []}
    return {
        "is_coffee_bean": True,
        **empty,
        "name": title or None,
        "country": next((v for k, v in _COUNTRIES.items() if k in low), None),
        "processing": next((v for k, v in _PROCESSING.items() if k in low), None),
        "flavor_notes": [],
    }


def _reasons(prompt: str, image: bytes | None) -> dict:
    candidates = json.loads(between(prompt, "<<CANDIDATES>>") or "[]")
    items = []
    for c in candidates:
        ids = [e["brew_id"] for e in c.get("evidence", [])][:2]
        items.append(
            {
                "candidate_id": c["candidate_id"],
                "reason": f"높게 평가한 기록 {len(ids)}건과 비슷한 원두예요.",
                "evidence_brew_ids": ids,
            }
        )
    return {"items": items}


DEFAULT_HANDLERS: dict[str, Handler] = {
    "BeanDraft": _bean_draft,
    "TagSuggestion": _tags,
    "CatalogNormalized": _catalog,
    "ReasonBatch": _reasons,
}


class FakeLLM:
    def __init__(
        self,
        handlers: dict[str, Handler] | None = None,
        *,
        provider: str = "fake",
        vision: bool = True,
        text: bool = True,
        error: Exception | None = None,
    ):
        self.provider = provider
        self._handlers = {**DEFAULT_HANDLERS, **(handlers or {})}
        self._tasks = {"vision": vision, "text": text}
        self.error = error
        self.calls: list[tuple[Task, str]] = []

    def set_handler(self, schema_name: str, handler: Handler) -> None:
        self._handlers[schema_name] = handler

    def model_for(self, task: Task) -> str | None:
        return f"{self.provider}-{task}" if self._tasks[task] else None

    def generate(
        self, *, task: Task, prompt: str, schema: type[T], image=None, image_mime="image/jpeg"
    ) -> LLMResult[T]:
        model = self.model_for(task)
        if model is None:
            raise LLMUnavailable(f"{self.provider}: '{task}' 작업 모델 없음")
        self.calls.append((task, schema.__name__))
        if self.error is not None:
            raise self.error
        handler = self._handlers.get(schema.__name__)
        if handler is None:
            raise LLMBadOutput(f"FakeLLM: {schema.__name__} 응답이 정의되지 않음")
        try:
            data = schema.model_validate(handler(prompt, image))
        except ValidationError as e:
            raise LLMBadOutput(str(e)) from e
        return LLMResult(data=data, provider=self.provider, model=model)
