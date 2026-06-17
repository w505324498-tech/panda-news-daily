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


def send_daily_email(
    *,
    date_str: str,
    github_projects: list[dict],
    ai_news: list[dict],
    world_news: list[dict],
    xhs_suggestion: dict,
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
        xhs_suggestion=xhs_suggestion,
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
    xhs_suggestion: dict,
    errors: list[str] | None = None,
) -> str:
    """Build the HTML email body."""

    def _gh_card(p: dict) -> str:
        name = p.get("name", "")
        url = p.get("url", "")
        stars = p.get("stars", 0)
        lang = p.get("language", "N/A")
        desc = p.get("description", "")[:200]
        why = p.get("why_notable", desc[:60])
        return f"""
        <tr>
          <td style="padding:16px; border-bottom:1px solid #eee">
            <div style="font-size:16px; font-weight:bold; margin-bottom:4px">
              <a href="{url}" style="color:#0969da; text-decoration:none">{_esc(name)}</a>
              <span style="font-size:13px; color:#666; margin-left:8px">⭐ {stars}</span>
              <span style="font-size:12px; color:#888; margin-left:8px">{_esc(lang)}</span>
            </div>
            <div style="font-size:14px; color:#444; margin-bottom:4px">{_esc(desc)}</div>
            <div style="font-size:13px; color:#d73a49">💡 {_esc(why)}</div>
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

    errors_html = ""
    if errors:
        errors_html = (
            '<div style="background:#fff3cd; padding:12px; border-radius:6px; margin-bottom:20px">'
            + "".join(f"<div style='color:#856404'>⚠️ {_esc(e)}</div>" for e in errors)
            + "</div>"
        )

    gh_rows = "".join(_gh_card(p) for p in github_projects) if github_projects else (
        "<tr><td style='padding:16px; color:#999'>暂无 GitHub 数据</td></tr>"
    )
    ai_rows = "".join(_news_row(e) for e in ai_news) if ai_news else (
        "<tr><td style='padding:14px; color:#999'>暂无 AI 新闻数据</td></tr>"
    )
    world_rows = "".join(_news_row(e) for e in world_news) if world_news else (
        "<tr><td style='padding:14px; color:#999'>暂无全球新闻数据</td></tr>"
    )

    xhs_html = f"""
    <div style="padding:16px; background:#fff0f5; border-radius:8px; margin:16px 0">
      <div style="font-size:16px; font-weight:bold; color:#e6005c; margin-bottom:8px">
        📕 {_esc(xhs_suggestion.get('title', '今日推荐'))}
      </div>
      <div style="font-size:14px; color:#333; margin-bottom:6px">
        项目: <a href="https://github.com/{_esc(xhs_suggestion.get('repo', ''))}" style="color:#0969da">
          {_esc(xhs_suggestion.get('repo', ''))}</a>
      </div>
      <div style="font-size:13px; color:#555; margin-bottom:6px">
        {_esc(xhs_suggestion.get('angle', ''))}
      </div>
      <div style="font-size:13px; color:#777">{_esc(xhs_suggestion.get('why', ''))}</div>
    </div>"""

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

    <!-- 小红书选题 -->
    <h2 style="font-size:20px; color:#24292f; border-bottom:2px solid #e6005c; padding-bottom:8px; margin-top:32px">
      📕 今日最适合做小红书的 GitHub 选题
    </h2>
    {xhs_html}

    <div style="margin-top:32px; padding-top:16px; border-top:1px solid #ddd;
                font-size:12px; color:#999; text-align:center">
      Panda Intelligence Center · Automated Daily Digest · <a href="https://github.com" style="color:#999">GitHub</a>
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
        xhs_suggestion={"title": "Test", "repo": "test/test", "angle": "test|test|test", "why": "test"},
        errors=["测试错误：GitHub API 返回 403"],
    )
    print("Send result:", ok)
