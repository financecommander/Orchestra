"""Base provider interface for Orchestra DSL."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from orchestra.core.agent import Agent
from orchestra.core.task import Task
from orchestra.core.context import Context


class BaseProvider(ABC):
    """Base class for Orchestra providers.

    Providers implement the actual execution logic for agents,
    such as calling LLM APIs, executing code, or interfacing with
    external systems.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the provider.

        Args:
            config: Optional provider configuration
        """
        self.config = config or {}

    @abstractmethod
    def execute(self, agent: Agent, task: Task, context: Context) -> Any:
        """Execute a task using this provider.

        Args:
            agent: Agent executing the task
            task: Task to execute
            context: Execution context

        Returns:
            Task execution result
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        pass

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"{self.__class__.__name__}()"
