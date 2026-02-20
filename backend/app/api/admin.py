from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.analytics.store import get_analytics_summary
from backend.app.config import get_settings
from backend.app.ingestion.sync import sync_city
from backend.app.vector.qdrant import collection_health

router = APIRouter()
settings = get_settings()


class CityCreateRequest(BaseModel):
    city_id: str = Field(min_length=2, pattern=r"^[a-z0-9_\-]+$")
    name: str = Field(min_length=2)


class SourceAddRequest(BaseModel):
    city_id: str = Field(min_length=2, pattern=r"^[a-z0-9_\-]+$")
    sources: list[str] = Field(min_length=1)


def require_admin_key(x_admin_api_key: str | None = Header(default=None)) -> None:
    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="invalid admin key")


def _city_path(city_id: str) -> Path:
    return settings.city_dir / city_id


@router.post("/cities", dependencies=[Depends(require_admin_key)])
def create_city(req: CityCreateRequest) -> dict:
    city_path = _city_path(req.city_id)
    city_path.mkdir(parents=True, exist_ok=True)

    city_yaml = city_path / "city.yaml"
    sources_yaml = city_path / "sources.yaml"

    if city_yaml.exists():
        raise HTTPException(status_code=409, detail="city already exists")

    city_yaml.write_text(
        yaml.safe_dump({"city_id": req.city_id, "name": req.name}, sort_keys=False),
        encoding="utf-8",
    )

    if not sources_yaml.exists():
        sources_yaml.write_text(yaml.safe_dump({"sources": []}, sort_keys=False), encoding="utf-8")

    return {"status": "created", "city_id": req.city_id}


@router.post("/sources", dependencies=[Depends(require_admin_key)])
def add_sources(req: SourceAddRequest) -> dict:
    city_path = _city_path(req.city_id)
    sources_yaml = city_path / "sources.yaml"

    if not city_path.exists() or not sources_yaml.exists():
        raise HTTPException(status_code=404, detail="city not found")

    data = yaml.safe_load(sources_yaml.read_text(encoding="utf-8")) or {"sources": []}
    existing = {item["uri"] for item in data.get("sources", []) if isinstance(item, dict) and "uri" in item}

    for uri in req.sources:
        if uri not in existing:
            data.setdefault("sources", []).append({"type": "url", "uri": uri})

    sources_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    return {"status": "updated", "city_id": req.city_id, "sources": len(data.get("sources", []))}


@router.post("/sync", dependencies=[Depends(require_admin_key)])
def sync(city_id: str) -> dict:
    if not _city_path(city_id).exists():
        raise HTTPException(status_code=404, detail="city not found")
    return sync_city(city_id)


@router.get("/status", dependencies=[Depends(require_admin_key)])
def status(city_id: str) -> dict:
    city_path = _city_path(city_id)
    if not city_path.exists():
        raise HTTPException(status_code=404, detail="city not found")

    sources_yaml = city_path / "sources.yaml"
    source_count = 0
    if sources_yaml.exists():
        data = yaml.safe_load(sources_yaml.read_text(encoding="utf-8")) or {}
        source_count = len(data.get("sources", []))

    return {
        "city_id": city_id,
        "sources": source_count,
        "vector_collection": collection_health(),
    }


@router.get("/analytics", dependencies=[Depends(require_admin_key)])
def analytics(
    city_id: str | None = Query(default=None, min_length=2),
    days: int = Query(default=7, ge=1, le=90),
) -> dict:
    return get_analytics_summary(city_id=city_id, days=days)
