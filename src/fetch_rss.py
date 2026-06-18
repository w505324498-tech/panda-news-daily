"""Fetch and parse RSS/Atom feeds from configured sources."""

import logging
import os
import time

import feedparser
import yaml

from src.dedupe import dedupe_by_title

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "sources.yaml")
MAX_RETRIES = 2
RETRY_DELAY = 3  # seconds between retries
# Note: feedparser controls its own HTTP timeout; we wrap with retry for
# transient network blips that would otherwise silently produce zero entries.


def load_sources() -> dict:
    """Load RSS source configuration from YAML file."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_feed(name: str, url: str) -> list[dict]:
    """Fetch a single RSS/Atom feed with retries, returning parsed entries."""
    last_error = None
    for attempt in range(1 + MAX_RETRIES):
        try:
            feed = feedparser.parse(url, agent="Panda-Intelligence-Center/1.0")
            if not feed.entries:
                if feed.bozo:
                    last_error = str(feed.bozo_exception)
                    logger.warning("RSS '%s' parse error (attempt %d): %s", name, attempt + 1, last_error)
                else:
                    last_error = "empty feed"
                    logger.warning("RSS '%s' returned 0 entries (attempt %d)", name, attempt + 1)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                return []

            entries = []
            for entry in feed.entries[:10]:  # Take up to 10 per feed
                entries.append({
                    "title": entry.get("title", "").strip(),
                    "url": entry.get("link", ""),
                    "source": name,
                    "summary": _clean_summary(entry),
                    "published": entry.get("published", "") or entry.get("updated", ""),
                })
            logger.info("RSS '%s': %d entries", name, len(entries))
            return entries
        except Exception as e:
            last_error = str(e)
            logger.warning("RSS '%s' failed (attempt %d): %s", name, attempt + 1, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    return []


def _clean_summary(entry) -> str:
    """Extract and clean a short summary from a feed entry."""
    # Try summary first, then description, then content
    raw = entry.get("summary", "") or entry.get("description", "") or ""
    if not raw and hasattr(entry, "content"):
        for c in entry.content:
            if c.get("value"):
                raw = c.value
                break
    # Strip HTML tags simply
    import re
    clean = re.sub(r"<[^>]+>", "", raw)
    clean = re.sub(r"\s+", " ", clean).strip()
    # Truncate to ~300 chars
    if len(clean) > 300:
        clean = clean[:297] + "..."
    return clean


def fetch_category(category: str) -> list[dict]:
    """Fetch all feeds for a category, deduplicate, return top N."""
    sources = load_sources()
    feeds = sources.get(category, [])
    logger.info("Fetching category '%s': %d feeds", category, len(feeds))

    all_entries: list[dict] = []
    for feed_cfg in feeds:
        entries = fetch_feed(feed_cfg["name"], feed_cfg["url"])
        all_entries.extend(entries)

    # Deduplicate by title similarity, then by exact URL
    unique = dedupe_by_title(all_entries, threshold=0.7)

    # Take top 8 per category
    return unique[:8]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== AI News ===")
    for e in fetch_category("ai_news"):
        print(f"  {e['title']} | {e['source']}")
    print("=== World News ===")
    for e in fetch_category("world_news"):
        print(f"  {e['title']} | {e['source']}")
