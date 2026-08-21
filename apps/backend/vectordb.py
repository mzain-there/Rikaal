"""Thin wrapper around Qdrant for storing and retrieving knowledge chunks."""
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from .config import QDRANT_URL, COLLECTION_NAME
from .embeddings import embed, embed_one, vector_size

_client = QdrantClient(url=QDRANT_URL)


def ensure_collection() -> None:
    existing = [c.name for c in _client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        _client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size(), distance=Distance.COSINE),
        )


def add_chunks(chunks: list[str], metadata: dict | None = None) -> int:
    """Embed and store a list of text chunks with shared metadata."""
    metadata = metadata or {}
    vectors = embed(chunks)
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={"text": chunk, **metadata},
        )
        for chunk, vec in zip(chunks, vectors)
    ]
    _client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)

    
def delete_by_repo(project: str, repo: str) -> None:
    """Delete all chunks belonging to a specific project and GitHub repo."""
    qfilter = Filter(
        must=[
            FieldCondition(
                key="project",
                match=MatchValue(value=project),
            ),
            FieldCondition(
                key="repo",
                match=MatchValue(value=repo),
            ),
        ]
    )

    _client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=qfilter,
    )

def search(query: str, top_k: int = 5, project: str | None = None) -> list[dict]:
    """Return the top_k most relevant chunks, optionally scoped to a project."""
    qfilter = None
    if project:
        qfilter = Filter(
            must=[FieldCondition(key="project", match=MatchValue(value=project))]
        )
    result = _client.query_points(
    collection_name=COLLECTION_NAME,
    query=embed_one(query),
    limit=top_k,
    query_filter=qfilter,
    )
    hits = result.points
    return [
        {"text": h.payload.get("text", ""), "score": h.score, "payload": h.payload}
        for h in hits
    ]
