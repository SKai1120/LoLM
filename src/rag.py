"""
LoLM RAG — Retrieval-Augmented Generation pipeline.

Sử dụng:
    from src.rag import KnowledgeBase

    kb = KnowledgeBase("my_docs")
    kb.add_file("docs/guide.md")
    kb.add_url("https://example.com/page")
    kb.add_repo("H:/Project/MyRepo", extensions=[".py", ".md"])

    results = kb.search("cách cài đặt?", k=5)
    prompt  = kb.build_prompt("cách cài đặt?", k=5)
"""

import os
import re
import sys
from pathlib import Path

import httpx
import ollama

EMBED_MODEL   = "nomic-embed-text"
CHUNK_SIZE    = 500    # ký tự mỗi chunk
CHUNK_OVERLAP = 80     # ký tự overlap giữa các chunk
DATA_DIR      = "data/chroma"

# Extensions mặc định khi index repo
_CODE_EXT = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".go", ".rs", ".java", ".c", ".cpp", ".h",
    ".md", ".txt", ".rst", ".toml", ".yaml", ".yml", ".json",
    ".html", ".css", ".sh", ".bat", ".ps1",
}


# ── Primitives ────────────────────────────────────────────────────────────────

def _embed(text: str) -> list[float]:
    resp = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return resp["embedding"]


def _chunk(text: str) -> list[str]:
    """Chia text thành các đoạn có overlap."""
    text = text.strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c.strip() for c in chunks if c.strip()]


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_file(path: Path) -> str:
    """Đọc file text hoặc PDF, trả về plain text."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            raise ImportError("Cài pypdf để đọc PDF: pip install pypdf")
    return path.read_text(encoding="utf-8", errors="ignore")


def _fetch_url(url: str) -> str:
    """Fetch trang web, strip HTML, trả về plain text."""
    resp = httpx.get(url, follow_redirects=True, timeout=20,
                     headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    # Strip tags, collapse whitespace
    text = re.sub(r"<script[^>]*>.*?</script>", " ", resp.text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>",  " ", text,      flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── KnowledgeBase ─────────────────────────────────────────────────────────────

class KnowledgeBase:
    """
    Wrapper ChromaDB — index và tìm kiếm tài liệu bằng vector similarity.

    Mỗi collection được lưu persistent tại DATA_DIR.
    Có thể tạo nhiều KB với name khác nhau để tách biệt dữ liệu.
    """

    def __init__(self, name: str = "default", data_dir: str = DATA_DIR) -> None:
        import chromadb
        os.makedirs(data_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(path=data_dir)
        self._col    = self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
        self.name = name

    # ── Thêm tài liệu ────────────────────────────────────────────────────────

    def add_texts(self, texts: list[str], source: str) -> int:
        """Chunk, embed và lưu danh sách text. Trả về số chunk đã lưu."""
        chunks = []
        for t in texts:
            chunks.extend(_chunk(t))
        if not chunks:
            return 0

        embeddings = [_embed(c) for c in chunks]
        ids        = [f"{source}::{i}" for i in range(len(chunks))]
        metadatas  = [{"source": source} for _ in chunks]

        self._col.upsert(ids=ids, embeddings=embeddings,
                         documents=chunks, metadatas=metadatas)
        return len(chunks)

    def add_file(self, path: str) -> int:
        """Index một file (txt, md, py, pdf, ...)."""
        p    = Path(path).resolve()
        text = _load_file(p)
        return self.add_texts([text], source=str(p))

    def add_url(self, url: str) -> int:
        """Fetch và index một trang web."""
        text = _fetch_url(url)
        return self.add_texts([text], source=url)

    def add_repo(
        self,
        repo_path: str,
        extensions: set[str] | None = None,
        skip_dirs: set[str] | None  = None,
    ) -> int:
        """
        Index toàn bộ file trong một thư mục / git repo.

        Args:
            repo_path:  Đường dẫn gốc của repo.
            extensions: Set các extension được index (mặc định: _CODE_EXT).
            skip_dirs:  Thư mục bỏ qua (mặc định: .git, node_modules, __pycache__, .venv).
        """
        if extensions is None:
            extensions = _CODE_EXT
        if skip_dirs is None:
            skip_dirs = {".git", "node_modules", "__pycache__", ".venv", ".mypy_cache"}

        total = 0
        root  = Path(repo_path).resolve()
        for p in root.rglob("*"):
            if any(part in skip_dirs for part in p.parts):
                continue
            if p.is_file() and p.suffix.lower() in extensions:
                try:
                    total += self.add_file(str(p))
                except Exception as e:
                    print(f"[rag] skip {p.name}: {e}", file=sys.stderr)
        return total

    # ── Tìm kiếm ─────────────────────────────────────────────────────────────

    def search(self, query: str, k: int = 5) -> list[dict]:
        """
        Tìm k chunk liên quan nhất với query.

        Trả về list[{"text": ..., "source": ..., "score": float(0-1)}].
        score = 1 là giống nhất (cosine similarity).
        """
        n = min(k, self._col.count())
        if n == 0:
            return []

        results = self._col.query(
            query_embeddings=[_embed(query)],
            n_results=n,
        )
        return [
            {
                "text":   doc,
                "source": meta["source"],
                "score":  round(1 - dist, 4),  # cosine distance → similarity
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    def build_prompt(self, query: str, k: int = 5, score_threshold: float = 0.3) -> str:
        """
        Tạo prompt RAG đầy đủ:
          [Context từ KB] + [câu hỏi gốc]

        Chỉ dùng chunk có score >= score_threshold.
        Nếu không tìm được gì liên quan, trả về query gốc không thay đổi.
        """
        chunks = [c for c in self.search(query, k) if c["score"] >= score_threshold]
        if not chunks:
            return query

        context_parts = []
        for i, c in enumerate(chunks, 1):
            context_parts.append(f"[{i}] {c['source']}\n{c['text']}")
        context = "\n\n".join(context_parts)

        return (
            f"Dưới đây là các đoạn tài liệu liên quan:\n\n"
            f"{context}\n\n"
            f"---\n"
            f"Dựa vào tài liệu trên, hãy trả lời câu hỏi sau:\n{query}"
        )

    # ── Tiện ích ──────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Số chunk đang lưu trong KB."""
        return self._col.count()

    def clear(self) -> None:
        """Xóa toàn bộ dữ liệu trong collection."""
        self._client.delete_collection(self.name)
        self._col = self._client.get_or_create_collection(
            name=self.name,
            metadata={"hnsw:space": "cosine"},
        )

    def __repr__(self) -> str:
        return f"KnowledgeBase(name={self.name!r}, chunks={self.count()})"
