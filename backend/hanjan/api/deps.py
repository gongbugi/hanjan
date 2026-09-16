from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from hanjan.auth import AuthUser, InvalidToken
from hanjan.config import Settings
from hanjan.embedding.base import Embedder
from hanjan.llm.base import LLM

_bearer = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.sessions() as session:
        yield session


def get_llm(request: Request) -> LLM:
    return request.app.state.llm


def get_embedder(request: Request) -> Embedder:
    return request.app.state.embedder


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(get_session)]
LLMDep = Annotated[LLM, Depends(get_llm)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]


def current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthUser:
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "로그인이 필요해요", headers={"WWW-Authenticate": "Bearer"}
        )
    try:
        return request.app.state.verifier.verify(credentials.credentials)
    except InvalidToken as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "토큰이 유효하지 않아요", headers={"WWW-Authenticate": "Bearer"}
        ) from e


def require_admin(user: Annotated[AuthUser, Depends(current_user)], settings: SettingsDep) -> AuthUser:
    """관리자 판정은 이 함수 한 곳에서만 한다.

    - 쓰기 라우터(api/admin.py) 전체에 라우터 단위로 걸려 있다 — 경로·메서드를 if로 거르지 않는다
    - 관리자는 서버 설정의 허용 목록으로만 정한다 — 가입 API가 없다
    - 인증 방식을 바꾸거나(Cloudflare Access 등) 앞단을 추가해도 고칠 곳은 여기뿐이다
    """
    if user.uid not in settings.admin_uids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "관리자만 쓸 수 있어요")
    return user
