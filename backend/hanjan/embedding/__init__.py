from hanjan.config import Settings
from hanjan.embedding.base import Embedder


def build_embedder(settings: Settings) -> Embedder:
    if settings.embedding_mode == "fake":
        from hanjan.embedding.fake import FakeEmbedder

        return FakeEmbedder(dim=settings.embedding_dim)
    from hanjan.embedding.e5 import E5Embedder

    return E5Embedder(settings.embedding_model, settings.embedding_dim, settings.embedding_cache_dir)
