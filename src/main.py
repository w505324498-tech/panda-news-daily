"""Panda News Daily — Global & AI news digest with Chinese summarization.

Orchestrates: RSS news → DeepSeek AI summarization → HTML Email delivery.
v3: 4 categories (AI / China-Watch / World / Global-Markets) + real-time index data.
China news sourced from international media (SCMP, BBC, The Diplomat, etc.) to avoid state-media repetition.
"""

import logging
import os
import sys
from datetime import date
from pathlib import Path

# Load .env file
_dotenv_path = Path(__file__).resolve().parent.parent / ".env"
if _dotenv_path.exists():
    with open(_dotenv_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

from src.fetch_rss import fetch_category
from src.fetch_stock import fetch_indices
from src.summarize import is_available as ai_available, summarize_news
from src.mailer import send_news_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("panda-news")

CATEGORIES = ["ai_news", "china_news", "world_news", "stock_news"]


def _fetch_all() -> tuple[dict[str, list[dict]], list[str]]:
    """Fetch all 4 RSS categories. Each failure is non-fatal."""
    results: dict[str, list[dict]] = {}
    errors: list[str] = []
    for cat in CATEGORIES:
        try:
            results[cat] = fetch_category(cat)
        except Exception as e:
            logger.exception("%s fetch crashed", cat)
            errors.append(f"{cat} 获取失败: {e}")
            results[cat] = []
    counts = ", ".join(f"{cat}={len(results[cat])}" for cat in CATEGORIES)
    logger.info("RSS fetch done: %s", counts)
    return results, errors


def _summarize_all(news: dict[str, list[dict]]) -> tuple[dict[str, list[dict]], list[str]]:
    """Summarize each category via DeepSeek. Each failure is non-fatal."""
    errors: list[str] = []
    for cat in CATEGORIES:
        try:
            news[cat] = summarize_news(news[cat], cat)
        except Exception as e:
            logger.exception("%s summarization crashed", cat)
            errors.append(f"{cat} 摘要失败: {e}")
    return news, errors


def main():
    date_str = date.today().isoformat()
    all_errors: list[str] = []

    # ── 1. Fetch ─────────────────────────────────────────────────────
    logger.info("══ Step 1/4: Fetching RSS news (4 categories)…")
    news, fetch_errs = _fetch_all()
    all_errors.extend(fetch_errs)

    # ── 2. Stock indices ─────────────────────────────────────────────
    logger.info("══ Step 2/4: Fetching stock indices…")
    indices: list[dict] = []
    try:
        indices = fetch_indices()
    except Exception as e:
        logger.exception("Stock index fetch crashed")
        all_errors.append(f"股市指数获取失败: {e}")

    # ── 3. Summarize ─────────────────────────────────────────────────
    if ai_available():
        logger.info("══ Step 3/4: AI summarization (Gemini)…")
        news, sum_errs = _summarize_all(news)
        all_errors.extend(sum_errs)
    else:
        logger.info("══ Step 3/4: AI summarization SKIPPED (GEMINI_API_KEY not set)")
        all_errors.append("⚠️ GEMINI_API_KEY 未配置，摘要未经 AI 改写")

    # ── 4. Send Email ────────────────────────────────────────────────
    logger.info("══ Step 4/4: Sending email…")
    try:
        ok = send_news_email(
            date_str=date_str,
            ai_news=news.get("ai_news", []),
            world_news=news.get("world_news", []),
            china_news=news.get("china_news", []),
            stock_news=news.get("stock_news", []),
            indices=indices,
            errors=all_errors if all_errors else None,
        )
        if ok:
            logger.info("✅ Email sent successfully!")
        else:
            logger.error("❌ Email sending failed — check SMTP config.")
            sys.exit(1)
    except Exception as e:
        logger.exception("Mailer crashed")
        sys.exit(1)

    sums = ", ".join(f"{cat}={len(news.get(cat, []))}" for cat in CATEGORIES)
    logger.info("══ Done: %s, Indices=%d, Errors=%d ══", sums, len(indices), len(all_errors))


if __name__ == "__main__":
    main()
