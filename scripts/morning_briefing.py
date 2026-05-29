"""
Morning Briefing — tự động gửi báo cáo sáng qua Telegram.

Nội dung:
    1. Tin tức tech hôm nay (DuckDuckGo)
    2. TODO items chưa xong từ devlog.md
    3. Tóm tắt tổng hợp qua AgentCrew (ManagerAgent)

Lên lịch (Windows Task Scheduler):
    - Program: C:\\path\\to\\LoLM\\.venv\\Scripts\\python.exe
    - Arguments: scripts\\morning_briefing.py
    - Start in: C:\\path\\to\\LoLM
    - Trigger: Daily 7:00 AM

Chạy thủ công để test:
    python scripts/morning_briefing.py
    python scripts/morning_briefing.py --dry-run  # không gửi Telegram
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from dotenv import load_dotenv
load_dotenv(root / ".env")


def _get_news(n: int = 5) -> str:
    """Lấy tin tức tech mới nhất từ DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
        results = list(DDGS().text("AI technology news today", max_results=n))
        if not results:
            return "Không lấy được tin tức."
        return "\n".join(f"• {r['title']}" for r in results)
    except Exception as e:
        return f"Lỗi lấy tin tức: {e}"


def _get_todos() -> str:
    """Đọc TODO items chưa xong từ devlog.md."""
    devlog = root / "devlog.md"
    if not devlog.exists():
        return "Không tìm thấy devlog.md"
    todos = [
        line.strip()
        for line in devlog.read_text(encoding="utf-8").splitlines()
        if "[ ]" in line
    ]
    return "\n".join(todos[:5]) if todos else "Không có TODO item nào."


async def run(dry_run: bool = False) -> None:
    today    = datetime.now().strftime("%Y-%m-%d %H:%M")
    headlines = _get_news()
    todo_text = _get_todos()

    # Tổng hợp qua AgentCrew (dùng ManagerAgent)
    summary = ""
    try:
        from src.crew.crew import AgentCrew, CrewEvent
        prompt = (
            f"Tóm tắt ngắn gọn (3-5 câu) tin tức công nghệ hôm nay và "
            f"đề xuất ưu tiên từ TODO list:\n\n"
            f"TIN TỨC:\n{headlines}\n\n"
            f"TODO:\n{todo_text}"
        )
        crew = AgentCrew()
        for event in crew.run(prompt):
            if isinstance(event, str):
                summary = event
    except Exception as e:
        summary = f"(Không tổng hợp được: {e})"

    msg = (
        f"🌅 *Morning Briefing — {today}*\n\n"
        f"📰 *Tin tức hôm nay:*\n{headlines}\n\n"
        f"📋 *TODO chưa xong:*\n{todo_text}\n\n"
        f"🤖 *Tóm tắt AI:*\n{summary[:800]}"
    )

    if dry_run:
        print("=== DRY RUN — Nội dung sẽ gửi ===")
        print(msg)
        return

    import os
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("❌ Thiếu TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID trong .env")
        return

    from telegram import Bot
    bot = Bot(token=token)
    async with bot:
        # Split nếu dài hơn 4096 chars
        limit = 4000
        for i in range(0, len(msg), limit):
            await bot.send_message(
                chat_id=int(chat_id),
                text=msg[i : i + limit],
                parse_mode="Markdown",
            )
    print(f"✅ Morning briefing đã gửi lúc {today}")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    asyncio.run(run(dry_run=dry))
