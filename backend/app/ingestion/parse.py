import re

from bs4 import BeautifulSoup


def extract_text(uri: str, raw: bytes, content_type: str) -> tuple[str, str]:
    if "html" in content_type.lower() or uri.lower().endswith((".html", ".htm")):
        soup = BeautifulSoup(raw, "lxml")
        for tag in soup(["script", "style", "noscript", "svg", "form", "button"]):
            tag.decompose()

        for tag in soup.find_all(["nav", "header", "footer", "aside"]):
            tag.decompose()

        # Remove common navigation/breadcrumb containers by class/id.
        for tag in soup.find_all(True):
            ident = " ".join(
                [
                    str(tag.get("id", "")),
                    " ".join(tag.get("class", [])) if isinstance(tag.get("class"), list) else "",
                ]
            ).lower()
            if any(
                key in ident
                for key in (
                    "nav",
                    "menu",
                    "breadcrumb",
                    "footer",
                    "header",
                    "skip",
                    "language",
                    "search",
                    "toolbar",
                )
            ):
                tag.decompose()

        title = (soup.title.string or "Untitled").strip() if soup.title else "Untitled"
        text = soup.get_text(" ", strip=True)
    else:
        title = uri.rsplit("/", 1)[-1] or "Untitled"
        text = raw.decode("utf-8", errors="ignore")

    # Remove common navigation boilerplate that still leaks into main content.
    noise = [
        r"\bSkip to main content\b",
        r"\bSF\.gov Menu\b",
        r"\bSF\.gov\b",
        r"\bMenu\b",
    ]
    for pattern in noise:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    text = re.sub(r"\s+", " ", text).strip()
    return title, text
