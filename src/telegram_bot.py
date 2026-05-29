"""
LoLM Telegram Bot — điều khiển AgentCrew từ xa qua long polling.

Commands:
    /ask <câu hỏi>  → chạy AgentCrew và trả kết quả
    /status         → kiểm tra Ollama + system health
    /reset          → xóa session hiện tại
    /brief          → trigger morning briefing ngay lập tức

Bảo mật: chỉ chấp nhận lệnh từ TELEGRAM_CHAT_ID trong .env
"""

from __future__ import annotations

import asyncio
import os
import subprocess

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


def _allowed(update: Update) -> bool:
    """Chỉ cho phép TELEGRAM_CHAT_ID trong .env ra lệnh."""
    allowed_id = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))
    return update.effective_chat.id == allowed_id


async def _send_chunks(update: Update, text: str) -> None:
    """Tự động split message > 4096 chars (Telegram limit)."""
    limit = 4000
    for i in range(0, len(text), limit):
        await update.message.reply_text(text[i : i + limit])


# ── Command handlers ───────────────────────────────────────────────────────────

async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    question = " ".join(context.args) if context.args else ""
    if not question:
        await update.message.reply_text("Cú pháp: /ask <câu hỏi>")
        return

    await update.message.reply_text("⚙️ Đang xử lý, vui lòng chờ...")

    from src.crew.crew import AgentCrew, CrewEvent

    crew         = AgentCrew()
    final_answer = ""

    for event in crew.run(question):
        if isinstance(event, CrewEvent):
            await update.message.reply_text(str(event))
        else:
            final_answer = event

    if final_answer:
        await _send_chunks(update, f"📝 **Kết quả:**\n\n{final_answer}")
    else:
        await update.message.reply_text("⚠️ Không có kết quả.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return

    lines = ["🖥️ **System Status**\n"]
    try:
        import ollama
        models   = ollama.list()
        names    = [m.model for m in models.models]
        lines.append(f"✅ Ollama: OK")
        lines.append(f"Models: {', '.join(names) or 'none'}")
    except Exception as e:
        lines.append(f"❌ Ollama: {e}")

    try:
        import psutil
        mem = psutil.virtual_memory()
        lines.append(f"RAM: {mem.percent:.1f}% used ({mem.available // 1024**3}GB free)")
        lines.append(f"CPU: {psutil.cpu_percent(interval=1):.1f}%")
    except ImportError:
        pass

    import platform
    lines.append(f"OS: {platform.system()} {platform.release()}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await update.message.reply_text("✅ Session đã được reset.")


async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await update.message.reply_text("⏳ Đang tạo morning briefing...")
    subprocess.Popen(
        ["python", "scripts/morning_briefing.py"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )


# ── App builder ────────────────────────────────────────────────────────────────

def build_app() -> Application:
    """Tạo Telegram Application với tất cả command handlers."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app   = Application.builder().token(token).build()
    app.add_handler(CommandHandler("ask",    cmd_ask))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("reset",  cmd_reset))
    app.add_handler(CommandHandler("brief",  cmd_brief))
    return app
