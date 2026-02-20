from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.admin import router as admin_router
from backend.app.api.query import router as query_router
from backend.app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="OpenCity AI",
    version="0.1.0",
    description="Multi-tenant civic knowledge retrieval API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router, prefix="/v1", tags=["query"])
app.include_router(admin_router, prefix="/v1/admin", tags=["admin"])


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
