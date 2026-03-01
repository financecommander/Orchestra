"""Tests for agent provider modules."""

import os
import pytest
from unittest.mock import patch
from orchestra.providers.agents.anthropic import AnthropicProvider
from orchestra.providers.agents.openai import OpenAIProvider
from orchestra.providers.agents.xai import XAIProvider
from orchestra.core.agent import Agent
from orchestra.core.task import Task
from orchestra.core.context import Context


class TestAnthropicProvider:
    """Test cases for AnthropicProvider."""

    def test_anthropic_provider_creation(self):
        """Test basic provider creation."""
        provider = AnthropicProvider()
        assert provider.model == "claude-3-5-sonnet-20241022"
        assert provider.temperature == 0.7
        assert provider.max_tokens == 4096
        assert provider.max_retries == 3

    def test_anthropic_provider_with_config(self):
        """Test provider creation with config."""
        config = {
            "model": "claude-3-opus-20240229",
            "temperature": 0.5,
            "max_tokens": 2048,
            "max_retries": 5,
        }
        provider = AnthropicProvider(config=config)
        assert provider.model == "claude-3-opus-20240229"
        assert provider.temperature == 0.5
        assert provider.max_tokens == 2048
        assert provider.max_retries == 5

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_anthropic_provider_env_api_key(self):
        """Test that API key is loaded from environment."""
        provider = AnthropicProvider()
        assert provider.api_key == "test-key"

    def test_anthropic_provider_execute(self):
        """Test provider execute method."""
        provider = AnthropicProvider()
        agent = Agent(
            name="test_agent",
            provider="anthropic",
            system_prompt="You are helpful.",
        )
        task = Task(name="task1", description="Test task")
        context = Context()

        result = provider.execute(agent, task, context)

        assert result["status"] == "completed"
        assert result["agent"] == "test_agent"
        assert result["task"] == "task1"
        assert result["provider"] == "anthropic"
        assert "response" in result

    def test_anthropic_provider_validate_config(self):
        """Test configuration validation."""
        provider = AnthropicProvider()
        assert provider.validate_config() is True

        # Invalid temperature
        provider.temperature = 2.0
        with pytest.raises(ValueError, match="Temperature must be between"):
            provider.validate_config()

        # Invalid max_tokens
        provider.temperature = 0.7
        provider.max_tokens = 0
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            provider.validate_config()

    def test_anthropic_provider_build_messages(self):
        """Test message building."""
        provider = AnthropicProvider()
        agent = Agent(name="test", provider="anthropic")
        task = Task(name="task1", description="Test task", inputs={"key": "value"})
        context = Context()
        context.set("context_key", "context_value")

        messages = provider._build_messages(agent, task, context)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "Test task" in messages[0]["content"]
        assert "key" in messages[0]["content"]
        assert "context_key" in messages[0]["content"]

    def test_anthropic_provider_retry_logic(self):
        """Test retry logic with exponential backoff."""
        provider = AnthropicProvider(config={"max_retries": 3, "retry_delay": 0.1})

        call_count = 0

        def mock_call_claude(messages, system_prompt=None):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("API error")
            return "Success"

        provider._call_claude = mock_call_claude

        result = provider._call_claude_with_retry(
            [{"role": "user", "content": "test"}]
        )
        assert result == "Success"
        assert call_count == 3

    def test_anthropic_provider_retry_exhausted(self):
        """Test that retry raises error when exhausted."""
        provider = AnthropicProvider(config={"max_retries": 2, "retry_delay": 0.01})

        def mock_call_claude(messages, system_prompt=None):
            raise Exception("API error")

        provider._call_claude = mock_call_claude

        with pytest.raises(RuntimeError, match="Failed to call Claude API"):
            provider._call_claude_with_retry([{"role": "user", "content": "test"}])

    def test_anthropic_provider_repr(self):
        """Test string representation."""
        provider = AnthropicProvider()
        assert "AnthropicProvider" in repr(provider)
        assert "claude-3-5-sonnet-20241022" in repr(provider)


class TestOpenAIProvider:
    """Test cases for OpenAIProvider."""

    def test_openai_provider_creation(self):
        """Test basic provider creation."""
        provider = OpenAIProvider()
        assert provider.model == "gpt-4"
        assert provider.temperature == 0.7
        assert provider.max_tokens == 2048
        assert provider.max_retries == 3

    def test_openai_provider_with_config(self):
        """Test provider creation with config."""
        config = {
            "model": "gpt-3.5-turbo",
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        provider = OpenAIProvider(config=config)
        assert provider.model == "gpt-3.5-turbo"
        assert provider.temperature == 0.3
        assert provider.max_tokens == 1024

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-openai"})
    def test_openai_provider_env_api_key(self):
        """Test that API key is loaded from environment."""
        provider = OpenAIProvider()
        assert provider.api_key == "test-key-openai"

    def test_openai_provider_execute(self):
        """Test provider execute method."""
        provider = OpenAIProvider()
        agent = Agent(
            name="test_agent", provider="openai", system_prompt="You are helpful."
        )
        task = Task(name="task1", description="Test task")
        context = Context()

        result = provider.execute(agent, task, context)

        assert result["status"] == "completed"
        assert result["agent"] == "test_agent"
        assert result["provider"] == "openai"

    def test_openai_provider_build_messages(self):
        """Test message building with system prompt."""
        provider = OpenAIProvider()
        agent = Agent(
            name="test", provider="openai", system_prompt="You are a helpful assistant."
        )
        task = Task(name="task1", description="Test task")
        context = Context()

        messages = provider._build_messages(agent, task, context)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."
        assert messages[1]["role"] == "user"

    def test_openai_provider_validate_config(self):
        """Test configuration validation."""
        provider = OpenAIProvider()
        assert provider.validate_config() is True

    def test_openai_provider_repr(self):
        """Test string representation."""
        provider = OpenAIProvider()
        assert "OpenAIProvider" in repr(provider)
        assert "gpt-4" in repr(provider)


class TestXAIProvider:
    """Test cases for XAIProvider."""

    def test_xai_provider_creation(self):
        """Test basic provider creation."""
        provider = XAIProvider()
        assert provider.model == "grok-3-mini"
        assert provider.temperature == 0.7
        assert provider.max_tokens == 2048

    def test_xai_provider_with_config(self):
        """Test provider creation with config."""
        config = {"model": "grok-1", "temperature": 0.8}
        provider = XAIProvider(config=config)
        assert provider.model == "grok-1"
        assert provider.temperature == 0.8

    @patch.dict(os.environ, {"XAI_API_KEY": "test-key-xai"})
    def test_xai_provider_env_api_key(self):
        """Test that API key is loaded from environment."""
        provider = XAIProvider()
        assert provider.api_key == "test-key-xai"

    def test_xai_provider_execute(self):
        """Test provider execute method."""
        provider = XAIProvider()
        agent = Agent(name="test_agent", provider="xai", system_prompt="You audit code.")
        task = Task(name="task1", description="Audit this code")
        context = Context()

        result = provider.execute(agent, task, context)

        assert result["status"] == "completed"
        assert result["provider"] == "xai"

    def test_xai_provider_validate_config(self):
        """Test configuration validation."""
        provider = XAIProvider()
        assert provider.validate_config() is True

    def test_xai_provider_repr(self):
        """Test string representation."""
        provider = XAIProvider()
        assert "XAIProvider" in repr(provider)
        assert "grok-3-mini" in repr(provider)
