import re

from backend.app.config import get_settings

settings = get_settings()

_STOPWORDS = {
    "this",
    "that",
    "with",
    "from",
    "what",
    "when",
    "where",
    "which",
    "your",
    "about",
    "into",
    "their",
    "there",
    "here",
    "have",
    "will",
    "could",
    "should",
    "would",
    "also",
    "city",
    "report",
    "problem",
}


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def coverage_score(query: str, chunks: list[dict]) -> float:
    terms = _keywords(query)
    if len(terms) < settings.min_keyword_count:
        return 1.0

    combined = " ".join(c.get("text", "") for c in chunks[:3])
    hay = _keywords(combined)
    if not terms:
        return 0.0
    return len(terms & hay) / len(terms)


def answer_coverage(query: str, answer: str) -> float:
    terms = _keywords(query)
    if not terms:
        return 0.0
    ans_terms = _keywords(answer)
    return len(terms & ans_terms) / len(terms)


def groundedness_score(answer: str, chunks: list[dict]) -> float:
    ans_terms = _keywords(answer)
    if not ans_terms:
        return 0.0
    context = " ".join(c.get("text", "") for c in chunks[:3])
    ctx_terms = _keywords(context)
    if not ctx_terms:
        return 0.0
    return len(ans_terms & ctx_terms) / len(ans_terms)


def should_refuse(query: str, chunks: list[dict]) -> tuple[bool, str | None, dict]:
    if not chunks:
        return True, "no_retrieval_hits", {"coverage": 0.0}

    top_score = float(chunks[0].get("score", 0.0))
    if top_score < settings.similarity_threshold:
        return True, "low_confidence", {"coverage": 0.0, "top_score": top_score}

    coverage = coverage_score(query, chunks)
    if coverage < settings.coverage_threshold:
        return True, "low_coverage", {"coverage": coverage, "top_score": top_score}

    return False, None, {"coverage": coverage, "top_score": top_score}
