"""Send HTML email via SMTP."""

from __future__ import annotations

import logging
import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_TO = os.getenv("MAIL_TO", "")
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER)

AUDIENCE_COLORS = {
    "普通用户": "#0969da",   # blue
    "AI爱好者": "#8250df",   # purple
    "开发者":     "#1a7f37",   # green
    "办公自动化": "#cf222e",   # red
}


def send_daily_email(
    *,
    date_str: str,
    github_projects: list[dict],
    ai_news: list[dict],
    world_news: list[dict],
    best_topic: dict,
    errors: list[str] | None = None,
) -> bool:
    """Compose and send the daily digest email."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        logger.error("SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS.")
        return False
    if not MAIL_TO:
        logger.error("MAIL_TO not configured.")
        return False

    html = _build_html(
        date_str=date_str,
        github_projects=github_projects,
        ai_news=ai_news,
        world_news=world_news,
        best_topic=best_topic,
        errors=errors,
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🐼 Panda Intelligence Daily - {date_str}"
    msg["From"] = MAIL_FROM
    msg["To"] = MAIL_TO
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
            server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(MAIL_FROM, [MAIL_TO], msg.as_string())
        server.quit()
        logger.info("Email sent to %s", MAIL_TO)
        return True
    except Exception as e:
        logger.error("SMTP send failed: %s", e)
        return False


def _build_html(
    *,
    date_str: str,
    github_projects: list[dict],
    ai_news: list[dict],
    world_news: list[dict],
    best_topic: dict,
    errors: list[str] | None = None,
) -> str:
    """Build the HTML email body."""

    def _stars(score: int) -> str:
        """Render star rating: ⭐⭐⭐⭐☆"""
        if score <= 0:
            return '<span style="color:#ccc">☆☆☆☆☆</span>'
        filled = "★" * score
        empty = "☆" * (5 - score)
        return f'<span style="color:#f0a500">{filled}</span><span style="color:#ccc">{empty}</span>'

    def _audience_tags(audience: list[str]) -> str:
        """Render colored audience pills."""
        if not audience:
            return ""
        pills = ""
        for tag in audience:
            color = AUDIENCE_COLORS.get(tag, "#666")
            pills += (
                f'<span style="display:inline-block; background:{color}; color:#fff; '
                f'font-size:11px; padding:2px 8px; border-radius:10px; margin-right:4px">{_esc(tag)}</span>'
            )
        return pills

    def _gh_card(p: dict) -> str:
        name = p.get("name", "")
        url = p.get("url", "")
        stars_count = p.get("stars", 0)
        lang = p.get("language", "N/A")
        desc = (p.get("description") or "")[:200]
        why = p.get("why_notable", desc[:60])
        scores = p.get("content_scores", {"xhs": 0, "douyin": 0, "gzh": 0})
        audience = p.get("audience", [])

        # Build scores row
        scores_html = (
            f'<span style="margin-right:14px">📕 小红书 {_stars(scores.get("xhs", 0))}</span>'
            f'<span style="margin-right:14px">🎵 抖音 {_stars(scores.get("douyin", 0))}</span>'
            f'<span>📰 公众号 {_stars(scores.get("gzh", 0))}</span>'
        )
        audience_html = _audience_tags(audience)

        return f"""
        <tr>
          <td style="padding:16px; border-bottom:1px solid #eee">
            <div style="font-size:16px; font-weight:bold; margin-bottom:4px">
              <a href="{url}" style="color:#0969da; text-decoration:none">{_esc(name)}</a>
              <span style="font-size:13px; color:#666; margin-left:8px">⭐ {stars_count}</span>
              <span style="font-size:12px; color:#888; margin-left:8px">{_esc(lang)}</span>
            </div>
            <div style="font-size:14px; color:#444; margin-bottom:4px">{_esc(desc)}</div>
            <div style="font-size:13px; color:#d73a49; margin-bottom:6px">💡 {_esc(why)}</div>
            <div style="font-size:13px; margin-bottom:4px">{scores_html}</div>
            <div style="margin-top:4px">{audience_html}</div>
          </td>
        </tr>"""

    def _news_row(e: dict) -> str:
        title = e.get("title", "")
        url = e.get("url", "")
        source = e.get("source", "")
        cn_summary = e.get("cn_summary", e.get("summary", ""))[:150]
        why = e.get("why_read", "")
        return f"""
        <tr>
          <td style="padding:14px; border-bottom:1px solid #eee">
            <div style="font-size:15px; font-weight:bold; margin-bottom:4px">
              <a href="{url}" style="color:#0969da; text-decoration:none">{_esc(title)}</a>
              <span style="font-size:12px; color:#888; margin-left:8px">{_esc(source)}</span>
            </div>
            <div style="font-size:14px; color:#444; margin-bottom:4px">{_esc(cn_summary)}</div>
            <div style="font-size:13px; color:#1a7f37">📌 {_esc(why)}</div>
          </td>
        </tr>"""

    # ── Errors banner ──────────────────────────────────────────────────
    errors_html = ""
    if errors:
        errors_html = (
            '<div style="background:#fff3cd; padding:12px; border-radius:6px; margin-bottom:20px">'
            + "".join(f"<div style='color:#856404'>⚠️ {_esc(e)}</div>" for e in errors)
            + "</div>"
        )

    # ── Best Topic Section (prominent, top of email) ────────────────────
    score = best_topic.get("recommendation_score", 0)
    reason = best_topic.get("recommendation_reason", "")
    platform = best_topic.get("recommended_platform", "")
    titles = best_topic.get("suggested_titles", [])
    repo_name = best_topic.get("repo", "")
    repo_url = best_topic.get("repo_url", "")

    # Build recommendation stars
    if score > 0:
        rec_stars = "★" * min(score, 5) + "☆" * max(0, 5 - score)
    else:
        rec_stars = ""

    # Build title list
    titles_html = ""
    if titles:
        titles_html = '<ol style="margin:8px 0 0 0; padding-left:20px">' + "".join(
            f'<li style="font-size:14px; color:#24292f; margin-bottom:4px">{_esc(t)}</li>'
            for t in titles
        ) + "</ol>"

    platform_badge = ""
    if platform:
        platform_bg = "#e6005c" if "小红书" in platform else "#010101" if "抖音" in platform else "#8250df"
        platform_badge = (
            f'<span style="display:inline-block; background:{platform_bg}; color:#fff; '
            f'font-size:12px; padding:3px 10px; border-radius:10px; margin-left:8px">{_esc(platform)}</span>'
        )

    best_topic_html = f"""
    <div style="padding:20px; background:linear-gradient(135deg, #fffde7 0%, #fff8e1 100%);
                border:2px solid #f9a825; border-radius:12px; margin-bottom:24px">
      <div style="font-size:18px; font-weight:bold; color:#e65100; margin-bottom:12px">
        🏆 今日最佳选题 {platform_badge}
      </div>
      <div style="font-size:15px; color:#333; margin-bottom:8px">
        推荐指数: <span style="color:#f0a500; font-size:16px">{rec_stars if rec_stars else "—"}</span>
      </div>
      <div style="font-size:14px; color:#555; margin-bottom:12px">{_esc(reason)}</div>
      {f'<div style="font-size:13px; color:#666; margin-bottom:4px">参考项目: <a href="{repo_url}" style="color:#0969da">{_esc(repo_name)}</a></div>' if repo_name else ""}
      <div style="font-size:14px; font-weight:bold; color:#24292f; margin-top:12px; margin-bottom:4px">
        💬 建议标题
      </div>
      {titles_html}
    </div>"""

    # ── GitHub rows ────────────────────────────────────────────────────
    gh_rows = "".join(_gh_card(p) for p in github_projects) if github_projects else (
        "<tr><td style='padding:16px; color:#999'>暂无 GitHub 数据</td></tr>"
    )

    # ── News rows ──────────────────────────────────────────────────────
    ai_rows = "".join(_news_row(e) for e in ai_news) if ai_news else (
        "<tr><td style='padding:14px; color:#999'>暂无 AI 新闻数据</td></tr>"
    )
    world_rows = "".join(_news_row(e) for e in world_news) if world_news else (
        "<tr><td style='padding:14px; color:#999'>暂无全球新闻数据</td></tr>"
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             max-width:640px; margin:0 auto; padding:20px; background:#f6f8fa">
  <div style="background:#fff; border-radius:12px; padding:24px; box-shadow:0 2px 8px rgba(0,0,0,0.08)">
    <h1 style="font-size:24px; color:#24292f; margin:0 0 4px 0">
      🐼 Panda Intelligence Center
    </h1>
    <p style="font-size:14px; color:#656d76; margin:0 0 24px 0">{date_str}</p>

    {errors_html}

    <!-- Today's Best Topic — most prominent section -->
    {best_topic_html}

    <!-- GitHub AI 热门项目 -->
    <h2 style="font-size:20px; color:#24292f; border-bottom:2px solid #0969da; padding-bottom:8px">
      🤖 GitHub AI 热门项目
    </h2>
    <table style="width:100%; border-collapse:collapse">{gh_rows}</table>

    <!-- AI 行业新闻 -->
    <h2 style="font-size:20px; color:#24292f; border-bottom:2px solid #1a7f37; padding-bottom:8px; margin-top:32px">
      🧠 AI 行业新闻
    </h2>
    <table style="width:100%; border-collapse:collapse">{ai_rows}</table>

    <!-- 全球重要新闻 -->
    <h2 style="font-size:20px; color:#24292f; border-bottom:2px solid #8250df; padding-bottom:8px; margin-top:32px">
      🌍 全球重要新闻
    </h2>
    <table style="width:100%; border-collapse:collapse">{world_rows}</table>

    <div style="margin-top:32px; padding-top:16px; border-top:1px solid #ddd;
                font-size:12px; color:#999; text-align:center">
      Panda Intelligence Center · Automated Daily Digest
    </div>
  </div>
</body>
</html>"""


def _esc(s: str) -> str:
    """Escape HTML entities."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ok = send_daily_email(
        date_str=str(date.today()),
        github_projects=[],
        ai_news=[],
        world_news=[],
        best_topic={
            "recommendation_score": 4,
            "recommendation_reason": "这个项目有完整的Web UI，3天涨了2000 star，适合做成图文教程",
            "recommended_platform": "小红书+抖音",
            "suggested_titles": [
                "🤯 GitHub爆火项目，3天涨3000 Star",
                "💼 这个AI工具让我少干2小时活",
                "🆓 又发现一个免费AI神器，打工人必备",
            ],
            "repo": "test/awesome-ai-tool",
            "repo_url": "https://github.com/test/awesome-ai-tool",
        },
        errors=["测试错误：GitHub API 返回 403"],
    )
    print("Send result:", ok)
