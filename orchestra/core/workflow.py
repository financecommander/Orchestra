"""Workflow orchestration engine."""

from typing import Optional

from orchestra.core.task import Task
from orchestra.core.gates import Gate


class Workflow:
    """Orchestrates multi-agent task execution with dependency resolution and gate checks."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.tasks: list[Task] = []
        self.gates: list[Gate] = []

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def add_tasks(self, tasks: list[Task]) -> None:
        self.tasks.extend(tasks)

    def add_gate(self, gate: "Gate") -> None:
        self.gates.append(gate)

    def add_gates(self, gates: list["Gate"]) -> None:
        self.gates.extend(gates)

    def _resolve_execution_order(self) -> list[Task]:
        """Topologically sort tasks based on dependencies."""
        resolved: list[Task] = []
        seen: set[str] = set()

        def visit(task: Task) -> None:
            if task.name in seen:
                return
            for dep in task.dependencies:
                visit(dep)
            seen.add(task.name)
            resolved.append(task)

        for task in self.tasks:
            visit(task)
        return resolved

    def _check_gates(self, task_name: str, result: str) -> None:
        """Run all gate checks against a task result."""
        for gate in self.gates:
            gate.check(task_name, result)

    def execute(self) -> dict[str, str]:
        """Execute all tasks in dependency order, applying gate checks."""
        ordered = self._resolve_execution_order()
        results: dict[str, str] = {}

        for task in ordered:
            dep_results = {dep.name: results[dep.name] for dep in task.dependencies if dep.name in results}
            result = task.execute(context=dep_results)
            self._check_gates(task.name, result)
            results[task.name] = result

        return results

    def __repr__(self) -> str:
        return f"Workflow(name={self.name!r}, tasks={len(self.tasks)}, gates={len(self.gates)})"
