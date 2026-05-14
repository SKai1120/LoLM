# LoLM — CLAUDE.md

## Dự án
Local Language Model stack — Ollama + Python, AMD 7900XTX 24GB, Windows 11.

## Quy ước
- Ngôn ngữ code: Python 3.10+
- Mọi thay đổi quan trọng phải ghi vào `devlog.md`
- Format devlog entry: `### [YYYY-MM-DD] Tiêu đề`
- Test chạy trên GPU AMD (ROCm/HIP) — không dùng CUDA

## Cấu trúc
- `src/` — Python source code
- `scripts/` — Tiện ích, benchmark, setup
- `docs/` — Tài liệu kỹ thuật
- `notebooks/` — Jupyter experiments
- `models/` — Model configs & metadata

## Ollama API
- Server: `http://localhost:11434`
- Default model biến: `DEFAULT_MODEL` trong `src/client.py`
