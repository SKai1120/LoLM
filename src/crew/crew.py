"""
AgentCrew — Orchestrator cho Multi-Agent System.

Pattern giống Agent.run() trong src/agent.py:
    for event in crew.run(task):
        # event là CrewEvent (status) hoặc str (kết quả cuối)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from crewai import Crew, Process

from src.crew import tools as crew_tools
from src.crew.agents import make_executor_agent, make_manager_agent
from src.crew.tasks import make_execute_task, make_plan_task, make_synthesis_task
from src.rag import KnowledgeBase


@dataclass
class CrewEvent:
    """Phát ra trong lúc crew chạy — dùng để hiện status trong TUI / Telegram."""
    phase: str    # "planning" | "executing" | "synthesizing" | "done"
    message: str

    def __str__(self) -> str:
        icons = {"planning": "📋", "executing": "⚙️", "synthesizing": "🔗", "done": "✅"}
        return f"{icons.get(self.phase, '•')} {self.message}"


class AgentCrew:
    """
    Điều phối Manager (Claude) và Executor (Qwen) qua 3 phase:
        1. Planning   — Manager phân rã task thành subtasks (JSON)
        2. Executing  — Executor chạy từng subtask với tools
        3. Synthesizing — Manager tổng hợp kết quả cuối
    """

    def __init__(self, kb: KnowledgeBase | None = None) -> None:
        crew_tools._global_kb = kb
        self._manager  = make_manager_agent()
        self._executor = make_executor_agent(crew_tools.ALL_TOOLS)

    def run(self, task: str) -> Iterator[CrewEvent | str]:
        """
        Generator: yields CrewEvent rồi str (câu trả lời cuối).
        Caller xử lý từng loại khác nhau (TUI hiện status, Telegram send message).
        """
        # ── Phase 1: Planning ──────────────────────────────────────────────────
        yield CrewEvent("planning", f"Đang phân tích: {task[:80]}...")

        plan_crew = Crew(
            agents=[self._manager],
            tasks=[make_plan_task(task, self._manager)],
            process=Process.sequential,
            verbose=False,
        )
        plan_output  = str(plan_crew.kickoff())
        subtasks     = self._parse_subtasks(plan_output)

        # ── Phase 2: Executing ─────────────────────────────────────────────────
        exec_results: list[str] = []
        for i, subtask in enumerate(subtasks, 1):
            yield CrewEvent("executing", f"[{i}/{len(subtasks)}] {subtask[:80]}...")

            exec_crew = Crew(
                agents=[self._executor],
                tasks=[make_execute_task(subtask, self._executor)],
                process=Process.sequential,
                verbose=False,
            )
            result = str(exec_crew.kickoff())
            exec_results.append(result)

        # ── Phase 3: Synthesizing ──────────────────────────────────────────────
        yield CrewEvent("synthesizing", "Đang tổng hợp kết quả...")

        # Inject exec results vào context của synthesis task
        synth_task = make_synthesis_task(task, self._manager)
        context_text = "\n\n---\n\n".join(
            f"**Kết quả subtask {i+1}:** {subtasks[i]}\n{r}"
            for i, r in enumerate(exec_results)
        )
        synth_task.description += f"\n\n**Kết quả từ Executor:**\n{context_text}"

        synth_crew = Crew(
            agents=[self._manager],
            tasks=[synth_task],
            process=Process.sequential,
            verbose=False,
        )
        final = str(synth_crew.kickoff())

        # ── Logging ────────────────────────────────────────────────────────────
        self._log(task, subtasks, exec_results, final)

        yield CrewEvent("done", f"Hoàn thành ({len(subtasks)} subtasks)")
        yield final

    @staticmethod
    def _parse_subtasks(plan_text: str) -> list[str]:
        """
        Parse JSON subtasks từ Manager output.
        Fallback về list 1 phần tử nếu parse thất bại.
        """
        try:
            start = plan_text.find("[")
            end   = plan_text.rfind("]") + 1
            if start == -1 or end == 0:
                return [plan_text.strip()]
            data = json.loads(plan_text[start:end])
            return [item.get("task", str(item)) for item in data if item]
        except Exception:
            return [plan_text.strip()]

    @staticmethod
    def _log(
        task: str,
        subtasks: list[str],
        results: list[str],
        final: str,
    ) -> None:
        """Ghi daily log vào data/logs/daily_YYYY-MM-DD.md sau mỗi run."""
        log_dir  = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        today    = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"daily_{today}.md"
        ts       = datetime.now().strftime("%H:%M:%S")

        lines = [
            f"\n## [{ts}] {task[:80]}\n",
            f"**Subtasks ({len(subtasks)}):**",
        ]
        lines += [f"- {s}" for s in subtasks]
        lines += [
            f"\n**Kết quả tổng hợp:**",
            final[:600] + ("..." if len(final) > 600 else ""),
            "\n---\n",
        ]
        with log_file.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))
