"""
LoLM Interactive Chat — terminal chat app.

Chạy:
    python -m src.chat
    python -m src.chat --session sessions/myproject.json
    python -m src.chat --model qwen2.5:14b
    python -m src.chat --no-router    (tắt auto-select, dùng model chính)

Lệnh trong chat:
    /help       — xem danh sách lệnh
    /model      — xem model đang dùng + thông tin session
    /history    — xem lại toàn bộ lịch sử
    /save       — lưu session thủ công
    /reset      — xóa lịch sử, bắt đầu lại
    /exit       — thoát (tự động lưu nếu có session file)
"""

import sys
import os
import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from rich import box

from src.client import ChatSession, DEFAULT_MODEL, DEFAULT_SYSTEM
from src.router import MODEL_FAST, MODEL_REASONING, select_model

app     = typer.Typer(add_completion=False)
console = Console()


def _header(session: ChatSession, session_file: str | None) -> None:
    """In header khi khởi động."""
    file_info = f"[dim]{session_file}[/dim]" if session_file else "[dim]không lưu[/dim]"
    console.print(Panel.fit(
        f"[bold cyan]LoLM Chat[/bold cyan]  •  model [yellow]auto[/yellow]  •  file {file_info}\n"
        f"[dim]Gõ [bold]/help[/bold] để xem lệnh  •  Ctrl+C hoặc [bold]/exit[/bold] để thoát[/dim]",
        box=box.ROUNDED,
        border_style="cyan",
    ))


def _show_help() -> None:
    console.print(Panel(
        "/help     — danh sách lệnh này\n"
        "/model    — model đang dùng + số turns + có summary không\n"
        "/history  — xem lại lịch sử trò chuyện\n"
        "/save     — lưu session thủ công\n"
        "/reset    — xóa lịch sử, giữ summary\n"
        "/exit     — thoát (tự động lưu)",
        title="[bold]Lệnh[/bold]",
        border_style="dim",
    ))


def _show_model_info(session: ChatSession) -> None:
    console.print(
        f"  Model chính : [yellow]{session.model}[/yellow]\n"
        f"  Số turns    : [cyan]{session.turn_count}[/cyan]\n"
        f"  Summary     : {'[green]có[/green]' if session._summary else '[dim]chưa có[/dim]'}\n"
        f"  max_turns   : [dim]{session.max_turns}[/dim]"
    )

def _stream_reply(session: ChatSession, prompt: str) -> str:
    """Stream câu trả lời ra terminal, trả về tên model đã dùng."""
    # Xác định model trước để hiển thị
    resolved = select_model(prompt) if session.model == "auto" else session.model
    icon     = "🧠" if resolved == MODEL_REASONING else "⚡"
    color    = "green" if resolved == MODEL_REASONING else "yellow"

    console.print(f"\n[{color}]{icon} {resolved}[/{color}]", end="  ")

    full = []
    try:
        for chunk in session.stream(prompt):
            console.print(chunk, end="", highlight=False)
            full.append(chunk)
    except KeyboardInterrupt:
        console.print("\n[dim](dừng stream)[/dim]")

    console.print("\n")
    return resolved


@app.command()
def main(
    session_file: str  = typer.Option(None,    "--session", "-s", help="File JSON để lưu/load session"),
    model:        str  = typer.Option("auto",  "--model",   "-m", help="Model cụ thể hoặc 'auto'"),
    max_turns:    int  = typer.Option(20,       "--max-turns",     help="Số turns tối đa trước khi nén"),
    verbose:      bool = typer.Option(False,    "--verbose", "-v", help="Hiện lý do chọn model"),
) -> None:

    # ── Load hoặc tạo session ─────────────────────────────────────────────────
    if session_file and os.path.exists(session_file):
        session = ChatSession.load(session_file, verbose=verbose)
        console.print(f"[dim green]📂 Tiếp tục session: {session_file} ({session.turn_count} turns)[/dim green]")
    else:
        session = ChatSession(model=model, max_turns=max_turns, verbose=verbose)

    _header(session, session_file)

    # ── Chat loop ─────────────────────────────────────────────────────────────
    while True:
        try:
            user_input = console.input("[cyan bold]Bạn:[/cyan bold] ").strip()
        except (KeyboardInterrupt, EOFError):
            user_input = "/exit"

        if not user_input:
            continue

        # ── Xử lý lệnh ───────────────────────────────────────────────────────
        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]

            if cmd == "/help":
                _show_help()

            elif cmd == "/model":
                _show_model_info(session)

            elif cmd == "/history":
                if session.turn_count == 0:
                    console.print("[dim]Chưa có lịch sử.[/dim]")
                else:
                    session.print_history()

            elif cmd == "/save":
                if session_file:
                    session.save(session_file)
                else:
                    name = console.input("Tên file (vd: sessions/myproject.json): ").strip()
                    if name:
                        session.save(name)
                        session_file = name

            elif cmd == "/reset":
                session.reset()
                console.print("[dim]Đã xóa lịch sử.[/dim]")

            elif cmd in ("/exit", "/quit", "/q"):
                if session_file:
                    session.save(session_file)
                console.print("[dim]Tạm biệt![/dim]")
                raise typer.Exit()

            else:
                console.print(f"[dim red]Lệnh không hợp lệ: {user_input}. Gõ /help để xem lệnh.[/dim red]")

            continue

        # ── Gửi câu hỏi đến model ────────────────────────────────────────────
        _stream_reply(session, user_input)

        # Auto-save sau mỗi turn nếu có session file
        if session_file:
            session.save(session_file)


if __name__ == "__main__":
    app()
