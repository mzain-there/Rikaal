"""Local embeddings via sentence-transformers. No API cost."""
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from .config import EMBED_MODEL


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    # Loaded once, cached for the process lifetime.
    return SentenceTransformer(EMBED_MODEL)


def embed(texts: list[str]) -> list[list[float]]:
    model = _model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def embed_one(text: str) -> list[float]:
    return embed([text])[0]


def vector_size() -> int:
    return _model().get_sentence_embedding_dimension()  # 384 for MiniLM-L6-v2
