import requests


def fetch_url(uri: str, timeout_sec: int = 20) -> tuple[bytes, str]:
    r = requests.get(uri, timeout=timeout_sec)
    r.raise_for_status()
    content_type = r.headers.get("content-type", "text/plain")
    return r.content, content_type
