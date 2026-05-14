"""
Ollama client wrapper — interface chính cho Local LM.

Dùng model="auto" để router tự chọn model phù hợp.
Dùng model="qwen2.5:14b" hoặc "deepseek-r1:32b" để ép thủ công.

Ví dụ dùng multi-turn:
    session = ChatSession()
    session.send("Tên tôi là K")
    session.send("Bạn còn nhớ tên tôi không?")  # model nhớ "K"
"""

import ollama
from typing import Iterator
from src.router import select_model, MODEL_FAST, get_ctx

DEFAULT_MODEL = "auto"

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


# ── Single-turn (câu hỏi độc lập, không nhớ lịch sử) ─────────────────────────

def chat(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: str = DEFAULT_SYSTEM,
    verbose: bool = False,
) -> str:
    """Gửi một câu hỏi, nhận câu trả lời đầy đủ. Không nhớ lịch sử."""
    resolved = _resolve_model(model, prompt, verbose)
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt},
    ]
    response = ollama.chat(
        model=resolved,
        messages=messages,
        options={"num_ctx": get_ctx(resolved)},
    )
    return response["message"]["content"]


def chat_stream(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: str = DEFAULT_SYSTEM,
    verbose: bool = False,
) -> Iterator[str]:
    """Gửi câu hỏi, stream từng mảnh trả lời. Không nhớ lịch sử."""
    resolved = _resolve_model(model, prompt, verbose)
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt},
    ]
    for chunk in ollama.chat(
        model=resolved,
        messages=messages,
        stream=True,
        options={"num_ctx": get_ctx(resolved)},
    ):
        yield chunk["message"]["content"]


# ── Multi-turn (nhớ lịch sử trong session) ────────────────────────────────────

