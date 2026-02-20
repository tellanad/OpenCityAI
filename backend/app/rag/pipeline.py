from backend.app.config import get_settings
from backend.app.rag.generate import generate_answer
from backend.app.rag.guardrails import should_refuse
from backend.app.rag.retrieve import retrieve_chunks

settings = get_settings()


def run_rag(city_id: str, query: str, session_id: str | None = None) -> dict:
    chunks = retrieve_chunks(city_id=city_id, query=query)

    refused, reason, guard_meta = should_refuse(query, chunks)

    if refused:
        return {
            "answer": "I don't know based on current city documents.",
            "citations": [],
            "meta": {
                "city_id": city_id,
                "retrieved_k": len(chunks),
                "refused": True,
                "reason": reason,
                "session_id": session_id,
                **guard_meta,
            },
        }

    answer = generate_answer(query=query, chunks=chunks)

    citations = []
    for c in chunks[:3]:
        citations.append(
            {
                "title": c.get("title", "Untitled"),
                "uri": c.get("uri", ""),
                "snippet": c.get("text", "")[:220],
                "score": c.get("score", 0.0),
            }
        )

    return {
        "answer": answer,
        "citations": citations,
        "meta": {
            "city_id": city_id,
            "retrieved_k": len(chunks),
            "refused": False,
            "model": settings.ollama_model,
            "session_id": session_id,
        },
    }
