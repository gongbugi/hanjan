from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from hanjan.collect.sources import FETCHERS, Fetcher, RobotsDisallowed, SourceConfig
from hanjan.embedding.base import Embedder
from hanjan.llm import prompts
from hanjan.llm.base import LLM, LLMBadOutput, LLMError, LLMUnavailable, QuotaExceeded
from hanjan.llm.schemas import CatalogNormalized
from hanjan.models import CatalogBean
from hanjan.services.documents import catalog_text, delete_documents, upsert_document


@dataclass
class CollectResult:
    fetched: int = 0
    new: int = 0
    updated: int = 0
    normalized: int = 0
    skipped: int = 0
    failed: int = 0
    pending: int = 0
    errors: list[str] = field(default_factory=list)


def collect(
    session: Session,
    *,
    sources: list[SourceConfig],
    fetcher: Fetcher,
    llm: LLM,
    embedder: Embedder,
    normalize_limit: int = 50,
    now: datetime | None = None,
) -> CollectResult:
    now = now or datetime.now(tz=UTC)
    result = CollectResult()

    for src in (s for s in sources if s.enabled):
        try:
            items = FETCHERS[src.kind](fetcher, src)
        except (httpx.HTTPError, RobotsDisallowed, ValueError, KeyError) as e:
            result.errors.append(f"{src.name}: {e}")
            continue
        if not items:
            # 사이트 구조가 바뀌어 선택자가 빗나간 경우가 대부분이다. 전부 판매 종료로 처리하지 않는다
            result.errors.append(f"{src.name}: 상품 0개 — 선택자나 주소를 확인하세요")
            continue

        seen: set[str] = set()
        for it in items:
            if it.url in seen:
                continue
            seen.add(it.url)
            existing = session.scalar(select(CatalogBean).where(CatalogBean.source_url == it.url))
            if existing is None:
                session.add(
                    CatalogBean(
                        source_name=it.source_name,
                        source_url=it.url,
                        title=it.title,
                        raw_text=it.text,
                        price=it.price,
                        available=it.available,
                        status="pending",
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                )
                result.new += 1
                continue
            changed = existing.title != it.title or existing.raw_text != it.text
            existing.title, existing.price, existing.available = it.title, it.price, it.available
            existing.last_seen_at = now
            if changed:
                existing.raw_text = it.text
                existing.status = "pending"
                result.updated += 1

        # 이번 목록에서 사라진 상품은 판매 종료로 본다 (가져오기에 성공한 소스만)
        session.execute(
            update(CatalogBean)
            .where(
                CatalogBean.source_name == src.name,
                CatalogBean.source_url.not_in(seen),
                CatalogBean.available.is_(True),
            )
            .values(available=False)
        )
        result.fetched += len(seen)
        session.commit()

    normalize_pending(session, llm=llm, embedder=embedder, result=result, limit=normalize_limit)
    return result


def normalize_pending(
    session: Session, *, llm: LLM, embedder: Embedder, result: CollectResult, limit: int
) -> None:
    pending = list(
        session.scalars(
            select(CatalogBean).where(CatalogBean.status == "pending").order_by(CatalogBean.id).limit(limit)
        )
    )
    for item in pending:
        try:
            r = llm.generate(
                task="text",
                prompt=prompts.catalog_prompt(source_name=item.source_name, title=item.title, text=item.raw_text),
                schema=CatalogNormalized,
            )
        except (QuotaExceeded, LLMUnavailable) as e:
            # 한도 소진 — 남은 건 pending으로 두고 다음 실행(태평양 자정 이후)에 이어서 한다
            result.errors.append(f"정리 중단: {e}")
            break
        except LLMBadOutput as e:
            item.status = "failed"
            result.failed += 1
            result.errors.append(f"{item.source_url}: {e}")
            session.commit()
            continue
        except LLMError as e:
            result.errors.append(f"정리 중단: {e}")
            break

        data = r.data
        item.normalized = data.model_dump()
        if not data.is_coffee_bean:
            item.status = "skipped"
            delete_documents(session, kind="catalog", ref_id=item.id)
            result.skipped += 1
        else:
            item.status = "normalized"
            item.country, item.processing = data.country, data.processing
            upsert_document(session, embedder, kind="catalog", ref_id=item.id, content=catalog_text(item))
            result.normalized += 1
        session.commit()  # 한 건씩 — 중간에 한도가 끊겨도 앞선 결과는 남는다

    result.pending = session.scalar(
        select(func.count()).select_from(CatalogBean).where(CatalogBean.status == "pending")
    ) or 0
