"""Call OpenAI-compatible API to generate Chinese summaries and analysis."""

import logging
import os
import json

logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")

REQUEST_TIMEOUT = 60


def _client():
    """Lazy-init the OpenAI client."""
    from openai import OpenAI
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=REQUEST_TIMEOUT)


def is_available() -> bool:
    return bool(API_KEY)


def _chat(prompt: str, max_tokens: int = 2000) -> str:
    """Send a chat completion request and return the content."""
    client = _client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


def summarize_github(projects: list[dict]) -> list[dict]:
    """Generate '为什么值得关注' for each GitHub project."""
    if not projects or not is_available():
        return projects

    # Build a batch prompt with all projects
    items_text = "\n\n".join(
        f"[{i+1}] {p['name']}\nStars: {p['stars']}\nLanguage: {p['language']}\n"
        f"Description: {p['description']}\nKeyword matched: {p['keyword']}"
        for i, p in enumerate(projects)
    )

    prompt = (
        "你是一个AI技术分析师。以下是从GitHub搜索到的今日热门AI开源项目。"
        "请为每个项目用中文写一句'为什么值得关注'（30字以内），"
        "说明该项目的独特价值或趋势意义。\n\n"
        f"{items_text}\n\n"
        "请按以下JSON格式输出（仅输出JSON，不要其他文字）：\n"
        '[{"index": 1, "why": "..."}, {"index": 2, "why": "..."}, ...]'
    )

    try:
        raw = _chat(prompt, max_tokens=1000)
        logger.info("GitHub summary generated")
        highlights = json.loads(raw)
        for h in highlights:
            idx = h["index"] - 1
            if 0 <= idx < len(projects):
                projects[idx]["why_notable"] = h["why"]
    except Exception as e:
        logger.warning("GitHub summarization failed: %s", e)
        for p in projects:
            p["why_notable"] = p["description"][:60] if p.get("description") else "值得关注的开源项目"

    return projects


def summarize_news(entries: list[dict], category: str) -> list[dict]:
    """Generate Chinese summary and 'why worth reading' for news entries."""
    if not entries or not is_available():
        return entries

    items_text = "\n\n".join(
        f"[{i+1}] 标题: {e['title']}\n来源: {e['source']}\n原文摘要: {e['summary']}"
        for i, e in enumerate(entries)
    )

    cat_label = "AI行业" if category == "ai_news" else "全球重要"
    prompt = (
        f"你是一个新闻编辑。以下是从RSS抓取的{cat_label}新闻。"
        "请为每条新闻生成：\n"
        "1. 简短中文摘要（50字以内）\n"
        "2. 为什么值得看（30字以内）\n\n"
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


def suggest_xhs_topic(github_projects: list[dict], ai_news: list[dict]) -> dict:
    """Suggest one GitHub project best suited for a Xiaohongshu (小红书) post."""
    if not is_available():
        return {"title": "今日推荐", "repo": "", "angle": "AI功能暂不可用，请配置OPENAI_API_KEY后获取推荐"}

    projects_text = "\n".join(
        f"- {p['name']}: {p['description']} (⭐{p['stars']})"
        for p in github_projects[:5]
    )
    news_text = "\n".join(
        f"- {e['title']}" for e in ai_news[:3]
    )

    prompt = (
        "你是一个小红书科技博主，擅长发现适合在小红书上分享的AI开源工具。\n\n"
        "今日热门GitHub AI项目：\n"
        f"{projects_text}\n\n"
        "今日AI行业新闻：\n"
        f"{news_text}\n\n"
        "请从GitHub项目中选择一个最适合做成小红书笔记的项目，"
        "考虑因素：对普通用户的吸引力、视觉效果、实用价值、新颖性。\n\n"
        "请按以下JSON格式输出（仅输出JSON，不要其他文字）：\n"
        '{"repo": "项目完整名称", "title": "小红书标题（吸引眼球，含emoji，20字以内）", '
        '"angle": "内容角度（3个要点，用竖线|分隔，每个10字以内）", '
        '"why": "为什么这个项目适合小红书（一句话）"}'
    )

    try:
        raw = _chat(prompt, max_tokens=600)
        logger.info("XHS suggestion generated")
        return json.loads(raw)
    except Exception as e:
        logger.warning("XHS suggestion failed: %s", e)
        return {"title": "今日推荐", "repo": "", "angle": f"生成失败: {e}"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test without API key
    print(f"API available: {is_available()}")

    if is_available():
        # Quick test
        test_projects = [
            {"name": "test/repo", "stars": 100, "language": "Python",
             "description": "A test AI agent framework", "keyword": "ai-agent",
             "url": "https://github.com/test/repo"}
        ]
        result = summarize_github(test_projects)
        print(result)
