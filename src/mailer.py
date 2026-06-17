"""Send HTML news digest email via SMTP."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_TO = os.getenv("MAIL_TO", "")
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER)


def send_news_email(
    *,
    date_str: str,
    ai_news: list[dict],
    world_news: list[dict],
    errors: list[str] | None = None,
) -> bool:
    """Compose and send the daily news digest email."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        logger.error("SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS.")
        return False
    if not MAIL_TO:
        logger.error("MAIL_TO not configured.")
        return False

    html = _build_html(date_str=date_str, ai_news=ai_news, world_news=world_news, errors=errors)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📰 Panda News Daily - {date_str}"
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
    ai_news: list[dict],
    world_news: list[dict],
    errors: list[str] | None = None,
) -> str:
    """Build the news-only HTML email body."""

    def _news_card(e: dict, index: int) -> str:
        title = e.get("title", "")
        url = e.get("url", "")
        source = e.get("source", "")
        cn_summary = e.get("cn_summary", e.get("summary", ""))[:150]
        why = e.get("why_read", "")
        return f"""
        <tr>
          <td style="padding:16px; border-bottom:1px solid #e8e8e8">
            <div style="font-size:16px; font-weight:bold; margin-bottom:6px">
              <span style="color:#8250df; margin-right:8px">#{index}</span>
              <a href="{url}" style="color:#0969da; text-decoration:none">{_esc(title)}</a>
            </div>
            <div style="font-size:12px; color:#888; margin-bottom:8px">📡 {_esc(source)}</div>
            <div style="font-size:14px; color:#333; line-height:1.7; margin-bottom:6px">
              📝 {_esc(cn_summary)}
            </div>
            {f'<div style="font-size:13px; color:#1a7f37">💡 {_esc(why)}</div>' if why else ''}
          </td>
        </tr>"""

    # ── Errors banner ──────────────────────────────────────────────────
    errors_html = ""
    if errors:
        errors_html = (
            '<div style="background:#fff3cd; padding:14px; border-radius:8px; margin-bottom:24px; border-left:4px solid #f0a500">'
            + "".join(f"<div style='color:#856404; font-size:13px; margin:4px 0'>⚠️ {_esc(e)}</div>" for e in errors)
            + "</div>"
        )

    # ── News sections ──────────────────────────────────────────────────
    ai_rows = "".join(_news_card(e, i + 1) for i, e in enumerate(ai_news)) if ai_news else (
        "<tr><td style='padding:16px; color:#999'>暂无 AI 新闻数据</td></tr>"
    )
    world_rows = "".join(_news_card(e, i + 1) for i, e in enumerate(world_news)) if world_news else (
        "<tr><td style='padding:16px; color:#999'>暂无全球新闻数据</td></tr>"
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             max-width:640px; margin:0 auto; padding:20px; background:#f6f8fa">
  <div style="background:#fff; border-radius:12px; padding:28px; box-shadow:0 2px 8px rgba(0,0,0,0.06)">

    <!-- Header -->
    <div style="text-align:center; padding-bottom:20px; border-bottom:3px solid #8250df; margin-bottom:24px">
      <h1 style="font-size:24px; color:#24292f; margin:0 0 6px 0">📰 Panda News Daily</h1>
      <p style="font-size:14px; color:#656d76; margin:0">{date_str} · AI Curation by DeepSeek</p>
    </div>

    {errors_html}

    <!-- AI News -->
    <h2 style="font-size:19px; color:#1a7f37; border-bottom:2px solid #1a7f37; padding-bottom:8px; margin-top:8px">
      🧠 AI 行业新闻
    </h2>
    <table style="width:100%; border-collapse:collapse; margin-bottom:8px">
      {ai_rows}
    </table>

    <!-- World News -->
    <h2 style="font-size:19px; color:#8250df; border-bottom:2px solid #8250df; padding-bottom:8px; margin-top:32px">
      🌍 全球重要新闻
    </h2>
    <table style="width:100%; border-collapse:collapse; margin-bottom:8px">
      {world_rows}
    </table>

    <!-- Footer -->
    <div style="margin-top:32px; padding-top:16px; border-top:1px solid #e8e8e8;
                font-size:12px; color:#999; text-align:center">
      🐼 Panda News Daily · Automated · Powered by DeepSeek
    </div>
  </div>
</body>
</html>"""


def _esc(s: str) -> str:
    """Escape HTML entities."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
