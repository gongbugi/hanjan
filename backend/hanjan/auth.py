"""인증. 신원(uid)은 오직 검증된 토큰에서만 꺼낸다 — 요청 본문으로 받은 uid는 믿지 않는다.

관리자 판정은 여기가 아니라 api/deps.py의 require_admin 한 곳에서 한다.
"""

import time
from dataclasses import dataclass
from typing import Protocol

from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from hanjan.config import Settings


@dataclass(frozen=True)
class AuthUser:
    uid: str


class InvalidToken(Exception):
    pass


class TokenVerifier(Protocol):
    def verify(self, token: str) -> AuthUser: ...


class DevTokenVerifier:
    """로컬 개발·테스트 전용. 운영 설정에서는 Settings 검증이 막는다."""

    def __init__(self, tokens: dict[str, str]):
        self._tokens = tokens

    def verify(self, token: str) -> AuthUser:
        uid = self._tokens.get(token)
        if uid is None:
            raise InvalidToken("알 수 없는 개발용 토큰")
        return AuthUser(uid)


class FirebaseTokenVerifier:
    def __init__(self, project_id: str, *, max_cache: int = 128):
        self._project_id = project_id
        self._request = google_requests.Request()
        self._cache: dict[str, tuple[float, AuthUser]] = {}
        self._max_cache = max_cache

    def verify(self, token: str) -> AuthUser:
        now = time.time()
        hit = self._cache.get(token)
        if hit is not None and hit[0] > now:
            return hit[1]
        try:
            claims = id_token.verify_firebase_token(token, self._request, audience=self._project_id)
        except (ValueError, google_exceptions.GoogleAuthError) as e:
            raise InvalidToken(str(e)) from e
        if not claims:
            raise InvalidToken("빈 토큰")
        # verify_firebase_token은 발급자를 따로 보지 않는다 — 직접 확인한다
        if claims.get("iss") != f"https://securetoken.google.com/{self._project_id}":
            raise InvalidToken("발급자 불일치")
        uid = claims.get("sub")
        if not uid:
            raise InvalidToken("sub 없음")
        user = AuthUser(uid)
        if len(self._cache) >= self._max_cache:
            self._cache.clear()
        self._cache[token] = (float(claims["exp"]), user)
        return user


def build_verifier(settings: Settings) -> TokenVerifier:
    if settings.auth_mode == "dev":
        return DevTokenVerifier(settings.dev_tokens)
    if not settings.firebase_project_id:
        raise ValueError("auth_mode=firebase에는 firebase_project_id가 필요하다")
    return FirebaseTokenVerifier(settings.firebase_project_id)
