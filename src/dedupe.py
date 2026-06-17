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


def dedupe_by_title(items: list[dict], threshold: float = 0.6) -> list[dict]:
    """
    Remove near-duplicate items based on title word overlap.
    Uses Jaccard similarity on words — much better than character-level for news titles.
    """
    import re

    def _tokenize(s: str) -> set[str]:
        """Tokenize a title into lowercase word tokens."""
        return set(re.findall(r"[a-zA-Z0-9一-鿿]+", s.lower()))

    seen: list[set[str]] = []
    result: list[dict] = []
    for item in items:
        title = item.get("title", "")
        if not title.strip():
            continue
        tokens = _tokenize(title)
        if not tokens:
            result.append(item)
            continue
        is_dup = False
        for s in seen:
            if not s:
                continue
            # Jaccard similarity: intersection / union
            overlap = len(tokens & s) / len(tokens | s)
            if overlap > threshold:
                is_dup = True
                break
        if not is_dup:
            seen.append(tokens)
            result.append(item)
    return result
