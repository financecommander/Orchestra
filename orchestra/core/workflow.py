"""Workflow module for Orchestra DSL."""

from typing import Any, Dict, List
from dataclasses import dataclass, field
from orchestra.core.task import Task
from orchestra.core.agent import Agent


@dataclass
class Workflow:
    """Represents a workflow in the Orchestra DSL.

    A workflow is a collection of tasks and agents that work together
    to accomplish a complex goal. It manages task dependencies and
    execution order.
    """

    name: str
    description: str
    agents: Dict[str, Agent] = field(default_factory=dict)
    tasks: Dict[str, Task] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate workflow configuration."""
        if not self.name:
            raise ValueError("Workflow name cannot be empty")
        if not self.description:
            raise ValueError("Workflow description cannot be empty")

    def add_agent(self, agent: Agent) -> "Workflow":
        """Add an agent to the workflow.

        Args:
            agent: Agent instance to add

        Returns:
            Self for method chaining
        """
        if agent.name in self.agents:
            raise ValueError(f"Agent '{agent.name}' already exists in workflow")
        self.agents[agent.name] = agent
        return self

    def add_task(self, task: Task) -> "Workflow":
        """Add a task to the workflow.

        Args:
            task: Task instance to add

        Returns:
            Self for method chaining
        """
        if task.name in self.tasks:
            raise ValueError(f"Task '{task.name}' already exists in workflow")

        # Validate that task's agent exists if specified
        if task.agent and task.agent not in self.agents:
            raise ValueError(f"Agent '{task.agent}' not found in workflow")

        # Validate dependencies
        for dep in task.dependencies:
            if dep not in self.tasks:
                raise ValueError(f"Dependency '{dep}' not found in workflow")

        self.tasks[task.name] = task
        return self

    def get_execution_order(self) -> List[str]:
        """Get task execution order based on dependencies.

        Returns:
            List of task names in execution order

        Raises:
            ValueError: If circular dependencies are detected
        """
        order = []
        visited = set()
        visiting = set()

        def visit(task_name: str):
            if task_name in visiting:
                raise ValueError(f"Circular dependency detected involving task '{task_name}'")
            if task_name in visited:
                return

            visiting.add(task_name)
            task = self.tasks[task_name]

            for dep in task.dependencies:
                visit(dep)

            visiting.remove(task_name)
            visited.add(task_name)
            order.append(task_name)

        for task_name in self.tasks:
            visit(task_name)

        return order

    def validate(self) -> bool:
        """Validate the workflow configuration.

        Returns:
            True if workflow is valid

        Raises:
            ValueError: If workflow validation fails
        """
        # Check for circular dependencies
        self.get_execution_order()

        # Validate all tasks have valid agents
        for task in self.tasks.values():
            if task.agent and task.agent not in self.agents:
                raise ValueError(f"Task '{task.name}' references unknown agent '{task.agent}'")

        return True

    def __repr__(self) -> str:
        """String representation of the workflow."""
        return f"Workflow(name='{self.name}', tasks={len(self.tasks)}, agents={len(self.agents)})"
