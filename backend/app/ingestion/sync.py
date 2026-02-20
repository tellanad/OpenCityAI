import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml
from qdrant_client.models import PointStruct

from backend.app.config import get_settings
from backend.app.ingestion.chunk import chunk_text
from backend.app.ingestion.crawl import fetch_url
from backend.app.ingestion.parse import extract_text
from backend.app.rag.retrieve import embed_text
from backend.app.vector.qdrant import delete_city_uri_points, ensure_collection, upsert_points

settings = get_settings()


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _state_file(city_id: str) -> Path:
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    return settings.state_dir / f"{city_id}.json"


def _load_state(city_id: str) -> dict:
    p = _state_file(city_id)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_state(city_id: str, state: dict) -> None:
    _state_file(city_id).write_text(json.dumps(state, indent=2), encoding="utf-8")


def _city_sources(city_id: str) -> list[dict]:
    source_file = settings.city_dir / city_id / "sources.yaml"
    if not source_file.exists():
        return []
    data = yaml.safe_load(source_file.read_text(encoding="utf-8")) or {}
    return data.get("sources", [])


def sync_city(city_id: str) -> dict:
    ensure_collection()
    state = _load_state(city_id)
    sources = _city_sources(city_id)

    stats = {
        "city_id": city_id,
        "sources_total": len(sources),
        "sources_updated": 0,
        "sources_skipped": 0,
        "chunks_upserted": 0,
        "errors": [],
    }

    now = datetime.now(UTC).isoformat()

    for src in sources:
        uri = src.get("uri", "").strip()
        if not uri:
            continue

        try:
            raw, content_type = fetch_url(uri)
            content_hash = _hash_bytes(raw)

            if state.get(uri) == content_hash:
                stats["sources_skipped"] += 1
                continue

            title, text = extract_text(uri, raw, content_type)
            chunks = chunk_text(text)
            if not chunks:
                stats["sources_skipped"] += 1
                state[uri] = content_hash
                continue

            delete_city_uri_points(city_id=city_id, uri=uri)

            points: list[PointStruct] = []
            for idx, chunk in enumerate(chunks):
                vec = embed_text(chunk)
                point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{city_id}:{uri}:{idx}"))
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vec,
                        payload={
                            "city_id": city_id,
                            "doc_id": hashlib.sha1(uri.encode("utf-8")).hexdigest(),
                            "chunk_id": f"{uri}#{idx}",
                            "chunk_index": idx,
                            "uri": uri,
                            "title": title,
                            "text": chunk,
                            "content_hash": content_hash,
                            "updated_at": now,
                        },
                    )
                )

            upsert_points(points)
            state[uri] = content_hash
            stats["sources_updated"] += 1
            stats["chunks_upserted"] += len(points)

        except Exception as exc:  # noqa: BLE001
            stats["errors"].append({"uri": uri, "error": str(exc)[:500]})

    _save_state(city_id, state)
    return stats
