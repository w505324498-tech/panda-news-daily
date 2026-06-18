# Panda News Daily v2 — 新增国内新闻 + 股市板块

**Date:** 2026-06-18
**Status:** approved

## Overview

在现有 AI 新闻 + 国际新闻基础上，新增**国内新闻**和**股市要闻**两个板块，
同时增加**实时指数摘要**（上证/深证/恒生/标普500/纳指）。

## Data Sources

### china_news (新增)
| Source | URL |
|--------|-----|
| 人民网 时政 | http://www.people.com.cn/rss/politics.xml |
| 人民网 社会 | http://www.people.com.cn/rss/society.xml |
| 新浪新闻 要闻 | http://rss.sina.com.cn/news/marquee/ddt.xml |

### stock_news (新增)
| Source | URL |
|--------|-----|
| 人民网 财经 | http://www.people.com.cn/rss/finance.xml |
| MarketWatch | https://feeds.marketwatch.com/marketwatch/topstories |
| WSJ Markets | https://feeds.a.dj.com/rss/RSSMarketsMain.xml |

### Stock Indices (新增)
腾讯行情 API: `http://qt.gtimg.cn/q=sh000001,sz399001,hkHSI,usSPX.GI,usIXIC.GI`
返回实时价/涨跌幅/涨跌额，免费无需 Key。

## Architecture

```
                                    ┌──────────────┐
                                    │  main.py     │
                                    │  orchestrator│
                                    └──┬───┬───┬──┘
                                       │   │   │
              ┌────────────────────────┘   │   └──────────────────┐
              ▼                            ▼                      ▼
    ┌─────────────┐              ┌──────────────┐       ┌──────────────────┐
    │ fetch_rss   │              │ fetch_stock  │       │ summarize        │
    │ (4 categories)│            │ (indices)    │       │ (4 categories)   │
    └─────────────┘              └──────────────┘       └──────────────────┘
                                                              │
                                              ┌───────────────┘
                                              ▼
                                     ┌──────────────┐
                                     │ mailer       │
                                     │ (5-section)  │
                                     └──────────────┘
```

## Changes

### New file: `src/fetch_stock.py`
- `fetch_indices() -> dict` — hit Tencent API, parse garbled-GBK response, return {name, price, change_pct, change_amt} per index
- Handle network errors gracefully: return empty dict on failure

### Modified: `config/sources.yaml`
- Add `china_news:` (3 feeds) and `stock_news:` (3 feeds) categories
- Existing `ai_news` and `world_news` unchanged

### Modified: `src/summarize.py`
- Add `china_news` prompt: Chinese-language news, summarize in Chinese with "值得关注" angle
- Add `stock_news` prompt: market news, extract key data points (which market, what moved, why)

### Modified: `src/mailer.py`
- Add index ticker bar at top (5 indices inline)
- Add `🇨🇳 国内新闻` section (8 items)
- Add `📈 股市要闻` section (8 items)
- New helper `_index_bar(indices)` renders the compact index strip

### Modified: `src/main.py`
- Fetch 4 categories instead of 2
- Call `fetch_indices()` for live index data
- Summarize all 4 categories
- Pass indices to mailer

### Modified: `.github/workflows/daily.yml`
- `timeout-minutes: 15` → `25`

## Email Layout

```
┌───────────────────────────────────────────┐
│  📰 Panda News Daily · 2026-06-19        │
│  ┌─────────────────────────────────────┐  │
│  │ 上证 4090 ↓0.4%  深证 16030 ↑0.9% │  │
│  │ 恒生 23812 ↓2.0%  标普500  纳指    │  │
│  └─────────────────────────────────────┘  │
│  🧠 AI 行业新闻 (8条)                     │
│  🇨🇳 国内新闻 (8条)                       │
│  🌍 国际新闻 (8条)                        │
│  📈 股市要闻 (8条)                        │
└───────────────────────────────────────────┘
```

## Error Handling

- Any category fetch fails → that section shows "暂无数据"
- Stock index API fails → index bar hidden
- Summarization fails per-category → fallback to raw titles
- No single failure blocks the email

## Verification

1. Run `python -m src.main` locally, verify email has 4 sections + index bar
2. Push, trigger workflow_dispatch, verify email received with all content
3. Check logs: 4 RSS categories + 1 stock API call, 4 DeepSeek calls
