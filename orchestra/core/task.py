"""Task module for Orchestra DSL."""

from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(Enum):
    """Status of a task execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a task in the Orchestra DSL.

    A task is a unit of work that can be assigned to an agent
    and executed as part of a workflow.
    """

    name: str
    description: str
    agent: Optional[str] = None
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None

    def __post_init__(self):
        """Validate task configuration."""
        if not self.name:
            raise ValueError("Task name cannot be empty")
        if not self.description:
            raise ValueError("Task description cannot be empty")

    def mark_running(self):
        """Mark task as running."""
        self.status = TaskStatus.RUNNING

    def mark_completed(self, result: Any):
        """Mark task as completed with result."""
        self.status = TaskStatus.COMPLETED
        self.result = result

    def mark_failed(self, error: str):
        """Mark task as failed with error."""
        self.status = TaskStatus.FAILED
        self.error = error

    def is_ready(self, completed_tasks: set) -> bool:
        """Check if task is ready to execute based on dependencies.

        Args:
            completed_tasks: Set of completed task names

        Returns:
            True if all dependencies are satisfied
        """
        return all(dep in completed_tasks for dep in self.dependencies)

    def __repr__(self) -> str:
        """String representation of the task."""
        return f"Task(name='{self.name}', status='{self.status.value}')"
