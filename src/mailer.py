"""Send HTML news digest email via SMTP."""

from __future__ import annotations

import logging
import os
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_TO = os.getenv("MAIL_TO", "")
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER)
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "🐼 Panda News Daily")


def send_news_email(
    *,
    date_str: str,
    ai_news: list[dict],
    world_news: list[dict],
    china_news: list[dict] | None = None,
    stock_news: list[dict] | None = None,
    indices: list[dict] | None = None,
    errors: list[str] | None = None,
) -> bool:
    """Compose and send the daily news digest email."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        logger.error("SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS.")
        return False
    if not MAIL_TO:
        logger.error("MAIL_TO not configured.")
        return False

    logger.info("Sending via %s", SMTP_HOST)

    html = _build_html(
        date_str=date_str,
        ai_news=ai_news,
        world_news=world_news,
        china_news=china_news or [],
        stock_news=stock_news or [],
        indices=indices or [],
        errors=errors,
    )

    # Unique Message-ID prevents Gmail from treating self-sent mail as a
    # duplicate and archiving it straight to Sent — it forces inbox delivery.
    msg_id = f"<panda-news-{date_str}-{uuid.uuid4().hex[:8]}@{SMTP_HOST.split('.', 1)[-1] or 'local'}>"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📰 Panda News Daily - {date_str}"
    msg["From"] = formataddr((MAIL_FROM_NAME, MAIL_FROM))
    msg["To"] = MAIL_TO
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = msg_id
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
    china_news: list[dict],
    stock_news: list[dict],
    indices: list[dict],
    errors: list[str] | None = None,
) -> str:
    """Build the multi-section news HTML email body."""

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

    def _section(title: str, emoji: str, color: str, news: list[dict]) -> str:
        rows = "".join(_news_card(e, i + 1) for i, e in enumerate(news)) if news else (
            "<tr><td style='padding:16px; color:#999'>暂无数据</td></tr>"
        )
        return f"""
        <h2 style="font-size:19px; color:{color}; border-bottom:2px solid {color}; padding-bottom:8px; margin-top:32px">
          {emoji} {title}
        </h2>
        <table style="width:100%; border-collapse:collapse; margin-bottom:8px">
          {rows}
        </table>"""

    # ── Index ticker bar ─────────────────────────────────────────────────
    index_html = _index_bar(indices)

    # ── Errors banner ────────────────────────────────────────────────────
    errors_html = ""
    if errors:
        errors_html = (
            '<div style="background:#fff3cd; padding:14px; border-radius:8px; margin-bottom:24px; border-left:4px solid #f0a500">'
            + "".join(f"<div style='color:#856404; font-size:13px; margin:4px 0'>⚠️ {_esc(e)}</div>" for e in errors)
            + "</div>"
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
      <p style="font-size:14px; color:#656d76; margin:0">{date_str} · AI Curation by Gemini</p>
    </div>

    {index_html}
    {errors_html}
    {_section("AI 行业新闻", "🧠", "#1a7f37", ai_news)}
    {_section("中国观察", "🔭", "#d32f2f", china_news)}
    {_section("国际新闻", "🌍", "#8250df", world_news)}
    {_section("全球市场", "📈", "#e65100", stock_news)}

    <!-- Footer -->
    <div style="margin-top:32px; padding-top:16px; border-top:1px solid #e8e8e8;
                font-size:12px; color:#999; text-align:center">
      🐼 Panda News Daily · Automated · Powered by Gemini
    </div>
  </div>
</body>
</html>"""


def _index_bar(indices: list[dict]) -> str:
    """Render a compact index ticker bar at the top of the email."""
    if not indices:
        return ""
    badges = []
    for idx in indices:
        name = idx["name"]
        cur = idx["current"]
        direction = idx["direction"]
        change_pct = idx["change_pct"]
        color = "#d32f2f" if direction == "↑" else "#1a7f37"
        badges.append(
            f'<span style="display:inline-block; padding:6px 12px; margin:3px 4px; '
            f'background:#f6f8fa; border-radius:8px; font-size:13px; white-space:nowrap">'
            f'<b>{name}</b> {cur:.0f} '
            f'<span style="color:{color}">{direction}{abs(change_pct):.2f}%</span></span>'
        )
    return (
        '<div style="text-align:center; padding:12px 0; margin-bottom:8px">'
        + "".join(badges)
        + "</div>"
    )


def _esc(s: str) -> str:
    """Escape HTML entities."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
