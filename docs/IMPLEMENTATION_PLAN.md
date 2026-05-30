# LoLM Multi-Agent System — Design & Implementation Specification

> **Mục đích tài liệu này:**
> 1. **Architecture Design** — đủ chi tiết để một AI agent thứ 3 tự implement theo
> 2. **Junior Developer Guide** — hướng dẫn từng bước để dev mới có thể tự triển khai

---

## 1. CONTEXT & MỤC TIÊU

Dự án LoLM đã có nền tảng local LLM hoàn chỉnh (Phase 1-5c, xem devlog.md). Giai đoạn tiếp theo
nâng cấp thành **Multi-Agent System** với:
- **Phân phối kép thông minh**: Task phức tạp → Claude API (cloud); task thực thi → Qwen local
- **Điều khiển từ xa**: Telegram Bot để ra lệnh từ điện thoại
- **Bảo mật truy cập**: Tailscale VPN mesh, không mở port
- **Tự động hóa**: Morning briefing tự gửi lúc 7:00 AM
- **Bộ nhớ dài hạn**: Tự ghi log mỗi phiên, searchable qua ChromaDB

---

## 2. TRẠNG THÁI HIỆN TẠI (Baseline)

| File | Chức năng | Tái dùng như thế nào |
|------|-----------|---------------------|
| `src/client.py` | `ChatSession` — Ollama multi-turn, memory compression | Không đổi |
| `src/router.py` | `select_model()` — keyword router qwen↔deepseek | Thêm `select_backend()` |
| `src/agent.py` | `Agent` — tool calling loop (5 tools) | Bọc thành CrewAI Tool |
| `src/rag.py` | `KnowledgeBase` — ChromaDB RAG, named KBs | Không đổi |
| `src/tui.py` | Textual TUI, /kb /agent /index commands | Thêm `/crew` command |

---

## 3. KIẾN TRÚC HỆ THỐNG (Target Architecture)

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT LAYER                               │
│  ┌─────────────────┐         ┌───────────────────────────────┐  │
│  │   TUI (Textual) │         │      Telegram Bot             │  │
│  │  /crew command  │         │  /ask /status /reset /brief   │  │
│  └────────┬────────┘         └──────────────┬────────────────┘  │
└───────────┼──────────────────────────────────┼───────────────────┘
            │                                  │
            ▼                                  ▼
┌───────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER (CrewAI)                    │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                       AgentCrew                              │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │  Manager Agent (Claude API — claude-sonnet-4-6)         │ │ │
│  │  │  Goal: Phân tích yêu cầu → Lập kế hoạch → Tổng hợp    │ │ │
│  │  └──────────────────────┬──────────────────────────────────┘ │ │
│  │                         │ subtasks                            │ │
│  │  ┌──────────────────────▼──────────────────────────────────┐ │ │
│  │  │  Executor Agent (Ollama — qwen2.5:14b)                  │ │ │
│  │  │  Goal: Thực thi subtask với tools                       │ │ │
│  │  │  Tools: read_file, list_dir, fetch_url,                 │ │ │
│  │  │         web_search, search_kb, git_log                  │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
            │                                  │
            ▼                                  ▼
