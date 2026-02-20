from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)

from backend.app.config import get_settings

settings = get_settings()

client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection() -> None:
    try:
        client.get_collection(settings.qdrant_collection)
    except Exception:  # noqa: BLE001
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=settings.vector_size, distance=Distance.COSINE),
        )


def search(city_id: str, query_embedding: list[float], top_k: int = 8):
    ensure_collection()
    return client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_embedding,
        query_filter=Filter(
            must=[FieldCondition(key="city_id", match=MatchValue(value=city_id))]
        ),
        with_payload=True,
        with_vectors=False,
        limit=top_k,
    )


def upsert_points(points: list[PointStruct]) -> None:
    if not points:
        return
    client.upsert(collection_name=settings.qdrant_collection, points=points)


def delete_city_uri_points(city_id: str, uri: str) -> None:
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(key="city_id", match=MatchValue(value=city_id)),
                    FieldCondition(key="uri", match=MatchValue(value=uri)),
                ]
            )
        ),
    )


def collection_health() -> dict:
    try:
        info = client.get_collection(settings.qdrant_collection)
        return {
            "status": "ready",
            "points_count": int(info.points_count or 0),
            "indexed_vectors_count": int(info.indexed_vectors_count or 0),
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "unavailable", "error": str(exc)[:200]}