class ChatSession:
    """
    Cuộc trò chuyện có nhớ lịch sử — 3 lớp bảo vệ context overflow:

    1. num_ctx đúng theo model     → Ollama đọc được đủ context
    2. Sliding window (max_turns)  → chỉ giữ N turn gần nhất
    3. Summary memory              → tóm tắt phần cũ trước khi bỏ,
                                     model vẫn "biết" quá khứ qua bản tóm tắt

    Thứ tự kích hoạt:
      turn <= max_turns          → dùng full history
      turn >  max_turns          → tóm tắt phần cũ + giữ window gần nhất
    """

    # Prompt dùng để tóm tắt — ngắn gọn, không cần reasoning
    _SUMMARY_PROMPT = (
        "Summarize the conversation below into 3-5 concise bullet points. "
        "Keep names, facts, and decisions. Reply ONLY with the summary, no extra text.\n\n"
        "{history}"
    )

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        system: str = DEFAULT_SYSTEM,
        max_turns: int = 20,      # giữ tối đa 20 cặp hỏi-đáp trước khi tóm tắt
        verbose: bool = False,
    ):
        self.model     = model
        self.system    = system
        self.max_turns = max_turns
        self.verbose   = verbose
        self._history: list[dict] = []   # chỉ lưu user + assistant, không có system
        self._summary: str = ""          # tóm tắt tích lũy của phần lịch sử cũ

    # ── Gửi và nhận đầy đủ ───────────────────────────────────────────────────

    def send(self, prompt: str) -> str:
        """Gửi tin nhắn, nhận câu trả lời đầy đủ."""
        resolved = _resolve_model(self.model, prompt, self.verbose)
        messages = self._build_messages(prompt)

        response = ollama.chat(
            model=resolved,
            messages=messages,
            options={"num_ctx": get_ctx(resolved)},
        )
        reply = response["message"]["content"]
        self._append(prompt, reply)
        return reply

    # ── Gửi và nhận dạng stream ──────────────────────────────────────────────

    def stream(self, prompt: str) -> Iterator[str]:
        """Gửi tin nhắn, stream từng mảnh trả lời."""
        resolved = _resolve_model(self.model, prompt, self.verbose)
        messages = self._build_messages(prompt)

        full_reply = []
        for chunk in ollama.chat(
            model=resolved,
            messages=messages,
            stream=True,
            options={"num_ctx": get_ctx(resolved)},
        ):
            piece = chunk["message"]["content"]
            full_reply.append(piece)
            yield piece

        # Lưu vào lịch sử sau khi stream xong
        self._append(prompt, "".join(full_reply))

    # ── Tiện ích ─────────────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        """
        Lưu session xuống file JSON.
        Bao gồm: model, system prompt, summary, toàn bộ history.

        Ví dụ:
            session.save("sessions/project_a.json")
        """
        import json, os
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        data = {
            "model":      self.model,
            "system":     self.system,
            "max_turns":  self.max_turns,
            "summary":    self._summary,
            "history":    self._history,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if self.verbose:
            from rich.console import Console
            Console().print(f"[dim green]💾 Session saved → {path}[/dim green]")

    @classmethod
    def load(cls, path: str, verbose: bool = False) -> "ChatSession":
        """
        Tải session từ file JSON và trả về ChatSession sẵn dùng.

        Ví dụ:
            session = ChatSession.load("sessions/project_a.json")
            session.send("Tiếp tục từ hôm qua nhé...")
        """
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        session = cls(
            model     = data.get("model",     DEFAULT_MODEL),
            system    = data.get("system",    DEFAULT_SYSTEM),
            max_turns = data.get("max_turns", 20),
            verbose   = verbose,
        )
        session._summary = data.get("summary", "")
        session._history = data.get("history", [])

        if verbose:
            from rich.console import Console
            Console().print(
                f"[dim green]📂 Session loaded ← {path} "
                f"({session.turn_count} turns, "
                f"{'có' if session._summary else 'không có'} summary)[/dim green]"
            )
        return session

    def reset(self) -> None:
        """Xóa toàn bộ lịch sử — bắt đầu cuộc trò chuyện mới."""
        self._history.clear()
        self._summary = ""

    @property
    def turn_count(self) -> int:
        """Số cặp hỏi-đáp đã có trong session."""
        return len(self._history) // 2

    def print_history(self) -> None:
        """In lại lịch sử trò chuyện ra terminal."""
        from rich.console import Console
        from rich.panel import Panel
        c = Console()
        for msg in self._history:
            if msg["role"] == "user":
                c.print(Panel(msg["content"], title="[cyan]Bạn[/cyan]", border_style="cyan"))
            else:
                c.print(Panel(msg["content"], title="[green]Model[/green]", border_style="green"))

    # ── Nội bộ ───────────────────────────────────────────────────────────────

    def _build_messages(self, prompt: str) -> list[dict]:
        """
        Ghép messages theo thứ tự:
          [system] → [summary nếu có] → [window gần nhất] → [câu hỏi mới]
        """
        window = self._history[-(self.max_turns * 2):]

        messages = [{"role": "system", "content": self.system}]

        # Nếu có summary từ lịch sử cũ → thêm vào sau system
        if self._summary:
            messages.append({
                "role":    "assistant",
                "content": f"[Previous conversation summary]\n{self._summary}",
            })

        messages.extend(window)
        messages.append({"role": "user", "content": prompt})
        return messages

    def _append(self, prompt: str, reply: str) -> None:
        """Thêm turn mới. Nếu vượt max_turns → tóm tắt phần cũ trước."""
        self._history.append({"role": "user",      "content": prompt})
        self._history.append({"role": "assistant", "content": reply})

        # Kích hoạt summary khi lịch sử vượt max_turns
        if len(self._history) > self.max_turns * 2:
            self._compress()

    def _compress(self) -> None:
        """
        Tóm tắt nửa đầu lịch sử, giữ lại nửa sau.
        Gọi model nhanh nhất (qwen) để tóm tắt — không cần reasoning.
        """
        half = len(self._history) // 2
        old_turns  = self._history[:half]
        keep_turns = self._history[half:]

        # Chuyển lịch sử cũ thành text thuần
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in old_turns
        )
        summary_prompt = self._SUMMARY_PROMPT.format(history=history_text)

        if self.verbose:
            from rich.console import Console
            Console().print(f"\n[dim yellow]⚙ Compressing {half} messages into summary...[/dim yellow]")

        # Dùng model nhanh để tóm tắt (bất kể session đang dùng model gì)
        from src.router import MODEL_FAST, get_ctx
        response = ollama.chat(
            model=MODEL_FAST,
            messages=[{"role": "user", "content": summary_prompt}],
            options={"num_ctx": get_ctx(MODEL_FAST)},
        )
        new_summary = response["message"]["content"].strip()

        # Gộp với summary cũ (nếu đã có từ lần compress trước)
        if self._summary:
            self._summary = f"{self._summary}\n{new_summary}"
        else:
            self._summary = new_summary

        # Chỉ giữ lại nửa sau
        self._history = keep_turns

        if self.verbose:
            from rich.console import Console
            Console().print(f"[dim yellow]⚙ Summary updated. History reduced to {len(self._history)//2} turns.[/dim yellow]\n")


def list_models() -> list[str]:
    """Liệt kê tất cả model đang có trên máy."""
    return [m.model for m in ollama.list().models]


# ── Demo ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    from rich.console import Console
    console = Console()

    SESSION_FILE = "sessions/demo.json"

    # Nếu đã có session cũ → load tiếp, không có → tạo mới
    if os.path.exists(SESSION_FILE):
        console.print("[bold cyan]LoLM — Tiếp tục session cũ[/bold cyan]\n")
        session = ChatSession.load(SESSION_FILE, verbose=True)
        console.print(f"[dim]Đang ở turn {session.turn_count}, có summary: {'có' if session._summary else 'không'}[/dim]\n")
    else:
        console.print("[bold cyan]LoLM — Session mới[/bold cyan]\n")
        session = ChatSession(verbose=True)

    questions = [
        "Xin chào! Tên tôi là K, tôi đang xây dựng dự án AI local.",
        "Bạn có thể tóm tắt lại tôi vừa nói gì không?",
        "Tên tôi là gì?",
    ]

    for q in questions:
        console.print(f"\n[cyan bold]K:[/cyan bold] {q}")
        console.print("[green bold]Model:[/green bold] ", end="")
        for chunk in session.stream(q):
            console.print(chunk, end="", highlight=False)
        console.print()

    # Lưu session sau mỗi lần chạy
    session.save(SESSION_FILE)
    console.print(f"\n[dim]Tổng số turns: {session.turn_count}[/dim]")
