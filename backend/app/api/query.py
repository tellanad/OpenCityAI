import time
import uuid
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.analytics.store import record_feedback_event, record_query_event
from backend.app.rag.pipeline import run_rag
from backend.app.rag.stream import stream_answer

router = APIRouter()
FeedbackReason = Literal["missing_info", "incorrect", "unclear", "outdated", "other"]


class QueryRequest(BaseModel):
    city_id: str = Field(min_length=2)
    query: str = Field(min_length=2)
    session_id: str | None = None


class FeedbackRequest(BaseModel):
    city_id: str = Field(min_length=2)
    query_id: str = Field(min_length=8)
    helpful: bool
    reason: FeedbackReason | None = None
    escalation_requested: bool = False
    comment: str | None = Field(default=None, max_length=1000)
    session_id: str | None = None


@router.post("/query")
def query(req: QueryRequest) -> dict:
    query_id = uuid.uuid4().hex
    started = time.perf_counter()

    result = run_rag(city_id=req.city_id, query=req.query, session_id=req.session_id)

    latency_ms = int((time.perf_counter() - started) * 1000)
    meta = result.setdefault("meta", {})
    meta["query_id"] = query_id
    meta["latency_ms"] = latency_ms

    try:
        record_query_event(
            city_id=req.city_id,
            query_id=query_id,
            query_text=req.query,
            session_id=req.session_id,
            latency_ms=latency_ms,
            refused=bool(meta.get("refused", False)),
            refusal_reason=str(meta.get("reason")) if meta.get("reason") else None,
            retrieved_k=int(meta.get("retrieved_k", 0)),
            citations_count=len(result.get("citations", [])),
            model=str(meta.get("model")) if meta.get("model") else None,
        )
    except Exception:  # noqa: BLE001
        # Keep query path available even if analytics storage is temporarily unavailable.
        meta["analytics_logged"] = False

    return result


@router.post("/feedback")
def feedback(req: FeedbackRequest) -> dict:
    feedback_id = record_feedback_event(
        city_id=req.city_id,
        query_id=req.query_id,
        helpful=req.helpful,
        reason=req.reason,
        escalation_requested=req.escalation_requested,
        comment=req.comment,
        session_id=req.session_id,
    )
    return {"status": "recorded", "feedback_id": feedback_id}


@router.post("/query/stream")
async def query_stream(req: Request) -> StreamingResponse:
    body = await req.json()
    city_id = str(body.get("city_id", "")).strip()
    query = str(body.get("query", "")).strip()
    session_id = body.get("session_id")

    if not city_id or not query:
        def _bad_request():
            yield "event: error\ndata: {\"error\":\"city_id and query are required\"}\n\n"

        return StreamingResponse(_bad_request(), media_type="text/event-stream")

    return StreamingResponse(
        stream_answer(city_id=city_id, query=query, session_id=session_id),
        media_type="text/event-stream",
    )
