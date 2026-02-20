import requests

from backend.app.config import get_settings

settings = get_settings()


def build_prompt(query: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        [
            f"[Source {i + 1}] title={c.get('title', 'Untitled')} uri={c.get('uri', '')}\n{c.get('text', '')}"
            for i, c in enumerate(chunks)
        ]
    )

    return (
        "You are a municipal information assistant. Use only the provided sources. "
        "If the answer is not supported by sources, respond with: I don't know based on current city documents.\n\n"
        f"Question:\n{query}\n\n"
        f"Sources:\n{context}\n\n"
        "Return a concise answer and cite source numbers in brackets, e.g. [1]."
    )


def fallback_extractive(chunks: list[dict]) -> str:
    snippets = [c.get("text", "").strip() for c in chunks[:2] if c.get("text")]
    if not snippets:
        return "I don't know based on current city documents."
    return "\n\n".join(snippets)[:1200]


def generate_answer(query: str, chunks: list[dict]) -> str:
    if not chunks:
        return "I don't know based on current city documents."

    prompt = build_prompt(query, chunks)

    try:
        r = requests.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 120},
            },
            timeout=settings.ollama_timeout_sec,
        )
        r.raise_for_status()
        data = r.json()
        text = (data.get("response") or "").strip()
        if not text:
            return fallback_extractive(chunks)
        return text
    except Exception:
        return fallback_extractive(chunks)
