# 🐼 Panda Intelligence Center (PIC)

每日自动抓取 GitHub AI 热门项目 + AI 行业新闻 + 全球重要新闻，调用 DeepSeek/OpenAI API 生成中文摘要，通过邮件推送。

## 功能

- **GitHub AI 热门项目** — 搜索 ai-agent / mcp / claude-code / codex / llm-tools / prompt-engineering 关键词，按 stars 排序，去重取 Top 5
- **AI 行业新闻** — RSS 抓取，AI 摘要，取 3 条
- **全球重要新闻** — RSS 抓取，AI 摘要，取 3 条（仅个人阅读，不用于小红书选题）
- **小红书选题推荐** — AI 从当日 GitHub 项目中选 1 个最适合做小红书的，给出标题和内容角度
- **HTML 邮件** — 每天早上自动发送精美邮件

## 项目结构

```
├── .github/workflows/daily.yml   # GitHub Actions 定时任务
├── config/sources.yaml            # RSS 源配置
├── src/
│   ├── main.py                    # 主流程编排
│   ├── fetch_github.py            # GitHub Search API
│   ├── fetch_rss.py               # RSS/Atom 抓取
│   ├── summarize.py               # AI 摘要生成
│   ├── mailer.py                  # SMTP 邮件发送
│   └── dedupe.py                  # 去重工具
├── requirements.txt
├── .env.example
└── README.md
```

## 快速开始

### 1. 克隆仓库

```bash
git clone git@github.com:YOUR_USERNAME/panda-intelligence-center.git
cd panda-intelligence-center
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入真实配置
```

必需的环境变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | DeepSeek/OpenAI API Key | — |
| `OPENAI_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `OPENAI_MODEL` | 模型名 | `deepseek-chat` |
| `SMTP_HOST` | SMTP 服务器地址 | — |
| `SMTP_PORT` | SMTP 端口 | `587` |
| `SMTP_USER` | SMTP 用户名 | — |
| `SMTP_PASS` | SMTP 密码 | — |
| `MAIL_TO` | 收件人邮箱 | — |
| `MAIL_FROM` | 发件人邮箱 | 同 SMTP_USER |
| `GITHUB_TOKEN` | GitHub Token（可选，提高 API 限额） | — |

> **注意：** 即使不配置 `OPENAI_API_KEY`，程序也能正常运行并发送邮件，只是摘要部分使用原始标题和简介，不做 AI 改写。

### 4. 本地运行

```bash
# 加载 .env 并运行
set -a && source .env && set +a
python -m src.main
```

### 5. 查看结果

检查邮箱是否收到邮件。标题格式：`🐼 Panda Intelligence Daily - YYYY-MM-DD`

## GitHub Actions 配置

### Secrets 配置

在仓库 **Settings → Secrets and variables → Actions** 中添加以下 Secrets：

| Secret | 说明 | 必填 |
|--------|------|------|
| `OPENAI_API_KEY` | DeepSeek API Key | 否（但不填则无 AI 摘要） |
| `OPENAI_BASE_URL` | API 地址 | 否（默认 DeepSeek） |
| `OPENAI_MODEL` | 模型名 | 否（默认 deepseek-chat） |
| `GH_TOKEN` | GitHub Token | 否（但推荐，提高 API 限额到 5000/hr） |
| `SMTP_HOST` | SMTP 服务器 | ✅ 是 |
| `SMTP_PORT` | SMTP 端口 | 否（默认 587） |
| `SMTP_USER` | SMTP 用户名 | ✅ 是 |
| `SMTP_PASS` | SMTP 密码 | ✅ 是 |
| `MAIL_TO` | 收件邮箱 | ✅ 是 |
| `MAIL_FROM` | 发件邮箱 | 否（默认同 SMTP_USER） |

### 手动触发

1. 打开仓库的 **Actions** 标签页
2. 左侧选择 **Panda Intelligence Daily**
3. 点击 **Run workflow** 下拉按钮
4. 点击绿色 **Run workflow** 按钮
5. 等待约 2-3 分钟，检查邮箱

### 定时运行

默认每天 UTC 00:00（北京时间 08:00）自动运行。修改 `.github/workflows/daily.yml` 中的 `cron` 表达式即可调整时间。

## 修改 RSS 源

编辑 `config/sources.yaml`：

```yaml
ai_news:
  - name: "来源名称"
    url: "https://example.com/rss.xml"

world_news:
  - name: "来源名称"
    url: "https://example.com/feed/"
```

- 支持 RSS 2.0 和 Atom 格式
- 单个源失败不影响其他源
- 程序自动去重

## 常见问题

### Q: 邮件发送失败？
- 检查 SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS 是否正确
- QQ 邮箱需使用授权码而非登录密码
- Gmail 需开启 App Passwords
- 163 邮箱需开启 SMTP 服务
- 端口 587 用 STARTTLS，端口 465 用 SSL

### Q: GitHub API 返回 403？
- 未配置 `GITHUB_TOKEN` 时，匿名 API 限额为 60 次/小时
- 建议在 GitHub Settings → Developer settings → Personal access tokens 创建 Token
- Token 不需要任何权限（仅用于提高限额），设为 `GH_TOKEN` Secret

### Q: AI 摘要没生成？
- 检查 `OPENAI_API_KEY` 是否有效
- DeepSeek API 地址为 `https://api.deepseek.com`
- 确认账户有余额

### Q: RSS 源没有数据？
- 部分 RSS 源可能被墙（如 BBC、NYT），建议在 GitHub Actions 上运行
- 可在 `sources.yaml` 中替换为可访问的源

## 后续扩展方向

- **小红书文案生成** — 根据 GitHub 项目自动生成完整小红书图文
- **抖音脚本** — 生成 60 秒短视频口播脚本
- **Markdown 历史报告** — 每日生成 .md 文件存档在仓库
- **Slack/Telegram 推送** — 多通道通知
- **网页版** — GitHub Pages 展示历史报告

## License

MIT
