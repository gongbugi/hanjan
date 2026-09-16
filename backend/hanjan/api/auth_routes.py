from typing import Annotated

from fastapi import APIRouter, Depends

from hanjan.api.deps import SettingsDep, current_user
from hanjan.auth import AuthUser
from hanjan.schemas import MeOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=MeOut)
def me(user: Annotated[AuthUser, Depends(current_user)], settings: SettingsDep):
    """프론트의 관리자 UI 표시용. 화면 숨김은 편의일 뿐, 실제 차단은 require_admin이 한다."""
    return MeOut(uid=user.uid, is_admin=user.uid in settings.admin_uids)
