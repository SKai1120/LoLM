"""
CrewAI Tool wrappers — bọc các tools từ src/agent.py thành CrewAI-compatible tools.

Tái dùng hoàn toàn logic _execute() từ src/agent.py, chỉ thêm @tool decorator.
"""

from __future__ import annotations

from crewai.tools import tool
from src.agent import _execute
from src.rag import KnowledgeBase

# Global kb reference — được set bởi AgentCrew.__init__() khi khởi động
_global_kb: KnowledgeBase | None = None


@tool("ReadFile")
def read_file_tool(path: str) -> str:
    """Đọc nội dung file text, code, markdown, hoặc bất kỳ file text nào. Input: đường dẫn file."""
    return _execute("read_file", {"path": path}, kb=None)


@tool("ListDir")
def list_dir_tool(path: str = ".") -> str:
    """Liệt kê tất cả files và thư mục con trong một đường dẫn. Input: đường dẫn (mặc định '.')."""
    return _execute("list_dir", {"path": path}, kb=None)


@tool("FetchURL")
def fetch_url_tool(url: str) -> str:
    """Fetch và đọc nội dung văn bản từ một trang web. Input: URL đầy đủ bao gồm https://."""
    return _execute("fetch_url", {"url": url}, kb=None)


@tool("WebSearch")
def web_search_tool(query: str) -> str:
    """Tìm kiếm thông tin trên internet với DuckDuckGo. Input: câu truy vấn tìm kiếm."""
    try:
        from duckduckgo_search import DDGS
        results = list(DDGS().text(query, max_results=5))
        if not results:
            return "Không tìm thấy kết quả."
        return "\n\n".join(
            f"**{r['title']}**\n{r['body']}\nURL: {r['href']}"
            for r in results
        )
    except Exception as e:
        return f"Lỗi tìm kiếm: {e}"


@tool("SearchKB")
def search_kb_tool(query: str) -> str:
    """Tìm kiếm trong knowledge base đã được index. Input: câu truy vấn ngữ nghĩa."""
    return _execute("search_kb", {"query": query, "k": 5}, kb=_global_kb)


@tool("GitLog")
def git_log_tool(path: str = ".", n: int = 10) -> str:
    """Xem lịch sử git commits của một repository. Input: đường dẫn repo, số commits muốn xem."""
    return _execute("git_log", {"path": path, "n": n}, kb=None)


ALL_TOOLS = [
    read_file_tool,
    list_dir_tool,
    fetch_url_tool,
    web_search_tool,
    search_kb_tool,
    git_log_tool,
]
