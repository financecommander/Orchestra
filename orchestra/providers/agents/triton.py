"""Triton provider for Orchestra DSL.

Implements the triton-ternary-coder model family via the Triton inference
backend, used for guardian-caste reasoning in codeforge-hub workflows.
"""

import os
import time
from typing import Any, Dict, Optional
from orchestra.providers.base import BaseProvider
from orchestra.core.agent import Agent
from orchestra.core.task import Task
from orchestra.core.context import Context


class TritonProvider(BaseProvider):
    """Triton inference provider with retry logic.

    This provider integrates with the Triton inference backend for agent task
    execution, supporting the triton-ternary-coder model family used in
    guardian-caste codeforge-hub workflows.
    Includes exponential backoff retry logic for API failures.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Triton provider.

        Args:
            config: Configuration including:
                - api_key: API key for Triton (defaults to TRITON_API_KEY env var)
                - base_url: Triton server base URL (defaults to TRITON_BASE_URL env var)
                - model: Model name to use (default: triton-ternary-coder-8b)
                - temperature: Sampling temperature (default: 0.7)
                - max_tokens: Maximum tokens to generate (default: 4096)
                - max_retries: Maximum number of retries (default: 3)
                - retry_delay: Initial retry delay in seconds (default: 1)
        """
        super().__init__(config)
        self.api_key = self.config.get("api_key") or os.getenv("TRITON_API_KEY")
        self.base_url = self.config.get("base_url") or os.getenv(
            "TRITON_BASE_URL", "http://localhost:8000"
        )
        self.model = self.config.get("model", "triton-ternary-coder-8b")
        self.temperature = self.config.get("temperature", 0.7)
        self.max_tokens = self.config.get("max_tokens", 4096)
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1)

    def execute(self, agent: Agent, task: Task, context: Context) -> Any:
        """Execute a task using Triton inference with retry logic.

        Args:
            agent: Agent executing the task
            task: Task to execute
            context: Execution context

        Returns:
            Task execution result with Triton model response

        Raises:
            RuntimeError: If all retries are exhausted
        """
        messages = self._build_messages(agent, task, context)
        response = self._call_triton_with_retry(messages, agent.system_prompt)

        return {
            "status": "completed",
            "agent": agent.name,
            "task": task.name,
            "response": response,
            "model": self.model,
            "provider": "triton",
        }

    def _build_messages(
        self, agent: Agent, task: Task, context: Context
    ) -> list[Dict[str, str]]:
        """Build messages for Triton inference.

        Args:
            agent: Agent configuration
            task: Task to execute
            context: Execution context

        Returns:
            List of message dictionaries
        """
        messages = []

        if agent.system_prompt:
            messages.append({"role": "system", "content": agent.system_prompt})

        content_parts = [f"Task: {task.description}"]

        if task.inputs:
            content_parts.append(f"\nInputs: {task.inputs}")

        if context.variables:
            content_parts.append(f"\nContext: {context.variables}")

        messages.append({"role": "user", "content": "\n".join(content_parts)})

        return messages

    def _call_triton_with_retry(
        self,
        messages: list[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Call Triton inference endpoint with exponential backoff retry.

        Args:
            messages: Messages to send to the model
            system_prompt: Optional system prompt (used when not in messages)

        Returns:
            Model response text

        Raises:
            RuntimeError: If all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return self._call_triton(messages)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    time.sleep(delay)

        raise RuntimeError(
            f"Failed to call Triton API after {self.max_retries} retries: {last_exception}"
        )

    def _call_triton(self, messages: list[Dict[str, str]]) -> str:
        """Call Triton inference endpoint.

        Args:
            messages: Messages to send

        Returns:
            Model response text
        """
        # This is a placeholder implementation.
        # In production this would call the Triton HTTP/gRPC inference endpoint,
        # for example using the tritonclient library:
        #
        # import tritonclient.http as httpclient
        # client = httpclient.InferenceServerClient(url=self.base_url)
        # inputs = [httpclient.InferInput("text", [1], "BYTES")]
        # inputs[0].set_data_from_numpy(np.array([messages[-1]["content"]], dtype=object))
        # outputs = [httpclient.InferRequestedOutput("output")]
        # response = client.infer(self.model, inputs, outputs=outputs)
        # return response.as_numpy("output")[0].decode("utf-8")

        if not self.api_key:
            return "[Simulated Triton response - no API key provided]"

        return f"[Triton {self.model} response to: {messages[-1]['content'][:100]}...]"

    def validate_config(self) -> bool:
        """Validate Triton provider configuration.

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
        return f"TritonProvider(model='{self.model}')"
