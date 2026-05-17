"""
Phase 2 — Benchmark so sánh models
Đo tốc độ + chất lượng của qwen2.5:14b và deepseek-r1:32b
"""

import httpx
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

MODELS = ["qwen2.5:14b", "deepseek-r1:32b"]

# Bài test: cùng câu hỏi, hỏi cả 2 model
TEST_PROMPTS = [
    {
        "name": "Tốc độ thuần (đếm số)",
        "prompt": "Count from 1 to 30, one number per line.",
    },
    {
        "name": "Tiếng Việt",
        "prompt": "Giải thích máy tính hoạt động như thế nào, dùng ngôn ngữ đơn giản cho người mới bắt đầu. Trả lời trong 5 câu.",
    },
    {
        "name": "Lập luận",
        "prompt": "I have 3 boxes. Box A is heavier than Box B. Box C is lighter than Box B. Which box is the heaviest? Explain step by step.",
    },
]


def benchmark_model(model: str, prompt: str) -> dict:
    """Gửi prompt, đo tốc độ và lấy kết quả."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    try:
        start = time.time()
        r = httpx.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=120,
        )
        elapsed = time.time() - start
        data = r.json()

        eval_count    = data.get("eval_count", 0)
        eval_duration = data.get("eval_duration", 1) / 1e9   # ns → s
        load_duration = data.get("load_duration", 0) / 1e9
        tps           = eval_count / eval_duration if eval_duration > 0 else 0
        response_text = data.get("response", "").strip()

        return {
            "ok": True,
            "tps": tps,
            "tokens": eval_count,
            "load_s": load_duration,
            "total_s": elapsed,
            "response": response_text,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_benchmark():
    console.print(Panel.fit(
        "[bold cyan]LoLM — Phase 2 Benchmark[/bold cyan]\n"
        "So sánh: [yellow]qwen2.5:14b[/yellow] vs [green]deepseek-r1:32b[/green]",
        box=box.DOUBLE
    ))

    results = {m: [] for m in MODELS}

    for i, test in enumerate(TEST_PROMPTS, 1):
        console.print(f"\n[bold]Test {i}/{len(TEST_PROMPTS)}: {test['name']}[/bold]")
        console.print(f"[dim]Prompt: {test['prompt'][:80]}...[/dim]" if len(test['prompt']) > 80 else f"[dim]Prompt: {test['prompt']}[/dim]")

        for model in MODELS:
            console.print(f"  ⏳ Đang chạy [yellow]{model}[/yellow]...", end="")
            res = benchmark_model(model, test["prompt"])
            results[model].append(res)

            if res["ok"]:
                console.print(f"\r  ✅ [yellow]{model}[/yellow] — "
                               f"[cyan]{res['tps']:.1f} t/s[/cyan] | "
                               f"{res['tokens']} tokens | "
                               f"load {res['load_s']:.1f}s | "
                               f"total {res['total_s']:.1f}s")
            else:
                console.print(f"\r  ❌ [yellow]{model}[/yellow] — Lỗi: {res['error']}")

    # ── Bảng tóm tắt tốc độ ──────────────────────────────────────────────────
    console.print("\n")
    speed_table = Table(title="Tốc độ (tokens/sec)", box=box.ROUNDED, show_lines=True)
    speed_table.add_column("Test", style="white")
    for m in MODELS:
        speed_table.add_column(m, justify="center", style="cyan")

    for i, test in enumerate(TEST_PROMPTS):
        row = [test["name"]]
        for m in MODELS:
            r = results[m][i]
            row.append(f"{r['tps']:.1f}" if r["ok"] else "ERR")
        speed_table.add_row(*row)

    # Dòng trung bình
    avg_row = ["[bold]Trung bình[/bold]"]
    for m in MODELS:
        valid = [r["tps"] for r in results[m] if r["ok"]]
        avg = sum(valid) / len(valid) if valid else 0
        avg_row.append(f"[bold]{avg:.1f}[/bold]")
    speed_table.add_row(*avg_row)
    console.print(speed_table)

    # ── In câu trả lời tiếng Việt để so sánh chất lượng ─────────────────────
    console.print("\n[bold]So sánh câu trả lời tiếng Việt:[/bold]")
    vi_idx = 1  # index của test "Tiếng Việt"
    for m in MODELS:
        r = results[m][vi_idx]
        if r["ok"]:
            console.print(Panel(
                r["response"],
                title=f"[yellow]{m}[/yellow]",
                border_style="yellow" if "qwen" in m else "green",
            ))

    # ── Gợi ý model chính ────────────────────────────────────────────────────
    console.print("\n[bold]Gợi ý:[/bold]")
    qwen_ok  = [r["tps"] for r in results["qwen2.5:14b"]      if r["ok"]]
    deep_ok  = [r["tps"] for r in results["deepseek-r1:32b"]  if r["ok"]]
    qwen_avg = sum(qwen_ok) / len(qwen_ok) if qwen_ok else 0
    deep_avg = sum(deep_ok) / len(deep_ok) if deep_ok else 0

    console.print(f"  • [yellow]qwen2.5:14b[/yellow]     → tốc độ trung bình [cyan]{qwen_avg:.1f} t/s[/cyan] | nhẹ hơn, tốt tiếng Việt")
    console.print(f"  • [green]deepseek-r1:32b[/green] → tốc độ trung bình [cyan]{deep_avg:.1f} t/s[/cyan] | mạnh hơn, lý luận tốt hơn")

    if deep_avg >= 20:
        console.print("\n  ✅ [green]deepseek-r1:32b[/green] chạy ổn trên máy bạn — nên dùng làm model chính.")
    else:
        console.print("\n  ✅ [yellow]qwen2.5:14b[/yellow] nhanh hơn đáng kể — cân nhắc dùng làm model chính.")


if __name__ == "__main__":
    run_benchmark()
