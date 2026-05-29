"""
CrewAI Agent definitions — ManagerAgent (Claude API) và ExecutorAgent (Qwen local).
"""

from __future__ import annotations

import os

from crewai import Agent, LLM


def make_manager_agent() -> Agent:
    """
    ManagerAgent: dùng Claude API để lập kế hoạch và tổng hợp kết quả.
    Có quyền delegate tasks cho Executor.
    """
    llm = LLM(
        model="claude-sonnet-4-6",
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )
    return Agent(
        role="Trưởng nhóm AI (Chief of Staff)",
        goal=(
            "Nhận yêu cầu từ người dùng, phân tích sâu, lập kế hoạch các bước cụ thể, "
            "giao việc cho Executor thực thi, rồi tổng hợp tất cả kết quả thành báo cáo "
            "rõ ràng, có cấu trúc, bằng tiếng Việt."
        ),
        backstory=(
            "Bạn là AI quản lý dự án kỳ cựu với kinh nghiệm phân tích hệ thống. "
            "Bạn giỏi phân rã yêu cầu phức tạp thành bước thực thi cụ thể và "
            "tổng hợp thông tin từ nhiều nguồn thành báo cáo súc tích."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=5,
    )


def make_executor_agent(tools: list) -> Agent:
    """
    ExecutorAgent: dùng Qwen local để thực thi subtasks với tools.
    Không có quyền delegate — chỉ thực thi.
    """
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    llm = LLM(
        model="ollama/qwen2.5:14b",
        base_url=base_url,
    )
    return Agent(
        role="Kỹ sư thực thi (Field Engineer)",
        goal=(
            "Nhận subtask cụ thể từ Manager, sử dụng tools để thu thập thông tin "
            "hoặc thực hiện hành động, rồi báo cáo kết quả chi tiết và chính xác."
        ),
        backstory=(
            "Bạn là AI chuyên thực thi. Khi cần thông tin cụ thể, bạn luôn dùng tools "
            "thay vì đoán. Bạn báo cáo kết quả thực tế từ tools, không bịa đặt. "
            "Bạn không dùng tiếng Trung hay ngôn ngữ khác ngoài tiếng Việt."
        ),
        llm=llm,
        tools=tools,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )
