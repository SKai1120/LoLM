"""
Ollama client wrapper — interface chính cho Local LM.

Dùng model="auto" để router tự chọn model phù hợp.
Dùng model="qwen2.5:14b" hoặc "deepseek-r1:32b" để ép thủ công.
"""

import ollama
from typing import Iterator
from src.router import select_model, MODEL_FAST

DEFAULT_MODEL = "auto"

# System prompt mặc định — fix lỗi model trộn tiếng Trung
DEFAULT_SYSTEM = (
    "You are a helpful assistant. "
    "Always respond in the same language the user uses. "
    "If the user writes in Vietnamese, respond entirely in Vietnamese."
)


def _resolve_model(model: str, prompt: str, verbose: bool = False) -> str:
    """Trả về tên model thực tế — nếu 'auto' thì qua router."""
    if model == "auto":
        return select_model(prompt, verbose=verbose)
    return model


def chat(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: str = DEFAULT_SYSTEM,
    verbose: bool = False,
) -> str:
    """Gửi một câu hỏi, nhận câu trả lời đầy đủ."""
    resolved = _resolve_model(model, prompt, verbose)
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt},
    ]
    response = ollama.chat(model=resolved, messages=messages)
    return response["message"]["content"]


def chat_stream(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: str = DEFAULT_SYSTEM,
    verbose: bool = False,
) -> Iterator[str]:
    """Gửi câu hỏi, nhận câu trả lời dạng stream (từng mảnh nhỏ)."""
    resolved = _resolve_model(model, prompt, verbose)
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt},
    ]
    for chunk in ollama.chat(model=resolved, messages=messages, stream=True):
        yield chunk["message"]["content"]


def list_models() -> list[str]:
    """Liệt kê tất cả model đang có trên máy."""
    return [m.model for m in ollama.list().models]


# ── Demo chạy trực tiếp ───────────────────────────────────────────────────────
if __name__ == "__main__":
    from rich.console import Console
    console = Console()

    console.print("[bold cyan]LoLM Client — Demo[/bold cyan]\n")

    console.print("[bold]Models có sẵn:[/bold]")
    for m in list_models():
        console.print(f"  • {m}")

    tests = [
        "Xin chào! Hôm nay thời tiết thế nào?",
        "Tại sao bầu trời màu xanh? Giải thích từng bước.",
    ]

    for prompt in tests:
        console.print(f"\n[dim]───────────────────────────────[/dim]")
        console.print(f"[bold]Câu hỏi:[/bold] {prompt}")
        console.print("[bold]Router chọn:[/bold]")

        # verbose=True để thấy lý do chọn model
        resolved = _resolve_model("auto", prompt, verbose=True)

        console.print("[bold]Trả lời:[/bold] ", end="")
        for chunk in chat_stream(prompt, model=resolved):
            console.print(chunk, end="", highlight=False)
        console.print()
