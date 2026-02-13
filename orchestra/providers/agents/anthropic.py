"""Anthropic/Claude AI provider."""

import json
import re

import anthropic as anthropic_sdk

from orchestra.providers.agents.base import BaseProvider


def _parse_sse_text(raw: str) -> str:
    """Extract text content from a raw SSE response stream."""
    text_parts = []
    for line in raw.split("\n"):
        if not line.startswith("data: "):
            continue
        payload = line[len("data: "):]
        if payload in ("[DONE]", ""):
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        delta = data.get("delta", {})
        if delta.get("type") == "text_delta":
            text_parts.append(delta.get("text", ""))
    return "".join(text_parts)


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic Claude models."""

    DEFAULT_MODEL = "claude-sonnet-4-5"

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key=api_key)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = anthropic_sdk.Anthropic(api_key=self.api_key)
        return self._client

    def execute(self, prompt: str, model: str | None = None) -> str:
        model = model or self.DEFAULT_MODEL
        message = self.client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        # Handle both parsed Message objects and raw SSE strings (proxy environments)
        if isinstance(message, str):
            return _parse_sse_text(message)
        return message.content[0].text
