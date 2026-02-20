import requests

from backend.app.config import get_settings
from backend.app.rag.guardrails import answer_coverage, groundedness_score

settings = get_settings()


def build_prompt(query: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        [
            f"[Source {i + 1}] title={c.get('title', 'Untitled')} uri={c.get('uri', '')}\n{c.get('text', '')}"
            for i, c in enumerate(chunks)
        ]
    )

    return (
        "Question:\n"
        f"{query}\n\n"
        "Sources:\n"
        f"{context}\n\n"
        "Answer in 2-4 short sentences. Use citations like [1]. "
        "If sources do not support the answer, say: I don't know based on current city documents."
    )


def fallback_extractive(chunks: list[dict]) -> str:
    if not chunks:
        return "I don't know based on current city documents."
    text = chunks[0].get("text", "").strip()
    if not text:
        return "I don't know based on current city documents."
    parts = [p.strip() for p in text.split(". ") if p.strip()]
    if not parts:
        return text[:600]
    return ". ".join(parts[:2])[:600]


def _needs_fallback(answer: str) -> bool:
    lower = answer.lower()
    bad = [
        "return a concise answer",
        "sources:",
        "statement",
        "question:",
        "questions:",
        "you are a municipal information assistant",
        "skips to main content",
    ]
    return any(b in lower for b in bad)


def generate_answer(query: str, chunks: list[dict]) -> str:
    if not chunks:
        return "I don't know based on current city documents."

    prompt = build_prompt(query, chunks)

    try:
        r = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "system": "You are a municipal information assistant. Use only the provided sources. "
                "If the answer is not supported by sources, reply exactly: I don't know based on current city documents.",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 120,
                    "stop": ["Sources:", "Statement", "Question:"],
                },
            },
            timeout=settings.ollama_timeout_sec,
        )
        r.raise_for_status()
        data = r.json()
        text = (data.get("response") or "").strip()
        if not text or _needs_fallback(text):
            return fallback_extractive(chunks)
        if answer_coverage(query, text) < 0.2:
            return fallback_extractive(chunks)
        if groundedness_score(text, chunks) < 0.3:
            return fallback_extractive(chunks)
        return text
    except Exception:
        return fallback_extractive(chunks)
