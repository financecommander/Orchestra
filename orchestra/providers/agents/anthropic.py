"""Anthropic/Claude AI provider."""

import anthropic as anthropic_sdk

from orchestra.providers.agents.base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Provider for Anthropic Claude models."""

    DEFAULT_MODEL = "claude-sonnet-4-5"

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key=api_key)
        self.client = anthropic_sdk.Anthropic(api_key=self.api_key)

    def execute(self, prompt: str, model: str | None = None) -> str:
        model = model or self.DEFAULT_MODEL
        message = self.client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
