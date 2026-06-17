# 📰 Panda News Daily

每日自动抓取 AI 行业新闻 + 全球重要新闻，调用 DeepSeek API 生成中文摘要，通过 HTML 邮件推送。

## 功能

- 🌍 **全球新闻** — BBC、NYT、Guardian、Al Jazeera、SCMP、Reuters 等 6 个 RSS 源
- 🧠 **AI 行业新闻** — Hacker News、TechCrunch、The Verge、ArXiv、MIT Tech Review 等 5 个源
- 🤖 **DeepSeek 中文摘要** — 每条新闻生成 50 字中文摘要 + "为什么值得看"
- 📧 **HTML 邮件推送** — 美观的卡片式邮件，手机/桌面均可阅读
- ⏰ **每日自动** — GitHub Actions 每天早上 8:00（北京时间）自动运行

## 快速开始

### 1. 克隆 & 安装

```bash
git clone https://github.com/w505324498/panda-intelligence-center.git
cd panda-intelligence-center
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key 和 SMTP 配置
```

### 3. 运行

```bash
python -m src.main
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | — |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名 | `deepseek-chat` |
| `SMTP_HOST` | SMTP 服务器 | — |
| `SMTP_PORT` | SMTP 端口 | `587` |
| `SMTP_USER` | SMTP 用户名 | — |
| `SMTP_PASS` | SMTP 密码 | — |
| `MAIL_TO` | 收件人 | — |
| `MAIL_FROM` | 发件人 | 同 `SMTP_USER` |

> **注意：** 即使不配置 `DEEPSEEK_API_KEY`，程序也能正常运行并发送邮件，只是摘要部分使用原始标题和简介，不做 AI 改写。

## GitHub Actions 定时运行

项目包含 `.github/workflows/daily.yml`，每天 UTC 00:00（北京时间 8:00）自动运行。

需要在 GitHub 仓库设置以下 Secrets：

| Secret | 说明 |
|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `SMTP_HOST` | SMTP 服务器地址 |
| `SMTP_PORT` | SMTP 端口 |
| `SMTP_USER` | SMTP 用户名 |
| `SMTP_PASS` | SMTP 密码 |
| `MAIL_TO` | 收件人邮箱 |
| `MAIL_FROM` | 发件人邮箱（可选，默认同 SMTP_USER） |

## 相关项目

- 🎬 [panda-xhs-weekly](https://github.com/w505324498/panda-xhs-weekly) — 每周 GitHub AI 热门项目 → 小红书/抖音选题

## 技术栈

- Python 3.11+
- DeepSeek API (OpenAI-compatible)
- feedparser (RSS)
- GitHub Actions (CI/CD)
