"""Panda News Daily — Global & AI news digest with Chinese summarization.

Orchestrates: RSS news → DeepSeek AI summarization → HTML Email delivery.
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
from src.summarize import is_available as ai_available, summarize_news
from src.mailer import send_news_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("panda-news")


def main():
    date_str = date.today().isoformat()
    errors: list[str] = []

    # ── 1. RSS News ──────────────────────────────────────────────────
    logger.info("══ Step 1/3: Fetching RSS news…")
    ai_news: list[dict] = []
    world_news: list[dict] = []
    try:
        ai_news = fetch_category("ai_news")
    except Exception as e:
        logger.exception("AI news fetch crashed")
        errors.append(f"AI 新闻获取失败: {e}")
    try:
        world_news = fetch_category("world_news")
    except Exception as e:
        logger.exception("World news fetch crashed")
        errors.append(f"全球新闻获取失败: {e}")

    logger.info("  AI news: %d items, World news: %d items", len(ai_news), len(world_news))

    # ── 2. DeepSeek Summarization ────────────────────────────────────
    if ai_available():
        logger.info("══ Step 2/3: AI summarization (DeepSeek)…")
        try:
            ai_news = summarize_news(ai_news, "ai_news")
        except Exception as e:
            logger.exception("AI news summarization crashed")
            errors.append(f"AI 新闻摘要失败: {e}")
        try:
            world_news = summarize_news(world_news, "world_news")
        except Exception as e:
            logger.exception("World news summarization crashed")
            errors.append(f"全球新闻摘要失败: {e}")
    else:
        logger.info("══ Step 2/3: AI summarization SKIPPED (DEEPSEEK_API_KEY not set)")
        errors.append("⚠️ DEEPSEEK_API_KEY 未配置，摘要未经 AI 改写")

    # ── 3. Send Email ────────────────────────────────────────────────
    logger.info("══ Step 3/3: Sending email…")
    try:
        ok = send_news_email(
            date_str=date_str,
            ai_news=ai_news,
            world_news=world_news,
            errors=errors if errors else None,
        )
        if ok:
            logger.info("✅ Email sent successfully!")
        else:
            logger.error("❌ Email sending failed — check SMTP config.")
            sys.exit(1)
    except Exception as e:
        logger.exception("Mailer crashed")
        sys.exit(1)

    logger.info(
        "══ Done: AI_News=%d, World_News=%d, Errors=%d ══",
        len(ai_news), len(world_news), len(errors),
    )


if __name__ == "__main__":
    main()
