"""테스트·로컬 개발용 결정론 임베더. 모델 없이 '겹치는 단어가 많을수록 가깝다'만 흉내 낸다."""

import hashlib
import math
import re

from hanjan.embedding.e5 import PASSAGE_PREFIX, QUERY_PREFIX

_WORD = re.compile(r"[0-9a-zA-Z가-힣]+")


def _features(text: str) -> list[str]:
    body = text.removeprefix(PASSAGE_PREFIX).removeprefix(QUERY_PREFIX).lower()
    feats: list[str] = []
    for word in _WORD.findall(body):
        feats.append(word)
        if len(word) >= 3:  # 한국어 어미·조사 차이를 흡수하려고 글자 2-gram도 쓴다
            feats.extend(word[i : i + 2] for i in range(len(word) - 1))
    return feats


class FakeEmbedder:
    def __init__(self, dim: int = 384, model_id: str = "fake-hash-embedder"):
        self.dim = dim
        self.model_id = model_id

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for feat in _features(text):
            h = hashlib.blake2b(feat.encode(), digest_size=8).digest()
            idx = int.from_bytes(h[:4], "little") % self.dim
            sign = 1.0 if h[4] & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
