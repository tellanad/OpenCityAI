import hashlib
import json
import threading
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any

from backend.app.config import get_settings

settings = get_settings()
_LOCK = threading.Lock()


def _events_path() -> Path:
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    return settings.state_dir / "analytics_events.jsonl"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _append_event(event: dict[str, Any]) -> None:
    line = json.dumps(event, ensure_ascii=True)
    with _LOCK:
        with _events_path().open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def _iter_events() -> list[dict[str, Any]]:
    path = _events_path()
    if not path.exists():
        return []

    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def record_query_event(
    *,
    city_id: str,
    query_id: str,
    query_text: str,
    session_id: str | None,
    latency_ms: int,
    refused: bool,
    refusal_reason: str | None,
    retrieved_k: int,
    citations_count: int,
    model: str | None,
) -> str:
    event_id = uuid.uuid4().hex
    query_hash = hashlib.sha256(query_text.strip().lower().encode("utf-8")).hexdigest()

    _append_event(
        {
            "event_id": event_id,
            "event_type": "query",
            "timestamp": _utc_now(),
            "city_id": city_id,
            "query_id": query_id,
            "session_id": session_id,
            "query_hash": query_hash,
            "latency_ms": latency_ms,
            "refused": bool(refused),
            "refusal_reason": refusal_reason,
            "retrieved_k": int(retrieved_k),
            "citations_count": int(citations_count),
            "model": model,
        }
    )

    return event_id


def record_feedback_event(
    *,
    city_id: str,
    query_id: str,
    helpful: bool,
    reason: str | None,
    escalation_requested: bool,
    comment: str | None,
    session_id: str | None,
) -> str:
    event_id = uuid.uuid4().hex
    clean_comment = (comment or "").strip()
    if len(clean_comment) > 1000:
        clean_comment = clean_comment[:1000]

    _append_event(
        {
            "event_id": event_id,
            "event_type": "feedback",
            "timestamp": _utc_now(),
            "city_id": city_id,
            "query_id": query_id,
            "session_id": session_id,
            "helpful": bool(helpful),
            "reason": reason,
            "escalation_requested": bool(escalation_requested),
            "comment": clean_comment,
        }
    )

    return event_id


def get_analytics_summary(city_id: str | None = None, days: int = 7) -> dict[str, Any]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    events = _iter_events()

    def in_scope(event: dict[str, Any]) -> bool:
        if city_id and event.get("city_id") != city_id:
            return False
        ts = event.get("timestamp")
        if not isinstance(ts, str):
            return False
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            return False
        return dt >= cutoff

    scoped = [e for e in events if in_scope(e)]
    query_events = [e for e in scoped if e.get("event_type") == "query"]
    feedback_events = [e for e in scoped if e.get("event_type") == "feedback"]

    total_queries = len(query_events)
    total_feedback = len(feedback_events)

    feedback_by_query: dict[str, dict[str, Any]] = {}
    for fb in feedback_events:
        qid = str(fb.get("query_id") or "")
        if not qid:
            continue
        feedback_by_query[qid] = fb

    refused_count = sum(1 for q in query_events if q.get("refused"))
    latencies = [int(q.get("latency_ms", 0)) for q in query_events if isinstance(q.get("latency_ms"), int)]
    retrieved_ks = [int(q.get("retrieved_k", 0)) for q in query_events if isinstance(q.get("retrieved_k"), int)]

    helpful_count = sum(1 for f in feedback_events if f.get("helpful") is True)
    escalation_count = sum(1 for f in feedback_events if f.get("escalation_requested") is True)
    unhelpful_count = sum(1 for f in feedback_events if f.get("helpful") is False)

    reason_counter = Counter(
        str(f.get("reason"))
        for f in feedback_events
        if isinstance(f.get("reason"), str) and str(f.get("reason")).strip()
    )

    return {
        "window_days": days,
        "city_id": city_id,
        "queries": {
            "total": total_queries,
            "refusal_rate": round(refused_count / total_queries, 4) if total_queries else 0.0,
            "median_latency_ms": median(latencies) if latencies else 0,
            "avg_retrieved_k": round(sum(retrieved_ks) / len(retrieved_ks), 2) if retrieved_ks else 0.0,
        },
        "feedback": {
            "total": total_feedback,
            "coverage_rate": round(len(feedback_by_query) / total_queries, 4) if total_queries else 0.0,
            "helpful_rate": round(helpful_count / total_feedback, 4) if total_feedback else 0.0,
            "unhelpful_rate": round(unhelpful_count / total_feedback, 4) if total_feedback else 0.0,
            "escalation_rate": round(escalation_count / total_feedback, 4) if total_feedback else 0.0,
            "top_reasons": reason_counter.most_common(5),
        },
        "events_total": len(scoped),
    }
