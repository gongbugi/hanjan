from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from hanjan.api.deps import SessionDep

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz():
    """liveness — 프로세스가 살아 있는지만. DB를 보지 않는다 (DB 장애로 앱까지 재시작되면 안 된다)."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz(session: SessionDep):
    """readiness — DB에 닿을 때만 트래픽을 받는다."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as e:
        raise HTTPException(503, "DB에 연결할 수 없어요") from e
    return {"status": "ready"}
