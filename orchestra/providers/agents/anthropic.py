"""Anthropic (Claude) provider for Orchestra DSL."""

import os
import time
from typing import Any, Dict, Optional
from orchestra.providers.base import BaseProvider
from orchestra.core.agent import Agent
from orchestra.core.task import Task
from orchestra.core.context import Context


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider with retry logic.

    This provider integrates with Anthropic's Claude API for agent task execution.
    Includes exponential backoff retry logic for API failures.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Anthropic provider.

        Args:
            config: Configuration including:
                - api_key: API key for Anthropic (defaults to ANTHROPIC_API_KEY env var)
                - model: Model name to use (default: claude-3-5-sonnet-20241022)
                - temperature: Sampling temperature (default: 0.7)
                - max_tokens: Maximum tokens to generate (default: 4096)
                - max_retries: Maximum number of retries (default: 3)
                - retry_delay: Initial retry delay in seconds (default: 1)
        """
        super().__init__(config)
        self.api_key = self.config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        self.model = self.config.get("model", "claude-3-5-sonnet-20241022")
        self.temperature = self.config.get("temperature", 0.7)
        self.max_tokens = self.config.get("max_tokens", 4096)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1)

    def execute(self, agent: Agent, task: Task, context: Context) -> Any:
        """Execute a task using Claude API with retry logic.

        Args:
            agent: Agent executing the task
            task: Task to execute
            context: Execution context

        Returns:
            Task execution result with Claude response

        Raises:
            RuntimeError: If all retries are exhausted
        """
        # Build messages from task and context
        messages = self._build_messages(agent, task, context)

        # Execute with retry logic
        response = self._call_claude_with_retry(messages, agent.system_prompt)

        return {
            "status": "completed",
            "agent": agent.name,
            "task": task.name,
            "response": response,
            "model": self.model,
            "provider": "anthropic",
        }

    def _build_messages(self, agent: Agent, task: Task, context: Context) -> list[Dict[str, str]]:
        """Build messages for Claude API.

        Args:
            agent: Agent configuration
            task: Task to execute
            context: Execution context

        Returns:
            List of message dictionaries
        """
        content_parts = []

        # Add task description
        content_parts.append(f"Task: {task.description}")

        # Add task inputs
        if task.inputs:
            content_parts.append(f"\nInputs: {task.inputs}")

        # Add relevant context variables
        if context.variables:
            content_parts.append(f"\nContext: {context.variables}")

        return [{"role": "user", "content": "\n".join(content_parts)}]

    def _call_claude_with_retry(
        self, messages: list[Dict[str, str]], system_prompt: Optional[str] = None
    ) -> str:
        """Call Claude API with exponential backoff retry.

        Args:
            messages: Messages to send to Claude
            system_prompt: Optional system prompt

        Returns:
            Claude's response text

        Raises:
            RuntimeError: If all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return self._call_claude(messages, system_prompt)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff: delay * 2^attempt
                    delay = self.retry_delay * (2**attempt)
                    time.sleep(delay)

        raise RuntimeError(
            f"Failed to call Claude API after {self.max_retries} retries: {last_exception}"
        )

    def _call_claude(
        self, messages: list[Dict[str, str]], system_prompt: Optional[str] = None
    ) -> str:
        """Call Claude API.

        Args:
            messages: Messages to send
            system_prompt: Optional system prompt

        Returns:
            Claude response text
        """
        # This is a placeholder implementation
        # In production, this would use the anthropic Python SDK:
        #
        # import anthropic
        # client = anthropic.Anthropic(api_key=self.api_key)
        # response = client.messages.create(
        #     model=self.model,
        #     max_tokens=self.max_tokens,
        #     temperature=self.temperature,
        #     system=system_prompt,
        #     messages=messages
        # )
        # return response.content[0].text

        if not self.api_key:
            return "[Simulated Claude response - no API key provided]"

        return f"[Claude {self.model} response to: {messages[0]['content'][:100]}...]"

    def validate_config(self) -> bool:
        """Validate Anthropic provider configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.model:
            raise ValueError("Model name is required")

        if self.temperature < 0 or self.temperature > 1:
            raise ValueError("Temperature must be between 0 and 1")

        if self.max_tokens < 1:
            raise ValueError("max_tokens must be positive")

        if self.max_retries < 1:
            raise ValueError("max_retries must be at least 1")

        return True

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"AnthropicProvider(model='{self.model}')"
