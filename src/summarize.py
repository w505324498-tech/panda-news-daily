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


def _parse_json(raw: str) -> any:
    """Parse JSON from LLM response, handling markdown code fences."""
    import re
    text = raw.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    return json.loads(text)


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


_CATEGORY_LABELS = {
    "ai_news": "AI行业",
    "world_news": "国际",
    "china_news": "国内",
    "stock_news": "股市",
}

_CATEGORY_GUIDANCE = {
    "ai_news": "聚焦技术突破、产品发布、行业趋势。用通俗比喻解释技术概念。",
    "world_news": "聚焦地缘政治、重大事件、全球影响。突出对中国读者的关联性。",
    "china_news": "聚焦国内政策、社会民生、经济动态。突出对普通人的生活影响。",
    "stock_news": "聚焦市场波动原因、板块轮动、监管政策。提取关键数字（涨跌幅、点位）和驱动因素。",
}


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

    cat_label = _CATEGORY_LABELS.get(category, "综合")
    guidance = _CATEGORY_GUIDANCE.get(category, "")
    prompt = (
        f"你是一个新闻编辑。以下是从RSS抓取的{cat_label}新闻。\n"
        f"写作原则：{guidance}\n\n"
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
        highlights = _parse_json(raw)
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
