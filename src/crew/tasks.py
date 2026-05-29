"""
CrewAI Task templates — 3 loại task trong pipeline Manager→Executor→Synthesis.
"""

from __future__ import annotations

from crewai import Agent, Task


def make_plan_task(user_request: str, manager: Agent) -> Task:
    """Task 1: Manager phân tích và lập kế hoạch subtasks."""
    return Task(
        description=(
            f"Yêu cầu từ người dùng:\n{user_request}\n\n"
            "Phân tích yêu cầu trên và xác định 2-4 subtask cụ thể cần thực hiện. "
            "Mỗi subtask phải đủ rõ ràng để Executor biết chính xác phải làm gì, "
            "bao gồm cả công cụ nào có thể dùng (đọc file, tìm web, fetch URL, v.v.)."
        ),
        expected_output=(
            "Danh sách subtasks dạng JSON array:\n"
            '[{"id": 1, "task": "mô tả subtask 1 chi tiết"}, '
            '{"id": 2, "task": "mô tả subtask 2 chi tiết"}, ...]'
        ),
        agent=manager,
    )


def make_execute_task(subtask: str, executor: Agent) -> Task:
    """Task 2: Executor thực thi một subtask cụ thể."""
    return Task(
        description=(
            f"Thực hiện subtask sau và báo cáo kết quả đầy đủ:\n\n{subtask}\n\n"
            "Hướng dẫn:\n"
            "- Dùng tools khi cần thông tin từ file, web, knowledge base\n"
            "- Báo cáo đúng những gì tìm được, không suy diễn thêm\n"
            "- Nếu không tìm được thông tin, nói rõ lý do"
        ),
        expected_output=(
            "Báo cáo chi tiết kết quả thực hiện subtask, bao gồm:\n"
            "- Những thông tin thu thập được\n"
            "- Nguồn thông tin (file path / URL)\n"
            "- Nhận xét ngắn gọn nếu cần"
        ),
        agent=executor,
    )


def make_synthesis_task(user_request: str, manager: Agent) -> Task:
    """Task 3: Manager tổng hợp tất cả kết quả thành báo cáo cuối."""
    return Task(
        description=(
            f"Yêu cầu gốc của người dùng: '{user_request}'\n\n"
            "Dựa trên tất cả kết quả từ các subtasks đã thực hiện (trong context), "
            "tổng hợp thành một câu trả lời hoàn chỉnh, rõ ràng, có cấu trúc. "
            "Câu trả lời phải:\n"
            "- Trả lời trực tiếp yêu cầu gốc\n"
            "- Có đầu mục / bullet points nếu phù hợp\n"
            "- Bằng tiếng Việt\n"
            "- Không lặp lại thông tin thừa"
        ),
        expected_output=(
            "Báo cáo tổng hợp đầy đủ, rõ ràng, bằng tiếng Việt, "
            "trả lời trực tiếp yêu cầu gốc của người dùng."
        ),
        agent=manager,
    )
