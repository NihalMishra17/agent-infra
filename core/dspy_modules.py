from __future__ import annotations

import os

import dspy


def configure_dspy() -> None:
    lm = dspy.LM(
        model=f"anthropic/{os.getenv('DSPY_MODEL', 'claude-3-5-haiku-20241022')}",
        max_tokens=int(os.getenv("DSPY_MAX_TOKENS", "1024")),
    )
    dspy.configure(lm=lm)


# ---------------------------------------------------------------------------
# Planner signatures
# ---------------------------------------------------------------------------

class DecomposeGoal(dspy.Signature):
    """
    Break a high-level user goal into a list of concrete, independently
    executable subtasks. Return ONLY a numbered list, one task per line.
    Each task must be self-contained and actionable by a research executor.
    """
    goal: str = dspy.InputField(desc="High-level user goal")
    past_context: str = dspy.InputField(desc="Relevant past memory, may be empty")
    tasks: str = dspy.OutputField(desc="Numbered list of subtasks, one per line")


class PlannerModule(dspy.Module):
    def __init__(self) -> None:
        self.decompose = dspy.ChainOfThought(DecomposeGoal)

    def forward(self, goal: str, past_context: str = "") -> list[str]:
        pred = self.decompose(goal=goal, past_context=past_context)
        lines = [l.strip() for l in pred.tasks.strip().splitlines() if l.strip()]
        # strip leading "1. " "2. " etc
        tasks = []
        for line in lines:
            parts = line.split(".", 1)
            tasks.append(parts[1].strip() if len(parts) == 2 and parts[0].isdigit() else line)
        return tasks


# ---------------------------------------------------------------------------
# Executor signatures
# ---------------------------------------------------------------------------

class ExecuteTask(dspy.Signature):
    """
    Execute a research subtask thoroughly. Produce a detailed, factual result.
    If you cannot complete the task, explain why clearly.
    """
    task_description: str = dspy.InputField(desc="The specific subtask to execute")
    past_context: str = dspy.InputField(desc="Relevant past memory, may be empty")
    result: str = dspy.OutputField(desc="Detailed result of executing the task")


class ExecutorModule(dspy.Module):
    def __init__(self) -> None:
        self.execute = dspy.ChainOfThought(ExecuteTask)

    def forward(self, task_description: str, past_context: str = "") -> str:
        pred = self.execute(task_description=task_description, past_context=past_context)
        return pred.result
