"""Call DeepSeek API to generate Chinese news summaries."""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "").strip() or "https://api.deepseek.com"
MODEL = os.getenv("DEEPSEEK_MODEL", "").strip() or "deepseek-chat"

REQUEST_TIMEOUT = 120


def _client():
    """Lazy-init the OpenAI client (DeepSeek is OpenAI-compatible)."""
    from openai import OpenAI
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=REQUEST_TIMEOUT)


def is_available() -> bool:
    return bool(API_KEY)


def _chat(prompt: str, max_tokens: int = 3000) -> str:
    """Send a chat completion request and return the content."""
    client = _client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


def summarize_news(entries: list[dict], category: str) -> list[dict]:
    """Generate Chinese summary and 'why worth reading' for news entries."""
    if not entries or not is_available():
        for e in entries:
            e.setdefault("cn_summary", e.get("summary", "")[:100])
            e.setdefault("why_read", "")
        return entries

    items_text = "\n\n".join(
        f"[{i+1}] 标题: {e['title']}\n来源: {e['source']}\n原文摘要: {e['summary']}"
        for i, e in enumerate(entries)
    )

    cat_label = "AI行业" if category == "ai_news" else "全球重要"
    prompt = (
        f"你是一个新闻编辑。以下是从RSS抓取的{cat_label}新闻。"
        "请为每条新闻生成：\n"
        "1. 简短中文摘要（50字以内，通俗易懂）\n"
        "2. 为什么值得看（30字以内，说明对读者的价值）\n\n"
        f"{items_text}\n\n"
        "请按以下JSON格式输出（仅输出JSON，不要其他文字）：\n"
        '[{"index": 1, "cn_summary": "中文摘要...", "why": "为什么值得看..."}, ...]'
    )

    try:
        raw = _chat(prompt, max_tokens=1500)
        logger.info("%s summary generated", category)
        highlights = json.loads(raw)
        for h in highlights:
            idx = h["index"] - 1
            if 0 <= idx < len(entries):
                entries[idx]["cn_summary"] = h.get("cn_summary", entries[idx]["summary"][:100])
                entries[idx]["why_read"] = h.get("why", "")
    except Exception as e:
        logger.warning("%s summarization failed: %s", category, e)
        for e_item in entries:
            e_item["cn_summary"] = e_item["summary"][:100]
            e_item["why_read"] = ""

    return entries
