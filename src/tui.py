"""
LoLM TUI — Textual interface.

Chạy:
    python -m src.tui
    python -m src.tui --session sessions/myproject.json
    python -m src.tui --model qwen2.5:14b

Phím tắt:
    F1         — help
    Ctrl+S     — lưu session
    Ctrl+R     — reset lịch sử
    Ctrl+Q     — thoát
"""

import os
import re
import typer
from rich.markup import escape

_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)

def _strip_think(text: str) -> str:
    return _THINK_RE.sub("", text)

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static
from textual import work
from textual.worker import get_current_worker

from src.client import ChatSession
from src.router import MODEL_REASONING, select_model
from src.rag import KnowledgeBase, list_kbs
from src.agent import Agent, ToolEvent

_FLOWER_FRAMES = [
    "·  ·  ·  ·  ·",
    "✿  ·  ·  ·  ·",
    "✿  ❀  ·  ·  ·",
    "✿  ❀  ❁  ·  ·",
    "✿  ❀  ❁  ✾  ·",
    "✿  ❀  ❁  ✾  ❋",
    "·  ❀  ❁  ✾  ❋",
    "·  ·  ❁  ✾  ❋",
    "·  ·  ·  ✾  ❋",
    "·  ·  ·  ·  ❋",
]

_cli = typer.Typer(add_completion=False)


