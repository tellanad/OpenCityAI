import json
import time
import uuid
from typing import AsyncGenerator

import httpx

from backend.app.analytics.store import record_query_event
from backend.app.config import get_settings
from backend.app.rag.generate import build_prompt, fallback_extractive
from backend.app.rag.retrieve import retrieve_chunks

settings = get_settings()


def _format_sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=True)
    return f"event: {event}\ndata: {payload}\n\n"


def _safe_record(**kwargs) -> None:
    try:
        record_query_event(**kwargs)
    except Exception:
        # Streaming should not fail due to analytics write errors.
        return


def _build_citations(chunks: list[dict]) -> list[dict]:
    out = []
    for c in chunks[:3]:
        out.append(
            {
                "title": c.get("title", "Untitled"),
                "uri": c.get("uri", ""),
                "snippet": c.get("text", "")[:220],
                "score": c.get("score", 0.0),
            }
        )
    return out


async def stream_answer(
    *,
    city_id: str,
    query: str,
    session_id: str | None,
) -> AsyncGenerator[str, None]:
    query_id = uuid.uuid4().hex
    started = time.perf_counter()

    chunks = retrieve_chunks(city_id=city_id, query=query)
    citations = _build_citations(chunks)

    if not chunks:
        meta = {
            "city_id": city_id,
            "retrieved_k": 0,
            "refused": True,
            "reason": "no_retrieval_hits",
            "model": settings.ollama_model,
            "session_id": session_id,
            "query_id": query_id,
            "citations": citations,
        }
        yield _format_sse("meta", meta)
        yield _format_sse(
            "token", {"token": "I don't know based on current city documents."}
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        _safe_record(
            city_id=city_id,
            query_id=query_id,
            query_text=query,
            session_id=session_id,
            latency_ms=latency_ms,
            refused=True,
            refusal_reason="no_retrieval_hits",
            retrieved_k=0,
            citations_count=len(citations),
            model=settings.ollama_model,
        )
        yield _format_sse("done", {"latency_ms": latency_ms, "refused": True})
        return

    top_score = chunks[0]["score"]
    if top_score < settings.similarity_threshold:
        meta = {
            "city_id": city_id,
            "retrieved_k": len(chunks),
            "refused": True,
            "reason": "low_confidence",
            "top_score": top_score,
            "model": settings.ollama_model,
            "session_id": session_id,
            "query_id": query_id,
            "citations": citations,
        }
        yield _format_sse("meta", meta)
        yield _format_sse(
            "token", {"token": "I don't know based on current city documents."}
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        _safe_record(
            city_id=city_id,
            query_id=query_id,
            query_text=query,
            session_id=session_id,
            latency_ms=latency_ms,
            refused=True,
            refusal_reason="low_confidence",
            retrieved_k=len(chunks),
            citations_count=len(citations),
            model=settings.ollama_model,
        )
        yield _format_sse("done", {"latency_ms": latency_ms, "refused": True})
        return

    meta = {
        "city_id": city_id,
        "retrieved_k": len(chunks),
        "refused": False,
        "model": settings.ollama_model,
        "session_id": session_id,
        "query_id": query_id,
        "citations": citations,
    }
    yield _format_sse("meta", meta)

    prompt = build_prompt(query, chunks)
    token_count = 0
    stream_failed = False

    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_sec) as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"temperature": 0.1, "num_predict": 120},
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = payload.get("response")
                    if token:
                        token_count += 1
                        yield _format_sse("token", {"token": token})
                    if payload.get("done") is True:
                        break
    except Exception:
        stream_failed = True

    if stream_failed or token_count == 0:
        fallback = fallback_extractive(chunks)
        yield _format_sse("token", {"token": fallback})

    latency_ms = int((time.perf_counter() - started) * 1000)
    _safe_record(
        city_id=city_id,
        query_id=query_id,
        query_text=query,
        session_id=session_id,
        latency_ms=latency_ms,
        refused=False,
        refusal_reason=None,
        retrieved_k=len(chunks),
        citations_count=len(citations),
        model=settings.ollama_model,
    )
    yield _format_sse("done", {"latency_ms": latency_ms, "refused": False})
