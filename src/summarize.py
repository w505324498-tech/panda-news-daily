"""Call OpenAI-compatible API to generate Chinese summaries and content creation analysis."""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or "https://api.deepseek.com"
MODEL = os.getenv("OPENAI_MODEL", "").strip() or "deepseek-chat"

REQUEST_TIMEOUT = 120

AUDIENCE_TAGS = ["AI爱好者", "上班族", "内容创作者", "开发者"]


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
            p["one_liner"] = _cn_fallback(p)
            p["what_is_it"] = _cn_fallback(p)
            p["why_notable"] = ["值得关注的开源AI项目"]
            p["content_scores"] = {"xhs": 0, "douyin": 0, "gzh": 0}
            p["audience"] = []
            p["xhs_core_hook"] = ""
            p["xhs_titles"] = []
        best_topic["recommendation_reason"] = "AI 摘要功能暂不可用，请配置 OPENAI_API_KEY 后获取智能推荐"
        return projects, best_topic

    # Build prompt — no English, all Chinese output
    projects_text = "\n\n".join(
        f"[{i+1}] {p['name']}\n"
        f"Stars: {p['stars']}\nLanguage: {p['language']}\n"
        f"Description: {p['description']}\nKeyword: {p['keyword']}"
        for i, p in enumerate(projects)
    )
    news_text = "\n".join(f"- {e['title']}" for e in ai_news[:3])

    prompt = (
        "你是一位小红书/抖音AI内容创作顾问。你的读者是普通中国人，不是程序员。\n\n"

        "## 核心任务\n"
        "分析以下GitHub AI项目，把每个项目翻译成「小白都能看懂的介绍」，并给出可直接用于内容创作的素材。\n\n"

        "## 输出语言要求\n"
        "- 全部使用中文，禁止出现英文单词（项目名除外）\n"
        "- 用生活化的比喻解释技术概念\n"
        "- 避免术语：API、CLI、deploy、framework、pipeline 等，如果必须出现要翻译成中文\n"
        "- 想象你在给一个不懂编程的朋友介绍这个工具\n\n"

        "## 评分标准（内容创作价值）\n"
        "- 小红书（1-5）：有好看的界面/可视化效果吗？能做出吸引人的图文笔记吗？\n"
        "- 抖音（1-5）：操作可录屏演示吗？有视觉冲击力吗？\n"
        "- 公众号（1-5）：有深度解读价值吗？能写成技术科普长文吗？\n\n"

        "## 受众标签（可多选）\n"
        "AI爱好者：对AI感兴趣、喜欢尝试新工具\n"
        "上班族：需要提效的职场人\n"
        "内容创作者：想做AI相关内容的自媒体人\n"
        "开发者：会写代码的技术人员\n\n"

        f"## 今日GitHub AI项目\n{projects_text}\n\n"
        f"## 今日AI新闻趋势（参考）\n{news_text}\n\n"

        "## 输出JSON格式（仅输出JSON，不要其他文字）\n"
        "{\n"
        '  "projects": [\n'
        '    {\n'
        '      "index": 1,\n'
        '      "one_liner": "一句话中文介绍，15字以内，让小白秒懂这项目能干嘛",\n'
        '      "what_is_it": "用2-3句通俗中文解释这个项目是什么、解决什么问题。不要技术术语，用生活化比喻。50字以内。",\n'
        '      "why_notable": ["原因1", "原因2", "原因3"],\n'
        '      "content_scores": {"xhs": 4, "douyin": 3, "gzh": 5},\n'
        '      "audience": ["AI爱好者", "上班族"],\n'
        '      "xhs_core_hook": "如果发小红书，1句话核心卖点（20字以内，要有吸引力）",\n'
        '      "xhs_titles": ["小红书标题1（含emoji，20字以内）", "标题2", "标题3"]\n'
        '    }\n'
        '  ],\n'
        '  "best_topic": {\n'
        '    "project_index": 2,\n'
        '    "recommendation_score": 5,\n'
        '    "recommendation_reason": "一句话说明为什么这个项目最适合做内容，50字以内",\n'
        '    "recommended_platform": "小红书",\n'
        '    "suggested_titles": ["标题1", "标题2", "标题3"]\n'
        '  }\n'
        '}\n\n'

        "## 最佳选题筛选优先级\n"
        "高优先级（优先选这些类型的项目）：\n"
        "Claude Code / Codex / Gemini / MCP / AI Agent / AI办公工具 / AI自动化工具 / "
        "效率工具 / 内容创作工具 / 可以录屏演示的工具\n\n"
        "低优先级（降低权重）：\n"
        "纯SDK / Framework / Library / 纯开发工具 / 普通人完全无法理解的项目\n\n"

        "## 关键要求\n"
        "- 所有文字必须中文，不要照搬英文描述\n"
        "- one_liner 和 what_is_it 要让完全不懂技术的人也能看懂\n"
        "- why_notable 从内容创作角度写：这个项目有什么值得「发」的？\n"
        "- xhs_core_hook 要像小红书爆款标题一样有吸引力\n"
        "- xhs_titles 3个不同角度：实用型、猎奇型、情感共鸣型\n"
        "- 最佳选题严格按上面的优先级权重筛选\n"
        "- content_scores 从内容创作难度和吸引力角度打分，不要从技术角度\n"
        "- JSON 必须完整闭合"
    )

    try:
        raw = _chat(prompt, max_tokens=4000)
        logger.info("GitHub analysis + best topic generated")
        data = json.loads(raw)

        # Apply project-level analysis
        for item in data.get("projects", []):
            idx = item["index"] - 1
            if 0 <= idx < len(projects):
                projects[idx]["one_liner"] = item.get("one_liner", _cn_fallback(projects[idx]))
                projects[idx]["what_is_it"] = item.get("what_is_it", _cn_fallback(projects[idx]))
                projects[idx]["why_notable"] = item.get("why_notable", ["值得关注的开源AI项目"])[:3]
                projects[idx]["content_scores"] = item.get("content_scores", {"xhs": 0, "douyin": 0, "gzh": 0})
                audience = item.get("audience", [])
                projects[idx]["audience"] = [t for t in audience if t in AUDIENCE_TAGS]
                projects[idx]["xhs_core_hook"] = item.get("xhs_core_hook", "")
                projects[idx]["xhs_titles"] = item.get("xhs_titles", [])[:3]

        # Extract best_topic
        bt = data.get("best_topic", {})
        best_topic = {
            "recommendation_score": int(bt.get("recommendation_score", 0)),
            "recommendation_reason": bt.get("recommendation_reason", ""),
            "recommended_platform": bt.get("recommended_platform", ""),
            "suggested_titles": bt.get("suggested_titles", [])[:3],
            "project_index": int(bt.get("project_index", 1)) - 1,
        }
        pi = best_topic["project_index"]
        if 0 <= pi < len(projects):
            best_topic["repo"] = projects[pi]["name"]
            best_topic["repo_url"] = projects[pi]["url"]
        else:
            best_topic["repo"] = projects[0]["name"] if projects else ""
            best_topic["repo_url"] = projects[0]["url"] if projects else ""

    except json.JSONDecodeError as e:
        logger.warning("GitHub analysis JSON parse failed: %s\nRaw: %.200s", e, raw)
        _apply_fallback(projects, best_topic, f"AI 返回格式异常，请检查模型配置")
    except Exception as e:
        logger.warning("GitHub analysis API call failed [%s]: %s", type(e).__name__, e)
        logger.debug("API config: base_url=%s model=%s key_len=%d", BASE_URL, MODEL, len(API_KEY))
        _apply_fallback(projects, best_topic, f"AI 分析暂时不可用: {e}")

    return projects, best_topic


