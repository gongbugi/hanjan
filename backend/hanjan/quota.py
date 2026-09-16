from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from hanjan.llm.base import QuotaExceeded

# Gemini API의 하루 요청 한도(RPD)는 태평양 자정에 초기화된다 (공식 문서).
# 한국 시간으로는 여름(PDT) 16시, 겨울(PST) 17시.
PACIFIC = ZoneInfo("America/Los_Angeles")

_CONSUME = text(
    """
    INSERT INTO llm_usage (model, day, count) VALUES (:model, :day, 1)
    ON CONFLICT (model, day) DO UPDATE SET count = llm_usage.count + 1
    WHERE llm_usage.count < :limit
    RETURNING count
    """
)


def quota_day(now: datetime | None = None) -> date:
    now = now or datetime.now(tz=UTC)
    if now.tzinfo is None:
        raise ValueError("시간대가 없는 datetime은 받지 않는다")
    return now.astimezone(PACIFIC).date()


class QuotaGuard:
    def __init__(self, session_factory: sessionmaker[Session], limits: dict[str, int]):
        self._sessions = session_factory
        self._limits = limits

    def consume(self, model: str, now: datetime | None = None) -> None:
        limit = self._limits.get(model)
        if limit is None:
            return
        if limit <= 0:
            raise QuotaExceeded(f"{model}: 하루 한도가 0으로 설정됨")
        # 요청 트랜잭션과 분리한다 — 요청이 롤백돼도 제공자에 나간 호출은 센다
        with self._sessions() as session, session.begin():
            row = session.execute(
                _CONSUME, {"model": model, "day": quota_day(now), "limit": limit}
            ).first()
        if row is None:
            raise QuotaExceeded(f"{model}: 오늘 한도 {limit}회 소진 (태평양 자정에 초기화)")
