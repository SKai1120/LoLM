"""
LoLM Agent — LLM với tool calling.

Thay vì RAG tĩnh (index trước, retrieve sau), Agent tự quyết định
khi nào cần đọc file / fetch URL / tìm KB và gọi tool tương ứng.

Dùng:
    from src.agent import Agent
    agent = Agent(kb=my_kb)
    for item in agent.run("đọc file config.py và giải thích"):
        print(item)  # ToolEvent hoặc str
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import ollama

from src.router import select_model, get_ctx
from src.rag import KnowledgeBase, _fetch_url

MAX_TOOL_ROUNDS = 8

AGENT_SYSTEM = (
    "Bạn là một AI assistant có thể dùng tools để đọc file, fetch web, tìm tài liệu, xem git log. "
    "Khi cần thông tin cụ thể từ file hoặc web, hãy dùng tool thay vì đoán. "
    "Sau khi có đủ thông tin, trả lời trực tiếp và đầy đủ bằng tiếng Việt. "
    "Không dùng tiếng Trung hoặc ngôn ngữ khác."
)

_TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Đọc nội dung một file (text, code, markdown, ...)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Đường dẫn file"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "Liệt kê files/thư mục trong một đường dẫn",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Đường dẫn thư mục (mặc định '.')"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch và đọc nội dung một trang web",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL cần fetch"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_kb",
            "description": "Tìm kiếm trong knowledge base đã index",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Câu truy vấn tìm kiếm"},
                    "k":     {"type": "integer", "description": "Số kết quả (mặc định 5)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "Xem git commit history của một repo",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Đường dẫn repo (mặc định '.')"},
                    "n":    {"type": "integer", "description": "Số commits (mặc định 10)"},
                },
                "required": [],
            },
        },
    },
]


# ── Tool Event ────────────────────────────────────────────────────────────────

@dataclass
class ToolEvent:
    """Phát ra khi agent thực thi một tool — dùng để hiện status trong UI."""
    name:   str
    args:   dict
    result: str

    def short_args(self) -> str:
        """Tóm tắt args để hiện trong UI."""
        if "path" in self.args:
            return self.args["path"]
        if "url" in self.args:
            return self.args["url"]
        if "query" in self.args:
            return f'"{self.args["query"]}"'
        return str(self.args)


# ── Tool executor ─────────────────────────────────────────────────────────────

def _execute(name: str, args: dict, kb: KnowledgeBase | None) -> str:
    if name == "read_file":
        p = Path(args.get("path", ""))
        if not p.exists():
            return f"File không tồn tại: {p}"
        text = p.read_text(encoding="utf-8", errors="ignore")
        if len(text) > 10_000:
            return text[:10_000] + "\n[TRUNCATED]"
        return text

    if name == "list_dir":
        p = Path(args.get("path", "."))
        if not p.exists():
            return f"Thư mục không tồn tại: {p}"
        lines = []
        for item in sorted(p.iterdir()):
            lines.append(("📁 " if item.is_dir() else "📄 ") + item.name)
        return "\n".join(lines) or "(trống)"

    if name == "fetch_url":
        try:
            text = _fetch_url(args["url"])
            if len(text) > 8_000:
                return text[:8_000] + "\n[TRUNCATED]"
            return text
        except Exception as e:
            return f"Lỗi fetch: {e}"

    if name == "search_kb":
        if kb is None:
            return "Knowledge base chưa được load. Dùng --kb khi khởi động."
        results = kb.search(args["query"], k=args.get("k", 5))
        if not results:
            return "Không tìm thấy kết quả liên quan."
        return "\n\n".join(
            f"[{r['source']}] score={r['score']}\n{r['text']}"
            for r in results
        )

    if name == "git_log":
        path = args.get("path", ".")
        n    = args.get("n", 10)
        try:
            res = subprocess.run(
                ["git", "-C", path, "log", f"-{n}", "--oneline", "--decorate"],
                capture_output=True, text=True, timeout=10,
            )
            return res.stdout.strip() or res.stderr.strip() or "(không có commit)"
        except Exception as e:
            return f"Lỗi git: {e}"

    return f"Tool không xác định: {name}"


# ── Agent ─────────────────────────────────────────────────────────────────────

class Agent:
    """
    Agent với tool calling.

    `run(prompt)` là generator — yields ToolEvent (status) rồi str (kết quả cuối).
    Caller xử lý từng loại khác nhau (UI hiện status vs text).
    """

    def __init__(
        self,
        model:   str                = "auto",
        kb:      KnowledgeBase | None = None,
        verbose: bool               = False,
    ) -> None:
        self.model   = model
        self.kb      = kb
        self.verbose = verbose
        self._history: list[dict] = [{"role": "system", "content": AGENT_SYSTEM}]

    @property
    def turn_count(self) -> int:
        return sum(1 for m in self._history if m["role"] == "user")

    def reset(self) -> None:
        self._history = [self._history[0]]

    def run(self, prompt: str) -> Iterator[ToolEvent | str]:
        """
        Chạy agent loop.
        Yields:
            ToolEvent — mỗi khi một tool được gọi (dùng để hiện status)
            str       — text câu trả lời cuối (toàn bộ, không phải streaming)
        """
        self._history.append({"role": "user", "content": prompt})
        resolved = select_model(prompt) if self.model == "auto" else self.model

        for _ in range(MAX_TOOL_ROUNDS):
            response = ollama.chat(
                model=resolved,
                messages=self._history,
                tools=_TOOL_DEFS,
                options={"num_ctx": get_ctx(resolved)},
            )
            msg = response["message"]

            # Lấy tool_calls — SDK có thể trả về object hoặc dict
            raw_calls = msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)

            if not raw_calls:
                # Không còn tool call → đây là câu trả lời cuối
                content = msg.get("content", "") if isinstance(msg, dict) else (msg.content or "")
                self._history.append({"role": "assistant", "content": content})
                yield content
                return

            # Lưu assistant message có tool_calls
            self._history.append(
                msg if isinstance(msg, dict)
                else {"role": "assistant", "content": msg.content or "", "tool_calls": raw_calls}
            )

            # Thực thi từng tool
            for tc in raw_calls:
                if isinstance(tc, dict):
                    name = tc["function"]["name"]
                    args = tc["function"]["arguments"]
                else:
                    name = tc.function.name
                    args = tc.function.arguments
                    if isinstance(args, str):
                        args = json.loads(args)

                result = _execute(name, args, self.kb)
                yield ToolEvent(name=name, args=args, result=result)

                self._history.append({"role": "tool", "content": result})

        yield "(Đã đạt giới hạn vòng lặp tool — thử câu hỏi ngắn hơn)"
