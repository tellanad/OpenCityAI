import re

from bs4 import BeautifulSoup


def extract_text(uri: str, raw: bytes, content_type: str) -> tuple[str, str]:
    if "html" in content_type.lower() or uri.lower().endswith((".html", ".htm")):
        soup = BeautifulSoup(raw, "lxml")
        title = (soup.title.string or "Untitled").strip() if soup.title else "Untitled"
        text = soup.get_text(" ", strip=True)
    else:
        title = uri.rsplit("/", 1)[-1] or "Untitled"
        text = raw.decode("utf-8", errors="ignore")

    text = re.sub(r"\s+", " ", text).strip()
    return title, text
