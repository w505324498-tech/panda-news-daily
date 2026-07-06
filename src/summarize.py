"""Call Gemini API to generate Chinese news summaries."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "").strip() or "gemini-2.5-flash"

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
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


def is_available() -> bool:
    ok = bool(API_KEY)
    if ok:
        logger.info("Gemini API key present (%s…%s, model=%s)",
                    API_KEY[:4], API_KEY[-4:], MODEL)
    return ok


def _chat(prompt: str, max_tokens: int = 3000) -> str:
    """Send a generateContent request to Gemini and return the text."""
    url = f"{GEMINI_BASE}/{MODEL}:generateContent?key={API_KEY}"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": max_tokens,
            # Gemini 2.5 Flash is a thinking model — disable thinking so
            # output tokens aren't consumed by internal reasoning.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
    )

    try:
        resp = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        logger.error("Gemini HTTP %s: %s", e.code, err_body)
        raise

    resp_body = resp.read().decode("utf-8")
    data = json.loads(resp_body)
    candidates = data.get("candidates", [])
    if not candidates:
        logger.warning("Gemini returned no candidates. Response: %s", resp_body[:300])
        return ""
    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    # Gemini thinking models may return multiple parts — take the text from
    # the last part (the actual response), skipping thought/introspection parts.
    texts = [p.get("text", "") for p in parts if p.get("text")]
    if not texts:
        logger.warning("Gemini returned no text parts. Parts: %s",
                       json.dumps(parts, ensure_ascii=False)[:300])
        return ""
    return "".join(texts)


_CATEGORY_LABELS = {
    "ai_news": "AI行业",
    "world_news": "国际",
    "china_news": "中国观察",
    "stock_news": "全球市场",
}

_CATEGORY_GUIDANCE = {
    "ai_news": "聚焦技术突破、产品发布、行业趋势。用通俗比喻解释技术概念。",
    "world_news": "聚焦地缘政治、重大事件、全球影响。突出对中国读者的关联性。",
    "china_news": "聚焦国际媒体对中国政策、经济、社会的独立分析与深度报道。突出普通人的切身感受和实际影响。",
    "stock_news": "聚焦全球市场（美股、亚洲、欧洲）的重大波动、央行政策、板块轮动。提取关键数字（涨跌幅、点位）和驱动因素。特别关注与中国市场相关的国际财经动向。",
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
        raw = _chat(prompt, max_tokens=8192)
        highlights = _parse_json(raw)
        logger.info("%s summary generated (%d items)", category, len(highlights))
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
