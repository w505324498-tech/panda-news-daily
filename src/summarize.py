"""Call OpenAI-compatible API to generate Chinese summaries and content creation analysis."""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")

REQUEST_TIMEOUT = 90

AUDIENCE_TAGS = ["普通用户", "AI爱好者", "开发者", "办公自动化"]


def _client():
    """Lazy-init the OpenAI client."""
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


# ── GitHub Analysis + Best Topic Picker (combined into one API call) ──────


def analyze_github_and_pick_best(
    projects: list[dict],
    ai_news: list[dict],
) -> tuple[list[dict], dict]:
    """
    Analyze GitHub projects for content creation suitability and pick the best topic.

    Returns (analyzed_projects, best_topic).
    Each project gains: why_notable, content_scores {xhs, douyin, gzh}, audience [].
    best_topic has: recommendation_score, recommendation_reason,
                    recommended_platform, suggested_titles [3].
    """
    best_topic: dict = {
        "recommendation_score": 0,
        "recommendation_reason": "",
        "recommended_platform": "",
        "suggested_titles": [],
    }

    if not projects or not is_available():
        # Fallback: no AI available
        for p in projects:
            p["why_notable"] = (p.get("description") or "值得关注的开源项目")[:60]
            p["content_scores"] = {"xhs": 0, "douyin": 0, "gzh": 0}
            p["audience"] = []
        best_topic["recommendation_reason"] = "AI 摘要功能暂不可用，请配置 OPENAI_API_KEY 后获取智能推荐"
        return projects, best_topic

    # Build prompt
    projects_text = "\n\n".join(
        f"[{i+1}] {p['name']}\n"
        f"Stars: {p['stars']}\nLanguage: {p['language']}\n"
        f"Description: {p['description']}\nKeyword matched: {p['keyword']}"
        for i, p in enumerate(projects)
    )
    news_text = "\n".join(f"- {e['title']}" for e in ai_news[:3])

    prompt = (
        "你是一位资深内容创作顾问兼AI技术分析师。你的任务是：\n"
        "1. 分析每个GitHub项目的技术价值和内容创作潜力\n"
        "2. 从中选出1个最适合做成自媒体内容的项目\n\n"

        "## 评分标准\n"
        "- 小红书：项目是否有好看的UI/GUI/可视化效果？能否做出吸引人的图文笔记？\n"
        "- 抖音：项目操作是否可录屏演示？是否有视觉冲击力或「wow moment」？\n"
        "- 公众号：项目是否有深度技术分析价值？能否写成技术解读长文？\n\n"

        "## 受众判断（可多选）\n"
        "普通用户：有GUI、一键部署、不需要写代码\n"
        "AI爱好者：免费、好玩、跟AI热门话题相关\n"
        "开发者：需要写代码、CLI工具、框架/库\n"
        "办公自动化：能提效、自动处理文件/数据/日程\n\n"

        "## 最佳选题优先考虑\n"
        "- 视觉冲击力强（有截图/演示效果）\n"
        "- 普通用户能理解和使用\n"
        "- 免费或低成本\n"
        "- 跟当前AI热点相关\n\n"

        f"## 今日GitHub热门AI项目\n{projects_text}\n\n"
        f"## 今日AI行业新闻（辅助判断趋势关联度）\n{news_text}\n\n"

        "请输出以下JSON（仅输出JSON，不要其他文字）：\n"
        "{\n"
        '  "projects": [\n'
        '    {\n'
        '      "index": 1,\n'
        '      "why_notable": "中文，30字以内，说明该项目的独特价值或趋势意义",\n'
        '      "content_scores": {"xhs": 4, "douyin": 3, "gzh": 5},\n'
        '      "audience": ["开发者", "AI爱好者"]\n'
        '    }\n'
        '  ],\n'
        '  "best_topic": {\n'
        '    "project_index": 3,\n'
        '    "recommendation_score": 5,\n'
        '    "recommendation_reason": "推荐理由，50字以内",\n'
        '    "recommended_platform": "小红书",\n'
        '    "suggested_titles": [\n'
        '      "GitHub爆火项目，3天涨3000 Star",\n'
        '      "这个AI工具让我少干2小时活",\n'
        '      "又发现一个免费AI神器"\n'
        '    ]\n'
        '  }\n'
        '}\n\n'
        "注意：suggested_titles 必须是3个吸引眼球的中文标题（含emoji，各20字以内），"
        "模仿小红书/抖音爆款标题风格。recommended_platform 为 小红书/抖音/小红书+抖音 之一。"
        "content_scores 分值范围1-5，没有内容创作价值为1。"
    )

    try:
        raw = _chat(prompt, max_tokens=3000)
        logger.info("GitHub analysis + best topic generated")
        data = json.loads(raw)

        # Apply project-level analysis
        for item in data.get("projects", []):
            idx = item["index"] - 1
            if 0 <= idx < len(projects):
                projects[idx]["why_notable"] = item.get("why_notable", "")
                projects[idx]["content_scores"] = item.get("content_scores", {"xhs": 0, "douyin": 0, "gzh": 0})
                audience = item.get("audience", [])
                # Validate audience tags
                projects[idx]["audience"] = [t for t in audience if t in AUDIENCE_TAGS]

        # Extract best_topic
        bt = data.get("best_topic", {})
        best_topic = {
            "recommendation_score": int(bt.get("recommendation_score", 0)),
            "recommendation_reason": bt.get("recommendation_reason", ""),
            "recommended_platform": bt.get("recommended_platform", ""),
            "suggested_titles": bt.get("suggested_titles", [])[:3],
            "project_index": int(bt.get("project_index", 1)) - 1,
        }
        # Link to actual project name
        pi = best_topic["project_index"]
        if 0 <= pi < len(projects):
            best_topic["repo"] = projects[pi]["name"]
            best_topic["repo_url"] = projects[pi]["url"]
        else:
            best_topic["repo"] = projects[0]["name"] if projects else ""
            best_topic["repo_url"] = projects[0]["url"] if projects else ""

    except Exception as e:
        logger.warning("GitHub analysis failed: %s", e)
        for p in projects:
            p["why_notable"] = (p.get("description") or "值得关注的开源项目")[:60]
            p["content_scores"] = {"xhs": 0, "douyin": 0, "gzh": 0}
            p["audience"] = []
        best_topic["recommendation_reason"] = f"AI 分析暂时不可用: {e}"

    return projects, best_topic


# ── News Summarization (unchanged) ─────────────────────────────────────────


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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"API available: {is_available()}")

    if is_available():
        test_projects = [
            {"name": "test/repo", "stars": 100, "language": "Python",
             "description": "A test AI agent framework", "keyword": "ai-agent",
             "url": "https://github.com/test/repo"}
        ]
        projs, best = analyze_github_and_pick_best(test_projects, [])
        print("Projects:", projs)
        print("Best:", best)
