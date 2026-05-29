"""
LoLM Crew — Multi-Agent System với CrewAI.

Sơ đồ hoạt động:
    User request
        ↓
    AgentCrew.run(task)
        ↓
    ManagerAgent (Claude API) → phân rã thành subtasks
        ↓
    ExecutorAgent (Qwen local) → thực thi với tools
        ↓
    ManagerAgent → tổng hợp kết quả cuối
"""
