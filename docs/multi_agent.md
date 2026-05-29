# Multi-Agent System — Hướng Dẫn Sử Dụng

## Kiến Trúc

```
User → AgentCrew.run(task)
           ↓
    ManagerAgent (Claude API)   ← lập kế hoạch, tổng hợp
           ↓ subtasks
    ExecutorAgent (Qwen local)  ← thực thi với tools
           ↓ results
    ManagerAgent synthesize     ← báo cáo cuối
```

## Tools ExecutorAgent có thể dùng

| Tool | Chức năng |
|------|-----------|
| `ReadFile` | Đọc file text/code/markdown |
| `ListDir` | Liệt kê thư mục |
| `FetchURL` | Fetch nội dung trang web |
| `WebSearch` | Tìm kiếm DuckDuckGo |
| `SearchKB` | Tìm trong knowledge base |
| `GitLog` | Xem git history |

## Dùng trong TUI

```bash
python -m src.tui

# Trong TUI:
/crew        # bật crew mode
# Giờ gõ bất kỳ câu hỏi nào → Manager phân tích → Executor thực thi

/crew        # tắt crew mode, về chat thường
```

## Dùng qua Telegram

```
/ask <câu hỏi>
```

Ví dụ:
```
/ask Thiết kế kiến trúc database cho app quản lý task
/ask Tóm tắt các file Python trong thư mục src/
/ask Tìm tin tức mới nhất về model AI tháng này
```

## Dùng trong code

```python
from dotenv import load_dotenv
load_dotenv()

from src.crew.crew import AgentCrew, CrewEvent

crew = AgentCrew()

for event in crew.run("Phân tích codebase và đề xuất cải tiến"):
    if isinstance(event, CrewEvent):
        print(f"[{event.phase}] {event.message}")
    else:
        print("=== KẾT QUẢ ===")
        print(event)
```

## Log tự động

Sau mỗi crew run, kết quả tự ghi vào:
```
data/logs/daily_YYYY-MM-DD.md
```

Có thể mở thư mục `data/logs/` trong **Obsidian** để xem log đẹp mắt.

## Cấu hình

Trong `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...   # bắt buộc cho ManagerAgent
OLLAMA_BASE_URL=http://localhost:11434  # optional, mặc định localhost
```
