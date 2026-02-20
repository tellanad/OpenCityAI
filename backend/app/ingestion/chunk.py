def chunk_text(text: str, max_words: int = 220, overlap: int = 40) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    i = 0
    step = max(1, max_words - overlap)

    while i < len(words):
        chunk = " ".join(words[i : i + max_words]).strip()
        if chunk:
            chunks.append(chunk)
        i += step

    return chunks
