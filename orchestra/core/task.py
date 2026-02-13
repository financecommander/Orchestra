"""Task definition for workflow steps."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from orchestra.providers.agents.base import BaseProvider


class Task:
    """A single unit of work within a workflow, executed by an AI agent."""

    def __init__(
        self,
        name: str,
        agent: "BaseProvider",
        prompt: str,
        dependencies: Optional[list["Task"]] = None,
    ):
        self.name = name
        self.agent = agent
        self.prompt = prompt
        self.dependencies: list[Task] = dependencies or []

    def execute(self, context: Optional[dict[str, str]] = None) -> str:
        """Execute this task using the assigned agent."""
        full_prompt = self.prompt
        if context:
            context_str = "\n\n".join(
                f"--- {name} ---\n{output}" for name, output in context.items()
            )
            full_prompt = f"Previous stage outputs:\n{context_str}\n\n{self.prompt}"

        return self.agent.execute(prompt=full_prompt)

    def __repr__(self) -> str:
        deps = [d.name for d in self.dependencies]
        return f"Task(name={self.name!r}, agent={self.agent!r}, deps={deps})"
