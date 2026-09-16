"""multilingual-e5 계열 로컬 임베더.

e5는 입력 앞에 `query: ` / `passage: ` 접두어가 필수다. 빠뜨려도 에러가 나지 않고 검색 품질만 조용히 떨어진다.
그래서 접두어는 호출부가 아니라 이 클래스 안에서만 붙인다.
"""

PASSAGE_PREFIX = "passage: "
QUERY_PREFIX = "query: "


def as_passage(text: str) -> str:
    t = text.strip()
    if t.startswith(QUERY_PREFIX):
        raise ValueError("문서에 query: 접두어가 붙어 있다 — 호출부가 접두어를 직접 붙이지 말 것")
    return t if t.startswith(PASSAGE_PREFIX) else PASSAGE_PREFIX + t


def as_query(text: str) -> str:
    t = text.strip()
    if t.startswith(PASSAGE_PREFIX):
        raise ValueError("질의에 passage: 접두어가 붙어 있다 — 호출부가 접두어를 직접 붙이지 말 것")
    return t if t.startswith(QUERY_PREFIX) else QUERY_PREFIX + t


class E5Embedder:
    def __init__(self, model_id: str, expected_dim: int, cache_dir: str | None = None):
        from sentence_transformers import SentenceTransformer  # 운영 이미지에만 설치 (extra: embed)

        self.model_id = model_id
        self._model = SentenceTransformer(model_id, cache_folder=cache_dir, device="cpu")
        # sentence-transformers 최신판은 get_embedding_dimension, 구버전은 get_sentence_embedding_dimension
        get_dim = getattr(self._model, "get_embedding_dimension", None) or self._model.get_sentence_embedding_dimension
        dim = get_dim()
        if dim != expected_dim:
            raise RuntimeError(
                f"{model_id} 차원 {dim} ≠ 설정 {expected_dim}. 모델을 바꿨다면 마이그레이션과 재임베딩이 필요하다"
            )
        self.dim = dim

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode([as_passage(t) for t in texts], normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([as_query(text)], normalize_embeddings=True)[0].tolist()
