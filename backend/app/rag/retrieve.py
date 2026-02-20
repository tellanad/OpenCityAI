from functools import lru_cache

from fastembed import TextEmbedding

from backend.app.config import get_settings
from backend.app.vector.qdrant import ensure_collection, search

settings = get_settings()


@lru_cache(maxsize=1)
def _embedder() -> TextEmbedding:
    return TextEmbedding(model_name=settings.embedding_model)


def embed_text(text: str) -> list[float]:
    if not text.strip():
        return [0.0] * settings.vector_size
    vec = next(_embedder().embed([text]))
    return vec.tolist()


def retrieve_chunks(city_id: str, query: str, top_k: int | None = None) -> list[dict]:
    ensure_collection()
    qv = embed_text(query)
    hits = search(city_id=city_id, query_embedding=qv, top_k=top_k or settings.retrieval_top_k)

    out = []
    for h in hits:
        payload = h.payload or {}
        out.append(
            {
                "score": float(h.score),
                "text": payload.get("text", ""),
                "title": payload.get("title", "Untitled"),
                "uri": payload.get("uri", ""),
                "chunk_id": payload.get("chunk_id", ""),
                "doc_id": payload.get("doc_id", ""),
            }
        )
    return out
