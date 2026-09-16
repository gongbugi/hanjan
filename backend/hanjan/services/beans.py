from hanjan.flavor import filter_known
from hanjan.llm import prompts
from hanjan.llm.base import LLM, LLMResult
from hanjan.llm.schemas import BeanDraft, TagSuggestion

DRAFT_FIELDS = ("name", "roaster", "country", "region", "variety", "processing", "roast_level")


def clean_draft(draft: BeanDraft) -> BeanDraft:
    data = draft.model_dump()
    for field in DRAFT_FIELDS:
        value = data[field]
        data[field] = value.strip() if isinstance(value, str) and value.strip() else None
    data["bag_flavor_notes"] = [n.strip() for n in data["bag_flavor_notes"] if n and n.strip()][:20]
    return BeanDraft(**data)


def filled_fields(draft: BeanDraft) -> int:
    """채워진 칸 수 — 신뢰도를 모델에게 묻지 않고 코드가 센다."""
    return sum(getattr(draft, f) is not None for f in DRAFT_FIELDS) + (1 if draft.bag_flavor_notes else 0)


def extract_bean_draft(llm: LLM, image_jpeg: bytes) -> tuple[BeanDraft, LLMResult[BeanDraft]]:
    result = llm.generate(
        task="vision", prompt=prompts.BEAN_EXTRACT, schema=BeanDraft, image=image_jpeg, image_mime="image/jpeg"
    )
    return clean_draft(result.data), result


def suggest_tags(llm: LLM, note: str) -> tuple[list[str], list[str], LLMResult[TagSuggestion]]:
    result = llm.generate(task="text", prompt=prompts.tag_prompt(note), schema=TagSuggestion)
    kept, dropped = filter_known(result.data.tags)
    return kept, dropped, result
