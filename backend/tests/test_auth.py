import time

import pytest

from hanjan import auth
from hanjan.auth import FirebaseTokenVerifier, InvalidToken

PROJECT = "hanjan-prod"


def claims(**overrides):
    base = {
        "iss": f"https://securetoken.google.com/{PROJECT}",
        "aud": PROJECT,
        "sub": "firebase-uid-1",
        "exp": time.time() + 3600,
    }
    return {**base, **overrides}


def patch_verify(monkeypatch, result):
    calls = []

    def fake_verify(token, request, audience=None, clock_skew_in_seconds=0):
        calls.append((token, audience))
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(auth.id_token, "verify_firebase_token", fake_verify)
    return calls


def test_uid_comes_from_the_verified_token_and_is_cached(monkeypatch):
    calls = patch_verify(monkeypatch, claims())
    verifier = FirebaseTokenVerifier(PROJECT)

    assert verifier.verify("token-1").uid == "firebase-uid-1"
    assert verifier.verify("token-1").uid == "firebase-uid-1"
    assert calls == [("token-1", PROJECT)]


def test_token_from_another_project_is_rejected(monkeypatch):
    patch_verify(monkeypatch, claims(iss="https://securetoken.google.com/someone-else"))
    with pytest.raises(InvalidToken, match="발급자"):
        FirebaseTokenVerifier(PROJECT).verify("token-1")


def test_library_validation_error_becomes_invalid_token(monkeypatch):
    patch_verify(monkeypatch, ValueError("Token expired"))
    with pytest.raises(InvalidToken):
        FirebaseTokenVerifier(PROJECT).verify("token-1")


def test_expired_cache_entry_is_verified_again(monkeypatch):
    calls = patch_verify(monkeypatch, claims(exp=time.time() - 1))
    verifier = FirebaseTokenVerifier(PROJECT)
    verifier.verify("token-1")
    verifier.verify("token-1")
    assert len(calls) == 2