class LoLMApp(App):
    TITLE = "LoLM Chat"
    BINDINGS = [
        ("f1",     "help",  "Help"),
        ("ctrl+s", "save",  "Lưu"),
        ("ctrl+r", "reset", "Reset"),
        ("ctrl+q", "quit",  "Thoát"),
    ]
    DEFAULT_CSS = """
    Screen { background: $background; }

    #log {
        height: 1fr;
        padding: 0 1;
    }

    #status {
        height: 1;
        padding: 0 1;
        color: $text-muted;
        display: none;
    }

    #stream {
        height: auto;
        padding: 0 1 1 1;
        background: $surface;
        display: none;
    }

    Input { dock: bottom; }
    """

    def __init__(
        self,
        session:      ChatSession,
        session_file: str | None,
        kb:           KnowledgeBase | None = None,
        agent:        Agent | None         = None,
    ) -> None:
        super().__init__()
        self.session      = session
        self.session_file = session_file
        self.kb           = kb
        self.agent        = agent        # None = chat thường, có = agent mode
        self._busy        = False
        self._flower_idx  = 0
        self._flower_timer = None

    # ── Layout ───────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(id="log", highlight=True, markup=True, wrap=True)
        yield Static("", id="status", markup=True)
        yield Static("", id="stream",  markup=True)
        yield Input(placeholder="Nhắn tin...  (F1 = help, Ctrl+Q = thoát)")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)
        model_label = f"[yellow]{self.session.model}[/yellow]"
        kb_label    = (f"  •  KB [green]{self.kb.name}[/green] "
                       f"[dim]({self.kb.count()} chunks)[/dim]") if self.kb else ""
        agent_label = "  •  [magenta]agent mode[/magenta]" if self.agent else ""
        log.write(f"[bold cyan]LoLM Chat[/bold cyan]  •  model {model_label}{kb_label}{agent_label}")
        if self.session_file and self.session.turn_count:
            log.write(f"[dim]📂 {self.session_file}  ({self.session.turn_count} turns)[/dim]")
        log.write("[dim]F1 help  •  Ctrl+S lưu  •  Ctrl+R reset  •  Ctrl+Q thoát[/dim]\n")
        self.query_one(Input).focus()

    # ── Input handler ─────────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        self.query_one(Input).clear()
        if not text or self._busy:
            return
        if text.startswith("/"):
            self._handle_command(text)
        else:
            log = self.query_one("#log", RichLog)
            log.write(f"[cyan bold]Bạn:[/cyan bold] {escape(text)}\n")
            if self.agent:
                self._do_agent(text)
            elif self.kb and self.kb.count() > 0:
                rag_prompt = self.kb.build_prompt(text)
                sources    = (
                    [c["source"] for c in self.kb.search(text)]
                    if rag_prompt != text else []
                )
                self._do_stream(rag_prompt, sources)
            else:
                self._do_stream(text, [])

    # ── Commands ──────────────────────────────────────────────────────────────

    def _handle_command(self, raw: str) -> None:
        cmd = raw.lower().split()[0]
        log = self.query_one("#log", RichLog)

        if cmd == "/help":
            self.action_help()
        elif cmd == "/model":
            log.write(
                f"[dim]Model [yellow]{self.session.model}[/yellow]  "
                f"Turns [cyan]{self.session.turn_count}[/cyan]  "
                f"Summary {'[green]có[/green]' if self.session._summary else 'chưa có'}[/dim]"
            )
        elif cmd == "/history":
            self._show_history()
        elif cmd == "/save":
            self.action_save()
        elif cmd == "/reset":
            self.action_reset()
        elif cmd == "/agent":
            if self.agent:
                self.agent = None
                log.write("[dim]Agent mode [red]tắt[/red] — dùng chat thường.[/dim]")
            else:
                self.agent = Agent(model=self.session.model, kb=self.kb)
                log.write("[dim]Agent mode [magenta]bật[/magenta] — LLM có thể dùng tools.[/dim]")
        elif cmd == "/index":
            arg = raw.split(maxsplit=1)[1] if len(raw.split()) > 1 else ""
            if not arg:
                log.write("[dim red]/index cần argument: file, URL, hoặc --repo path[/dim red]")
            else:
                self._do_index(arg)
        elif cmd == "/kb":
            parts = raw.split(maxsplit=2)
            sub   = parts[1].lower() if len(parts) > 1 else ""
            arg   = parts[2]         if len(parts) > 2 else ""

            if not sub:
                if self.kb:
                    log.write(f"[dim]KB [green]{self.kb.name}[/green]  {self.kb.count()} chunks[/dim]")
                else:
                    log.write("[dim]Chưa load KB — dùng /kb new <name> hoặc /kb switch <name>[/dim]")

            elif sub == "list":
                names = list_kbs()
                if not names:
                    log.write("[dim]Chưa có KB nào.[/dim]")
                else:
                    current = self.kb.name if self.kb else None
                    for n in names:
                        marker = " [green]←[/green]" if n == current else ""
                        log.write(f"  [dim]• {n}{marker}[/dim]")

            elif sub == "new":
                if not arg:
                    log.write("[dim red]/kb new cần tên: /kb new <name>[/dim red]")
                else:
                    self.kb = KnowledgeBase(arg)
                    if self.agent:
                        self.agent.kb = self.kb
                    log.write(f"[dim green]✓ Tạo KB [bold]{arg}[/bold] ({self.kb.count()} chunks)[/dim green]")

            elif sub == "switch":
                if not arg:
                    log.write("[dim red]/kb switch cần tên: /kb switch <name>[/dim red]")
                elif arg not in list_kbs():
                    log.write(f"[dim red]KB '{arg}' không tồn tại. Dùng /kb list để xem.[/dim red]")
                else:
                    self.kb = KnowledgeBase(arg)
                    if self.agent:
                        self.agent.kb = self.kb
                    log.write(f"[dim green]✓ Switched sang KB [bold]{arg}[/bold] ({self.kb.count()} chunks)[/dim green]")

            elif sub == "rename":
                if not self.kb:
                    log.write("[dim red]Chưa load KB nào.[/dim red]")
                elif not arg:
                    log.write("[dim red]/kb rename cần tên mới: /kb rename <name>[/dim red]")
                else:
                    old = self.kb.name
                    self.kb.rename(arg)
                    log.write(f"[dim green]✓ Đổi tên [bold]{old}[/bold] → [bold]{arg}[/bold][/dim green]")

            elif sub == "delete":
                if not self.kb:
                    log.write("[dim red]Chưa load KB nào.[/dim red]")
                else:
                    name = self.kb.name
                    self.kb.drop()
                    self.kb = None
                    if self.agent:
                        self.agent.kb = None
                    log.write(f"[dim green]✓ Đã xóa KB [bold]{name}[/bold][/dim green]")

            else:
                log.write(f"[dim red]Lệnh không hợp lệ. Dùng: /kb list | new | switch | rename | delete[/dim red]")
        elif cmd in ("/exit", "/quit", "/q"):
            self.action_quit()
        else:
            log.write(f"[dim red]Lệnh không hợp lệ: {escape(raw)}[/dim red]")

    def _show_history(self) -> None:
        log = self.query_one("#log", RichLog)
        if not self.session._history:
            log.write("[dim]Chưa có lịch sử.[/dim]")
            return
        for msg in self.session._history:
            if msg["role"] == "user":
                log.write(f"[cyan]┌ Bạn[/cyan]\n{escape(msg['content'])}\n")
            else:
                log.write(f"[green]┌ Model[/green]\n{escape(msg['content'])}\n")

    # ── Streaming ─────────────────────────────────────────────────────────────

    @work(thread=True)
    def _do_index(self, arg: str) -> None:
        """Index file / URL / repo vào KB (chạy trong thread)."""
        log = self.query_one("#log", RichLog)
        if self.kb is None:
            self.kb = KnowledgeBase()

        arg = arg.strip()
        try:
            if arg.startswith("--repo") or arg.startswith("-r"):
                path = arg.split(maxsplit=1)[1] if len(arg.split()) > 1 else "."
                self.call_from_thread(log.write, f"[dim]📁 Indexing repo: {path}...[/dim]")
                n = self.kb.add_repo(path)
            elif arg.startswith("http://") or arg.startswith("https://"):
                self.call_from_thread(log.write, f"[dim]🌐 Fetching: {arg}...[/dim]")
                n = self.kb.add_url(arg)
            else:
                self.call_from_thread(log.write, f"[dim]📄 Indexing: {arg}...[/dim]")
                n = self.kb.add_file(arg)
            self.call_from_thread(
                log.write,
                f"[dim green]✓ Đã index {n} chunks  •  KB tổng: {self.kb.count()} chunks[/dim green]",
            )
        except Exception as e:
            self.call_from_thread(log.write, f"[dim red]Lỗi index: {e}[/dim red]")

    @work(thread=True)
    def _do_agent(self, prompt: str) -> None:
        """Agent loop — gọi tools rồi hiện kết quả cuối."""
        self._busy = True
        label      = "[magenta]🤖 agent[/magenta]"

        self.call_from_thread(self._start_spinner, label)
        spinner_active = True
        final_text     = ""

        for item in self.agent.run(prompt):
            if isinstance(item, ToolEvent):
                status = f"🔧 [dim]{item.name}[/dim]  [dim cyan]{item.short_args()}[/dim cyan]"
                self.call_from_thread(self.query_one("#status", Static).update, status)
            else:
                # str = câu trả lời cuối
                if spinner_active:
                    self.call_from_thread(self._stop_spinner)
                    spinner_active = False
                final_text = _strip_think(item)
                self.call_from_thread(self._show_stream, label, final_text)

        if spinner_active:
            self.call_from_thread(self._stop_spinner)

        self.call_from_thread(self._finish_stream, label, final_text, [])

        if self.session_file:
            self.call_from_thread(self.session.save, self.session_file)

        self._busy = False

    @work(thread=True)
    def _do_stream(self, prompt: str, sources: list[str] | None = None) -> None:
        worker    = get_current_worker()
        self._busy = True

        resolved = select_model(prompt) if self.session.model == "auto" else self.session.model
        icon     = "🧠" if resolved == MODEL_REASONING else "⚡"
        color    = "green" if resolved == MODEL_REASONING else "yellow"
        label    = f"[{color}]{icon} {resolved}[/{color}]"

        # Spinner chạy trong lúc chờ + trong lúc model đang <think>
        self.call_from_thread(self._start_spinner, label)
        accumulated    = []
        spinner_active = True
        displayed_len  = 0  # số ký tự display đã hiện, tránh O(n²)

        for chunk in self.session.stream(prompt):
            if worker.is_cancelled:
                break
            accumulated.append(chunk)
            full = "".join(accumulated)

            in_think = "<think>" in full and "</think>" not in full
            if in_think:
                continue  # giữ spinner, chưa hiện gì

            if spinner_active:
                self.call_from_thread(self._stop_spinner)
                spinner_active = False

            display = _strip_think(full)
            if len(display) > displayed_len:
                self.call_from_thread(self._show_stream, label, display)
                displayed_len = len(display)

        if spinner_active:
            self.call_from_thread(self._stop_spinner)

        self.call_from_thread(
            self._finish_stream,
            label,
            _strip_think("".join(accumulated)),
            sources or [],
        )

        if self.session_file:
            self.call_from_thread(self.session.save, self.session_file)

        self._busy = False

    # ── Spinner helpers (called from main thread) ─────────────────────────────

    def _start_spinner(self, label: str) -> None:
        status = self.query_one("#status", Static)
        status.display = True
        self._flower_idx   = 0
        self._flower_timer = self.set_interval(
            0.18,
            lambda: self._tick_spinner(label),
        )

    def _tick_spinner(self, label: str) -> None:
        self._flower_idx = (self._flower_idx + 1) % len(_FLOWER_FRAMES)
        frame = _FLOWER_FRAMES[self._flower_idx]
        self.query_one("#status", Static).update(f"{label}  [cyan]{frame}[/cyan]")

    def _stop_spinner(self) -> None:
        if self._flower_timer:
            self._flower_timer.stop()
            self._flower_timer = None
        status = self.query_one("#status", Static)
        status.display = False
        status.update("")

    # ── Stream display helpers ────────────────────────────────────────────────

    def _show_stream(self, label: str, text: str) -> None:
        box = self.query_one("#stream", Static)
        box.display = True
        box.update(f"{label}\n{escape(text)}")

    def _finish_stream(self, label: str, text: str, sources: list[str]) -> None:
        self.query_one("#stream", Static).display = False
        self.query_one("#stream", Static).update("")
        log = self.query_one("#log", RichLog)
        log.write(f"{label}\n{escape(text)}")
        if sources:
            unique = list(dict.fromkeys(sources))  # dedup, giữ thứ tự
            log.write("[dim]📚 " + "  •  ".join(unique) + "[/dim]")
        log.write("")
        log.scroll_end()

    # ── Actions (key bindings) ────────────────────────────────────────────────

    def action_help(self) -> None:
        self.query_one("#log", RichLog).write(
            "[dim]Lệnh chat: /help /model /history /save /reset /exit\n"
            "       /agent  — bật/tắt agent mode\n"
            "       /index <file|URL|--repo path>  — thêm tài liệu vào KB\n"
            "KB:    /kb              — xem KB hiện tại\n"
            "       /kb list         — liệt kê tất cả KB\n"
            "       /kb new <name>   — tạo và switch sang KB mới\n"
            "       /kb switch <name>— switch sang KB đã có\n"
            "       /kb rename <name>— đổi tên KB hiện tại\n"
            "       /kb delete       — xóa KB hiện tại\n"
            "Phím:  F1=help  Ctrl+S=lưu  Ctrl+R=reset  Ctrl+Q=thoát[/dim]"
        )

    def action_save(self) -> None:
        log = self.query_one("#log", RichLog)
        if self.session_file:
            self.session.save(self.session_file)
            log.write(f"[dim green]✓ Đã lưu: {self.session_file}[/dim green]")
        else:
            log.write("[dim]Chưa có session file — dùng --session khi khởi động.[/dim]")

    def action_reset(self) -> None:
        self.session.reset()
        if self.agent:
            self.agent.reset()
        self.query_one("#log", RichLog).write("[dim]✓ Đã xóa lịch sử.[/dim]")

    def action_quit(self) -> None:
        if self.session_file:
            self.session.save(self.session_file)
        self.exit()


# ── CLI entry point ───────────────────────────────────────────────────────────

@_cli.command()
def main(
    session_file: str | None = typer.Option(None,   "--session", "-s", help="File JSON session"),
    model:        str        = typer.Option("auto", "--model",   "-m", help="Model hoặc 'auto'"),
    max_turns:    int        = typer.Option(20,     "--max-turns",     help="Số turns tối đa"),
    verbose:      bool       = typer.Option(False,  "--verbose", "-v", help="Log lý do chọn model"),
    kb_name:      str | None = typer.Option(None,   "--kb",      "-k", help="Tên knowledge base"),
    agent_mode:   bool       = typer.Option(False,  "--agent",   "-a", help="Bật agent mode ngay khi khởi động"),
) -> None:
    if session_file and os.path.exists(session_file):
        session = ChatSession.load(session_file, verbose=verbose)
    else:
        session = ChatSession(model=model, max_turns=max_turns, verbose=verbose)

    kb    = KnowledgeBase(kb_name) if kb_name else None
    agent = Agent(model=model, kb=kb) if agent_mode else None
    LoLMApp(session, session_file, kb=kb, agent=agent).run()


if __name__ == "__main__":
    _cli()
