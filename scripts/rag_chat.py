"""
RAG Chat — CLI đơn giản để test pipeline.

Dùng:
    python scripts/rag_chat.py --file docs/guide.md
    python scripts/rag_chat.py --url https://example.com
    python scripts/rag_chat.py --repo H:/Project/MyRepo
    python scripts/rag_chat.py --kb my_project   # dùng lại KB đã index

Có thể kết hợp nhiều nguồn:
    python scripts/rag_chat.py --file a.md --file b.pdf --url https://x.com
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import typer
from rich.console import Console
from rich.panel import Panel
from rich import box

from src.rag import KnowledgeBase
from src.client import ChatSession

app     = typer.Typer(add_completion=False)
console = Console()


@app.command()
def main(
    files:  list[str] = typer.Option([], "--file", "-f",  help="File để index"),
    urls:   list[str] = typer.Option([], "--url",  "-u",  help="URL để fetch & index"),
    repos:  list[str] = typer.Option([], "--repo", "-r",  help="Repo/thư mục để index"),
    kb_name: str      = typer.Option("default", "--kb",   help="Tên knowledge base"),
    model:   str      = typer.Option("auto",    "--model",help="LLM model"),
    top_k:   int      = typer.Option(5,         "--k",    help="Số chunk retrieve"),
    clear:   bool     = typer.Option(False, "--clear",    help="Xóa KB trước khi index"),
) -> None:

    # ── Khởi tạo KB ──────────────────────────────────────────────────────────
    kb = KnowledgeBase(name=kb_name)

    if clear:
        kb.clear()
        console.print("[dim]✓ Đã xóa KB cũ.[/dim]")

    # ── Index tài liệu mới ────────────────────────────────────────────────────
    total_new = 0

    for f in files:
        console.print(f"[dim]📄 Indexing file: {f}[/dim]", end=" ")
        n = kb.add_file(f)
        console.print(f"[dim green]{n} chunks[/dim green]")
        total_new += n

    for url in urls:
        console.print(f"[dim]🌐 Fetching: {url}[/dim]", end=" ")
        n = kb.add_url(url)
        console.print(f"[dim green]{n} chunks[/dim green]")
        total_new += n

    for repo in repos:
        console.print(f"[dim]📁 Indexing repo: {repo}[/dim]", end=" ")
        n = kb.add_repo(repo)
        console.print(f"[dim green]{n} chunks[/dim green]")
        total_new += n

    console.print(Panel.fit(
        f"[bold cyan]RAG Chat[/bold cyan]  •  KB [yellow]{kb_name}[/yellow]  •  "
        f"[cyan]{kb.count()}[/cyan] chunks  •  model [yellow]{model}[/yellow]\n"
        f"[dim]Gõ /sources để xem nguồn  •  /exit để thoát[/dim]",
        box=box.ROUNDED, border_style="cyan",
    ))

    if kb.count() == 0:
        console.print("[yellow]⚠ KB trống — hãy thêm --file / --url / --repo[/yellow]")

    # ── Chat loop ─────────────────────────────────────────────────────────────
    session    = ChatSession(model=model)
    last_query = ""

    while True:
        try:
            user_input = console.input("[cyan bold]Bạn:[/cyan bold] ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue

        if user_input.lower() in ("/exit", "/quit", "/q"):
            break

        if user_input.lower() == "/sources":
            if not last_query:
                console.print("[dim]Chưa có câu hỏi nào.[/dim]")
            else:
                chunks = kb.search(last_query, k=top_k)
                for c in chunks:
                    console.print(f"  [dim]{c['source']}  score={c['score']}[/dim]")
            continue

        last_query = user_input

        # Retrieve + augment prompt
        rag_prompt = kb.build_prompt(user_input, k=top_k)
        if rag_prompt != user_input:
            console.print(f"[dim]↳ Tìm thấy context, augmenting prompt...[/dim]")

        # Stream reply
        console.print()
        for chunk in session.stream(rag_prompt):
            console.print(chunk, end="", highlight=False)
        console.print("\n")

    console.print("[dim]Tạm biệt![/dim]")


if __name__ == "__main__":
    app()
