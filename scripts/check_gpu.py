"""Kiểm tra Ollama server và GPU status."""

import subprocess
import sys
import httpx
import json


def check_ollama_running() -> bool:
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def get_models() -> list:
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=5)
        return r.json().get("models", [])
    except Exception:
        return []


def run_benchmark(model: str = "llama3.2:3b") -> None:
    print(f"\nBenchmark model: {model}")
    payload = {
        "model": model,
        "prompt": "Count from 1 to 20.",
        "stream": False
    }
    r = httpx.post("http://localhost:11434/api/generate", json=payload, timeout=120)
    data = r.json()
    eval_count = data.get("eval_count", 0)
    eval_duration = data.get("eval_duration", 1) / 1e9  # ns -> s
    tps = eval_count / eval_duration if eval_duration > 0 else 0
    print(f"  Tokens generated: {eval_count}")
    print(f"  Time: {eval_duration:.2f}s")
    print(f"  Speed: {tps:.1f} tokens/sec")
    if tps > 30:
        print("  [OK] GPU đang được dùng")
    elif tps > 5:
        print("  [WARN] Tốc độ thấp — có thể đang dùng CPU")
    else:
        print("  [ERROR] Rất chậm — kiểm tra lại cấu hình")


if __name__ == "__main__":
    print("=== LoLM GPU Check ===\n")

    if check_ollama_running():
        print("[OK] Ollama server đang chạy tại localhost:11434")
    else:
        print("[ERROR] Ollama không chạy. Hãy khởi động Ollama trước.")
        sys.exit(1)

    models = get_models()
    if models:
        print(f"\nModels có sẵn ({len(models)}):")
        for m in models:
            size_gb = m.get("size", 0) / 1e9
            print(f"  • {m['name']} ({size_gb:.1f} GB)")
        run_benchmark(models[0]["name"])
    else:
        print("\nChưa có model nào. Chạy: ollama pull llama3.2:3b")
