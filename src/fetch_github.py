"""Fetch trending AI projects from GitHub Search API."""

import logging
import os
from datetime import datetime, timedelta, timezone

import requests

from src.dedupe import dedupe_by_url

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
# Optional: use GITHUB_TOKEN for higher rate limit
TOKEN = os.getenv("GITHUB_TOKEN", "").strip()

SEARCH_KEYWORDS = [
    "ai-agent",
    "mcp",
    "claude-code",
    "codex",
    "llm-tools",
    "prompt-engineering",
]

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Panda-Intelligence-Center/1.0",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

REQUEST_TIMEOUT = 30


def search_repos(keyword: str) -> list[dict]:
    """Search GitHub repositories for a keyword, sorted by stars."""
    # Search repos updated in last 30 days, sorted by stars
    since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    url = (
        f"{GITHUB_API}/search/repositories"
        f"?q={keyword}+pushed:>={since}"
        f"&sort=stars&order=desc&per_page=10"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        logger.info("GitHub search '%s': %d results", keyword, len(items))
        return items
    except requests.RequestException as e:
        logger.warning("GitHub search '%s' failed: %s", keyword, e)
        return []


def fetch_github_projects() -> list[dict]:
    """Fetch top AI projects from GitHub, deduplicated across all keywords."""
    all_items: list[dict] = []

    for kw in SEARCH_KEYWORDS:
        repos = search_repos(kw)
        for repo in repos:
            all_items.append({
                "url": repo.get("html_url", ""),
                "name": repo.get("full_name", ""),
                "stars": repo.get("stargazers_count", 0),
                "language": repo.get("language") or "N/A",
                "description": (repo.get("description") or "").strip(),
                "keyword": kw,
                "updated_at": repo.get("updated_at", ""),
            })

    # Deduplicate by URL
    unique = dedupe_by_url(all_items)

    # Sort by stars desc, take top 5
    unique.sort(key=lambda x: x["stars"], reverse=True)
    top5 = unique[:5]

    logger.info("GitHub: %d total, %d unique, %d selected", len(all_items), len(unique), len(top5))
    return top5


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for p in fetch_github_projects():
        print(f"⭐ {p['stars']:>6} | {p['name']:<30} | {p['language']}")
