"""Ollama client wrapper — simple interface cho local LM."""

import ollama
from typing import Iterator


DEFAULT_MODEL = "llama3.2:3b"


def chat(prompt: str, model: str = DEFAULT_MODEL, system: str = "") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = ollama.chat(model=model, messages=messages)
    return response["message"]["content"]


def chat_stream(prompt: str, model: str = DEFAULT_MODEL, system: str = "") -> Iterator[str]:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for chunk in ollama.chat(model=model, messages=messages, stream=True):
        yield chunk["message"]["content"]


def list_models() -> list[str]:
    return [m["name"] for m in ollama.list()["models"]]


if __name__ == "__main__":
    from rich.console import Console
    console = Console()

    console.print("[bold green]Models có sẵn:[/bold green]")
    for m in list_models():
        console.print(f"  • {m}")

    console.print("\n[bold]Test chat:[/bold]")
    for chunk in chat_stream("Xin chào! Giới thiệu bản thân ngắn gọn."):
        console.print(chunk, end="", highlight=False)
    console.print()