┌──────────────────────┐         ┌──────────────────────────────────┐
│   STORAGE LAYER      │         │      NETWORK LAYER               │
│  ChromaDB (RAG)      │         │  Tailscale VPN mesh              │
│  data/logs/*.md      │         │  • SSH over Tailscale (TUI)      │
│  sessions/*.json     │         │  • Telegram long-polling         │
└──────────────────────┘         └──────────────────────────────────┘
```

---

## 4. TECHNOLOGY STACK

| Component | Công nghệ | Phiên bản | Lý do |
|-----------|-----------|-----------|-------|
| Agent Framework | CrewAI | >=0.80.0 | Có sẵn Manager/Executor pattern, role/goal/task |
| Cloud LLM | Anthropic API | claude-sonnet-4-6 | Tư duy chiến lược, tổng hợp |
| Local LLM | Ollama qwen2.5:14b | existing | Nhanh, free, 65.6 t/s |
| Vector DB | ChromaDB | >=0.5.0 (existing) | Memory + RAG |
| Telegram | python-telegram-bot | >=21.0 | Polling mode, no webhook needed |
| VPN | Tailscale | latest | Secure mesh, no port-forward |
| Scheduler | Windows Task Scheduler | built-in | Heartbeat automation |

---

## 5. CẤU TRÚC FILE (After Implementation)

```
LoLM/
├── src/
│   ├── client.py              # Ollama wrapper (không đổi)
│   ├── router.py              # + select_backend()
│   ├── agent.py               # Tool calling (không đổi)
│   ├── rag.py                 # ChromaDB RAG (không đổi)
│   ├── tui.py                 # + /crew command
│   ├── crew/                  # NEW — CrewAI module
│   │   ├── __init__.py
│   │   ├── agents.py          # ManagerAgent + ExecutorAgent
│   │   ├── tasks.py           # Task templates
│   │   ├── tools.py           # CrewAI Tool wrappers
│   │   └── crew.py            # AgentCrew orchestrator
│   └── telegram_bot.py        # NEW — Telegram bot
├── scripts/
│   ├── benchmark.py           # (existing)
│   ├── check_gpu.py           # (existing)
│   ├── rag_chat.py            # (existing)
│   ├── start_bot.py           # NEW — Bot entry point
│   └── morning_briefing.py    # NEW — Heartbeat automation
├── docs/
│   ├── setup.md               # (existing)
│   ├── multi_agent.md         # NEW — Usage guide
│   ├── remote_access.md       # NEW — Tailscale setup
│   └── IMPLEMENTATION_PLAN.md # THIS FILE
├── .env.example               # NEW — Template
├── requirements.txt           # MODIFIED
└── devlog.md                  # MODIFIED
```

---

## 6. JUNIOR DEVELOPER — IMPLEMENTATION GUIDE

### Prerequisite
- [ ] Python 3.10+
- [ ] Ollama running: `curl http://localhost:11434/api/tags`
- [ ] qwen2.5:14b pulled
- [ ] Git repo cloned
- [ ] Anthropic API key (console.anthropic.com)
- [ ] Telegram bot token (@BotFather)

### Step 1 — Install Dependencies

```bash
cd LoLM
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Step 2 — Setup .env

```bash
cp .env.example .env
# Edit .env with real API keys
```

### Step 3 — Create src/crew/ Module

```bash
mkdir src/crew && touch src/crew/__init__.py
```

Create 4 files:
1. `src/crew/tools.py` — 6 tool wrappers
2. `src/crew/agents.py` — ManagerAgent + ExecutorAgent
3. `src/crew/tasks.py` — 3 task templates
4. `src/crew/crew.py` — AgentCrew orchestrator

**Test:**
```bash
python -c "
from src.crew.crew import AgentCrew
crew = AgentCrew()
for event in crew.run('Liệt kê 3 điểm mạnh Python'):
    print(event)
"
```

### Step 4 — Add select_backend() to router.py

```python
# Add to end of src/router.py
MODEL_CLOUD = "claude-sonnet-4-6"
_CLOUD_KEYWORDS = [...]

def select_backend(prompt: str) -> tuple[str, str]:
    ...
```

### Step 5 — Add /crew Command to TUI

In `src/tui.py`:
- Import: `from src.crew.crew import AgentCrew, CrewEvent`
- Add field: `self._crew: AgentCrew | None = None` in `__init__`
- Add handler in `_handle_command()` for `/crew`
- Add worker `_do_crew()` similar to `_do_agent()`

### Step 6 — Create Telegram Bot

1. Message @BotFather: `/newbot`
2. Get token → add to `.env`
3. Message @userinfobot → get Chat ID → add to `.env`
4. Create `src/telegram_bot.py` with handlers
5. Create `scripts/start_bot.py` entry point

**Test:**
```bash
python scripts/start_bot.py
# Send /ask hello from Telegram
```

### Step 7 — Setup Tailscale

1. Download: https://tailscale.com/download
2. Install on Windows & phone
3. Sign in with same account
4. Get IP: `tailscale ip -4`
5. Enable SSH on Windows: Settings → OpenSSH Server
6. Connect from phone: `ssh user@<tailscale-ip>`

### Step 8 — Setup Morning Briefing

1. Create `scripts/morning_briefing.py`
2. Open Task Scheduler (Windows)
3. Create task → Daily 7:00 AM
4. Program: `.venv\Scripts\python.exe`
5. Arguments: `scripts/morning_briefing.py`

**Test manually:**
```bash
python scripts/morning_briefing.py --dry-run
```

### Step 9 — Verify Log Files

Auto logging to `data/logs/daily_YYYY-MM-DD.md` after each crew run.

**Sync with Obsidian:**
- Open Obsidian
- Settings → Vault → Open folder as vault
- Select `data/logs/`

### Step 10 — Commit & Push

```bash
git add .
git commit -m "Phase 6: Multi-Agent System with CrewAI, Telegram, Tailscale"
git push -u origin <branch-name>
```

---

## 7. VERIFICATION CHECKLIST

```bash
# Test each component
python -c "from src.router import select_backend; print(select_backend('thiết kế hệ thống'))"
# Expected: ('cloud', 'claude-sonnet-4-6')

python -c "from src.crew.crew import AgentCrew; print('AgentCrew imports OK')"

python scripts/start_bot.py
# Send /status from Telegram

python scripts/morning_briefing.py
# Check Telegram for briefing message

ls data/logs/
# Should have daily_YYYY-MM-DD.md
```

---

## 8. SECURITY NOTES

1. `.env` never commits (in .gitignore)
2. Telegram auth guard — only TELEGRAM_CHAT_ID can control bot
3. Tailscale mesh — only same account devices connect
4. Anthropic API — set rate limits to avoid overspend
5. Ollama — listens only localhost:11434
