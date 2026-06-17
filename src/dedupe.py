"""URL-based deduplication for fetched items."""


def dedupe_by_url(items: list[dict]) -> list[dict]:
    """Remove duplicate items based on 'url' key, preserving order."""
    seen: set[str] = set()
    result: list[dict] = []
    for item in items:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            result.append(item)
    return result


def dedupe_by_title(items: list[dict], threshold: float = 0.8) -> list[dict]:
    """
    Remove near-duplicate items based on title similarity.
    Uses simple character overlap ratio — fast and dependency-free.
    """
    seen: list[str] = []
    result: list[dict] = []
    for item in items:
        title = item.get("title", "")
        is_dup = False
        for s in seen:
            if _similarity(title, s) > threshold:
                is_dup = True
                break
        if not is_dup:
            seen.append(title)
            result.append(item)
    return result


def _similarity(a: str, b: str) -> float:
    """Simple character-set overlap ratio."""
    if not a or not b:
        return 0.0
    set_a = set(a.lower())
    set_b = set(b.lower())
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    return len(intersection) / min(len(set_a), len(set_b))
