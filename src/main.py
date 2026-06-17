"""Panda Intelligence Center — Daily AI & World News Digest.

Orchestrates: GitHub trending → RSS news → AI summarization → Email delivery.
"""

import logging
import sys
from datetime import date, datetime, timezone

from src.fetch_github import fetch_github_projects
from src.fetch_rss import fetch_category
from src.summarize import is_available as ai_available
from src.summarize import summarize_github, summarize_news, suggest_xhs_topic
from src.mailer import send_daily_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pic")


def main():
    date_str = date.today().isoformat()
    errors: list[str] = []

    # ── 1. GitHub AI Trending ──────────────────────────────────────
    logger.info("══ Step 1/5: Fetching GitHub AI projects…")
    github_projects: list[dict] = []
    try:
        github_projects = fetch_github_projects()
    except Exception as e:
        logger.exception("GitHub fetch crashed")
        errors.append(f"GitHub 数据获取失败: {e}")

    # ── 2. RSS News ────────────────────────────────────────────────
    logger.info("══ Step 2/5: Fetching RSS news…")
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

    # ── 3. AI Summarization ────────────────────────────────────────
    if ai_available():
        logger.info("══ Step 3/5: AI summarization (API available)…")
        try:
            github_projects = summarize_github(github_projects)
        except Exception as e:
            logger.exception("GitHub summarization crashed")
            errors.append(f"GitHub AI 摘要失败: {e}")
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
        logger.info("══ Step 3/5: AI summarization SKIPPED (OPENAI_API_KEY not set)…")
        errors.append("⚠️ OPENAI_API_KEY 未配置，摘要未经 AI 改写")

    # ── 4. XHS Suggestion ─────────────────────────────────────────
    logger.info("══ Step 4/5: Generating XHS topic suggestion…")
    xhs_suggestion: dict = {"title": "今日推荐", "repo": "", "angle": "", "why": ""}
    try:
        if ai_available():
            xhs_suggestion = suggest_xhs_topic(github_projects, ai_news)
        else:
            xhs_suggestion["angle"] = "AI功能暂不可用"
    except Exception as e:
        logger.exception("XHS suggestion crashed")
        errors.append(f"小红书选题生成失败: {e}")

    # ── 5. Send Email ──────────────────────────────────────────────
    logger.info("══ Step 5/5: Sending email…")
    try:
        ok = send_daily_email(
            date_str=date_str,
            github_projects=github_projects,
            ai_news=ai_news,
            world_news=world_news,
            xhs_suggestion=xhs_suggestion,
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

    # Summary
    logger.info(
        "══ Done: GitHub=%d, AI_News=%d, World_News=%d, Errors=%d ══",
        len(github_projects), len(ai_news), len(world_news), len(errors),
    )


if __name__ == "__main__":
    main()
