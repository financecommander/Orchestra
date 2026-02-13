"""Base provider interface for AI agents."""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Abstract base class for AI agent providers."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    @abstractmethod
    def execute(self, prompt: str, model: str | None = None) -> str:
        """Send a prompt to the AI provider and return the response."""
        ...

    def __repr__(self) -> str:
        masked = f"...{self.api_key[-4:]}" if self.api_key and len(self.api_key) > 4 else "***"
        return f"{self.__class__.__name__}(api_key={masked!r})"
