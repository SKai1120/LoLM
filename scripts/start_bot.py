"""
Entry point cho Telegram Bot.

Chạy:
    python scripts/start_bot.py

Yêu cầu:
    - File .env với TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID
    - ANTHROPIC_API_KEY cho AgentCrew (ManagerAgent dùng Claude API)
    - Ollama đang chạy tại localhost:11434
"""

import sys
from pathlib import Path

# Đảm bảo root dir trong sys.path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from dotenv import load_dotenv
load_dotenv(root / ".env")

from src.telegram_bot import build_app

if __name__ == "__main__":
    import os
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        print("❌ Thiếu TELEGRAM_BOT_TOKEN trong .env")
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  Thiếu ANTHROPIC_API_KEY — ManagerAgent sẽ không hoạt động")

    app = build_app()
    print("🤖 LoLM Telegram Bot đang chạy...")
    print("   Nhấn Ctrl+C để dừng")
    app.run_polling(drop_pending_updates=True)
