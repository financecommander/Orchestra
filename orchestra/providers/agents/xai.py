"""XAI (Grok) provider for Orchestra DSL."""

import os
import time
from typing import Any, Dict, Optional
from orchestra.providers.base import BaseProvider
from orchestra.core.agent import Agent
from orchestra.core.task import Task
from orchestra.core.context import Context


class XAIProvider(BaseProvider):
    """XAI Grok API provider with retry logic.

    This provider integrates with XAI's Grok API for agent task execution.
    Includes exponential backoff retry logic for API failures.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the XAI provider.

        Args:
            config: Configuration including:
                - api_key: API key for XAI (defaults to XAI_API_KEY env var)
                - model: Model name to use (default: grok-beta)
                - temperature: Sampling temperature (default: 0.7)
                - max_tokens: Maximum tokens to generate (default: 2048)
                - max_retries: Maximum number of retries (default: 3)
                - retry_delay: Initial retry delay in seconds (default: 1)
        """
        super().__init__(config)
        self.api_key = self.config.get("api_key") or os.getenv("XAI_API_KEY")
        self.model = self.config.get("model", "grok-beta")
        self.temperature = self.config.get("temperature", 0.7)
        self.max_tokens = self.config.get("max_tokens", 2048)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1)

    def execute(self, agent: Agent, task: Task, context: Context) -> Any:
        """Execute a task using XAI API with retry logic.

        Args:
            agent: Agent executing the task
            task: Task to execute
            context: Execution context

        Returns:
            Task execution result with Grok response

        Raises:
            RuntimeError: If all retries are exhausted
        """
        # Build messages from task and context
        messages = self._build_messages(agent, task, context)

        # Execute with retry logic
        response = self._call_grok_with_retry(messages)

        return {
            "status": "completed",
            "agent": agent.name,
            "task": task.name,
            "response": response,
            "model": self.model,
            "provider": "xai",
        }

    def _build_messages(self, agent: Agent, task: Task, context: Context) -> list[Dict[str, str]]:
        """Build messages for Grok API.

        Args:
            agent: Agent configuration
            task: Task to execute
            context: Execution context

        Returns:
            List of message dictionaries
        """
        messages = []

        # Add system message if available
        if agent.system_prompt:
            messages.append({"role": "system", "content": agent.system_prompt})

        # Build user message
        content_parts = []
        content_parts.append(f"Task: {task.description}")

        if task.inputs:
            content_parts.append(f"\nInputs: {task.inputs}")

        if context.variables:
            content_parts.append(f"\nContext: {context.variables}")

        messages.append({"role": "user", "content": "\n".join(content_parts)})

        return messages

    def _call_grok_with_retry(self, messages: list[Dict[str, str]]) -> str:
        """Call Grok API with exponential backoff retry.

        Args:
            messages: Messages to send to Grok

        Returns:
            Grok's response text

        Raises:
            RuntimeError: If all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return self._call_grok(messages)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff: delay * 2^attempt
                    delay = self.retry_delay * (2**attempt)
                    time.sleep(delay)

        raise RuntimeError(
            f"Failed to call Grok API after {self.max_retries} retries: {last_exception}"
        )

    def _call_grok(self, messages: list[Dict[str, str]]) -> str:
        """Call Grok API.

        Args:
            messages: Messages to send

        Returns:
            Grok response text
        """
        # This is a placeholder implementation
        # In production, this would use XAI's API (OpenAI-compatible):
        #
        # import openai
        # client = openai.OpenAI(
        #     api_key=self.api_key,
        #     base_url="https://api.x.ai/v1"
        # )
        # response = client.chat.completions.create(
        #     model=self.model,
        #     messages=messages,
        #     temperature=self.temperature,
        #     max_tokens=self.max_tokens
        # )
        # return response.choices[0].message.content

        if not self.api_key:
            return "[Simulated Grok response - no API key provided]"

        return f"[Grok {self.model} response to: {messages[-1]['content'][:100]}...]"

    def validate_config(self) -> bool:
        """Validate XAI provider configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.model:
            raise ValueError("Model name is required")

        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")

        if self.max_tokens < 1:
            raise ValueError("max_tokens must be positive")

        if self.max_retries < 1:
            raise ValueError("max_retries must be at least 1")

        return True

    def __repr__(self) -> str:
        """String representation of the provider."""
        return f"XAIProvider(model='{self.model}')"
