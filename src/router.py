"""
Smart Router — tự động chọn model phù hợp với câu hỏi.

Logic:
  - "auto" → phân tích prompt → chọn qwen hoặc deepseek
  - Tên model cụ thể → dùng thẳng, không qua router
"""

import re

MODEL_FAST      = "qwen2.5:14b"       # nhanh, chat hàng ngày
MODEL_REASONING = "deepseek-r1:32b"   # chậm, suy luận sâu

# num_ctx tối ưu cho từng model — cân bằng giữa context dài và VRAM
# Công thức: VRAM model + KV Cache (ctx * ~0.1MB/token) <= 24GB
MODEL_CTX: dict[str, int] = {
    "qwen2.5:14b":    32_768,   # 9GB model  + ~3GB KV  = ~12GB ✅
    "deepseek-r1:32b": 8_192,   # 19GB model + ~2GB KV  = ~21GB ✅
    "llama3.2:3b":    16_384,   # 2GB model  + ~1.5GB KV = ~4GB ✅
}
DEFAULT_CTX = 8_192   # fallback cho model không có trong danh sách


def get_ctx(model: str) -> int:
    """Trả về num_ctx phù hợp cho model."""
    return MODEL_CTX.get(model, DEFAULT_CTX)

# Từ khóa gợi ý cần suy luận sâu
_REASONING_KEYWORDS = [
    # Phân tích / lập luận
    "tại sao", "vì sao", "lý do", "nguyên nhân", "giải thích tại sao",
    "phân tích", "so sánh", "đánh giá", "chứng minh", "lập luận",
    "ưu nhược", "ưu điểm", "nhược điểm", "pros", "cons",
    # Toán / logic
    "tính", "tính toán", "bao nhiêu", "kết quả", "giải", "phương trình",
    "bước", "step by step", "từng bước",
    # Lập trình
    "code", "debug", "lỗi", "error", "thuật toán", "algorithm",
    "tối ưu", "optimize", "refactor", "thiết kế", "architecture",
    # Suy luận
    "nếu", "giả sử", "assume", "hypothesis", "dự đoán", "predict",
    "hệ quả", "consequence", "impact", "ảnh hưởng",
]

# Từ khóa gợi ý câu hỏi nhanh / chat thông thường
_FAST_KEYWORDS = [
    "dịch", "translate", "tóm tắt", "summary", "summarize",
    "viết", "write", "soạn", "draft",
    "xin chào", "hello", "hi ", "cảm ơn", "thanks",
    "là gì", "what is", "định nghĩa", "define",
    "liệt kê", "list", "cho tôi biết",
]


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def select_model(prompt: str, verbose: bool = False) -> str:
    """
    Phân tích prompt và trả về tên model phù hợp.

    verbose=True → in lý do chọn ra terminal (để debug / học)
    """
    reasoning_hits = _count_keyword_hits(prompt, _REASONING_KEYWORDS)
    fast_hits      = _count_keyword_hits(prompt, _FAST_KEYWORDS)
    prompt_len     = len(prompt)

    # Điểm số: càng cao → càng cần suy luận
    score = reasoning_hits * 2 - fast_hits

    # Prompt dài + nhiều vế → thêm điểm reasoning
    if prompt_len > 200:
        score += 1
    if prompt_len > 400:
        score += 1

    chosen = MODEL_REASONING if score >= 2 else MODEL_FAST

    if verbose:
        from rich.console import Console
        from rich import box
        from rich.table import Table
        c = Console()
        t = Table(box=box.SIMPLE, show_header=False)
        t.add_row("[dim]Reasoning hits[/dim]", str(reasoning_hits))
        t.add_row("[dim]Fast hits[/dim]",      str(fast_hits))
        t.add_row("[dim]Prompt length[/dim]",  str(prompt_len))
        t.add_row("[dim]Score[/dim]",          str(score))
        icon  = "🧠" if chosen == MODEL_REASONING else "⚡"
        color = "green" if chosen == MODEL_REASONING else "yellow"
        t.add_row("[dim]→ Model[/dim]", f"[{color}]{icon} {chosen}[/{color}]")
        c.print(t)

    return chosen