def _cn_fallback(p: dict) -> str:
    """Generate a minimal Chinese fallback description."""
    desc = (p.get("description") or "").strip()
    if desc:
        return desc[:80]
    return "AI开源项目"


def _apply_fallback(projects: list[dict], best_topic: dict, reason: str) -> None:
    """Apply fallback values when AI analysis fails."""
    for p in projects:
        p["one_liner"] = _cn_fallback(p)
        p["what_is_it"] = _cn_fallback(p)
        p["why_notable"] = ["值得关注的开源AI项目"]
        p["content_scores"] = {"xhs": 0, "douyin": 0, "gzh": 0}
        p["audience"] = []
        p["xhs_core_hook"] = ""
        p["xhs_titles"] = []
    best_topic["recommendation_reason"] = reason


# ── XHS Draft Generator ──────────────────────────────────────────────────────


def generate_xhs_draft(best_project: dict, ai_news: list[dict]) -> dict:
    """
    Generate a full, ready-to-publish Xiaohongshu draft for a single best project.

    Returns a dict with: project_name, one_liner, why_notable, xhs_titles (5),
    xhs_body (300-500 chars), cover_texts (3), screenshots, publish_checklist.
    """
    empty: dict = {
        "project_name": "",
        "one_liner": "",
        "why_notable": [],
        "xhs_titles": [],
        "xhs_body": "",
        "cover_texts": [],
        "screenshots": [],
        "publish_checklist": "",
    }

    if not best_project or not is_available():
        return empty

    proj_info = (
        f"项目名：{best_project.get('name', '')}\n"
        f"Stars：{best_project.get('stars', 0)}\n"
        f"描述：{best_project.get('description', '')}\n"
        f"语言：{best_project.get('language', '')}\n"
        f"AI分析的一句话介绍：{best_project.get('one_liner', '')}\n"
        f"AI分析的通俗解释：{best_project.get('what_is_it', '')}"
    )
    news_hint = "\n".join(f"- {e['title']}" for e in ai_news[:3])

    prompt = (
        "你是一个小红书AI内容博主，擅长用普通人视角分享AI工具。\n\n"

        "## 任务\n"
        f"以下GitHub项目被选为今日最佳选题，请为这个项目生成一篇可直接发布的小红书完整草稿。\n\n"

        f"## 项目信息\n{proj_info}\n\n"
        f"## 今日AI新闻（辅助判断时效角度）\n{news_hint}\n\n"

        "## 输出要求\n"
        "全部中文。JSON格式（仅输出JSON，不要其他文字）：\n"
        "{\n"
        '  "xhs_titles": ["标题1", "标题2", "标题3", "标题4", "标题5"],\n'
        '  "xhs_body": "正文内容（300-500字）",\n'
        '  "cover_texts": ["封面文案1", "封面文案2", "封面文案3"],\n'
        '  "screenshots": ["截图建议1", "截图建议2", "截图建议3"],\n'
        '  "publish_checklist": "发布前检查清单和测试步骤"\n'
        "}\n\n"

        "## 标题要求（xhs_titles，5个）\n"
        "- 普通人能看懂，一眼就知道这工具能干嘛\n"
        "- 不要营销号风格，不要夸张（❌「震惊！」「全网首发」「后悔没早知道」）\n"
        "- 像真实分享（✅「最近发现一个工具」「这个还挺好用的」）\n"
        "- 每标题20字以内，含emoji\n\n"

        "## 正文要求（xhs_body，300-500字）\n"
        "- 第一人称，像普通上班族在分享日常发现\n"
        "- 不像广告，不像AI生成，语气自然口语化\n"
        "- 不要堆砌技术术语\n"
        "- 可以用的表达：「最近发现一个工具」「准备试试看」「如果好用再继续分享」\n"
        "- 结构：发现 → 是什么 → 能干嘛 → 我的感受 → 推荐理由\n\n"

        "## 封面文案要求（cover_texts，3个）\n"
        "- 简短有冲击力，适合做封面大字\n"
        "- 例如：AI工具实测 / 本周AI发现 / 打工人AI神器\n"
        "- 每条10字以内\n\n"

        "## 截图建议（screenshots，3个）\n"
        "- 告诉我应该截什么图来配合文案\n"
        "- 例如：GitHub主页截图 / 工具运行界面截图 / 使用前后对比截图\n"
        "- 具体说明截哪个页面、哪个功能\n\n"

        "## 发布前检查（publish_checklist）\n"
        "- 直接告诉我：是否需要录屏 / 是否需要实际测试 / 是否可以直接发\n"
        "- 如果建议测试，给出最简单的测试步骤（2-3步）\n"
        "- 用 checklist 格式，每行一个 ✅ 开头的条目\n\n"

        "## 关键要求\n"
        "- 正文必须像真人写的，不像AI生成\n"
        "- 不要喊口号，不要「姐妹们冲啊」「家人谁懂啊」这种\n"
        "- 真诚分享的语气，像跟朋友聊天\n"
        "- 字号适中，每段不超过3行\n"
        "- JSON 必须完整闭合"
    )

    try:
        raw = _chat(prompt, max_tokens=2500)
        logger.info("XHS draft generated for %s", best_project.get("name", "unknown"))
        data = json.loads(raw)
        return {
            "project_name": best_project.get("name", ""),
            "one_liner": best_project.get("one_liner", ""),
            "why_notable": best_project.get("why_notable", []),
            "xhs_titles": data.get("xhs_titles", [])[:5],
            "xhs_body": data.get("xhs_body", ""),
            "cover_texts": data.get("cover_texts", [])[:3],
            "screenshots": data.get("screenshots", [])[:3],
            "publish_checklist": data.get("publish_checklist", ""),
        }
    except json.JSONDecodeError as e:
        logger.warning("XHS draft JSON parse failed: %s", e)
        return empty
    except Exception as e:
        logger.warning("XHS draft API call failed [%s]: %s", type(e).__name__, e)
        return empty


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
