"""OpenAI AI provider."""

import openai as openai_sdk

from orchestra.providers.agents.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI models (GPT-4, etc.)."""

    DEFAULT_MODEL = "gpt-4-turbo"

    def __init__(self, api_key: str | None = None):
        super().__init__(api_key=api_key)
        self.client = openai_sdk.OpenAI(api_key=self.api_key)

    def execute(self, prompt: str, model: str | None = None) -> str:
        model = model or self.DEFAULT_MODEL
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
