"""Tests for agent provider modules."""

import os
import pytest
from unittest.mock import patch
from orchestra.providers.agents.anthropic import AnthropicProvider
from orchestra.providers.agents.openai import OpenAIProvider
from orchestra.providers.agents.xai import XAIProvider
from orchestra.providers.agents.triton import TritonProvider
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
        assert provider.model == "grok-beta"
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
        assert "grok-beta" in repr(provider)


class TestTritonProvider:
    """Test cases for TritonProvider."""

    def test_triton_provider_creation(self):
        """Test basic provider creation."""
        provider = TritonProvider()
        assert provider.model == "triton-ternary-coder-8b"
        assert provider.temperature == 0.7
        assert provider.max_tokens == 4096
        assert provider.max_retries == 3

    def test_triton_provider_with_config(self):
        """Test provider creation with config."""
        config = {
            "model": "triton-ternary-coder-70b",
            "temperature": 0.4,
            "max_tokens": 2048,
            "max_retries": 5,
        }
        provider = TritonProvider(config=config)
        assert provider.model == "triton-ternary-coder-70b"
        assert provider.temperature == 0.4
        assert provider.max_tokens == 2048
        assert provider.max_retries == 5

    @patch.dict(os.environ, {"TRITON_API_KEY": "test-key-triton"})
    def test_triton_provider_env_api_key(self):
        """Test that API key is loaded from environment."""
        provider = TritonProvider()
        assert provider.api_key == "test-key-triton"

    @patch.dict(os.environ, {"TRITON_BASE_URL": "http://triton.example.com:8000"})
    def test_triton_provider_env_base_url(self):
        """Test that base URL is loaded from environment."""
        provider = TritonProvider()
        assert provider.base_url == "http://triton.example.com:8000"

    def test_triton_provider_execute(self):
        """Test provider execute method."""
        provider = TritonProvider()
        agent = Agent(
            name="test_agent",
            provider="triton",
            system_prompt="You are a guardian.",
        )
        task = Task(name="task1", description="Review this code")
        context = Context()

        result = provider.execute(agent, task, context)

        assert result["status"] == "completed"
        assert result["agent"] == "test_agent"
        assert result["task"] == "task1"
        assert result["provider"] == "triton"
        assert "response" in result

    def test_triton_provider_execute_with_context(self):
        """Test execute with populated context."""
        provider = TritonProvider()
        agent = Agent(name="reviewer", provider="triton", system_prompt="Review code.")
        task = Task(name="review", description="Review PR", inputs={"pr_id": "42"})
        context = Context()
        context.set("repo", "Orchestra")

        result = provider.execute(agent, task, context)

        assert result["status"] == "completed"
        assert result["provider"] == "triton"

    def test_triton_provider_build_messages_with_system_prompt(self):
        """Test message building includes system prompt."""
        provider = TritonProvider()
        agent = Agent(
            name="test", provider="triton", system_prompt="You are a guardian."
        )
        task = Task(name="task1", description="Test task", inputs={"key": "value"})
        context = Context()
        context.set("context_key", "context_value")

        messages = provider._build_messages(agent, task, context)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a guardian."
        assert messages[1]["role"] == "user"
        assert "Test task" in messages[1]["content"]
        assert "key" in messages[1]["content"]
        assert "context_key" in messages[1]["content"]

    def test_triton_provider_build_messages_no_system_prompt(self):
        """Test message building without system prompt."""
        provider = TritonProvider()
        agent = Agent(name="test", provider="triton")
        task = Task(name="task1", description="Test task")
        context = Context()

        messages = provider._build_messages(agent, task, context)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    def test_triton_provider_retry_logic(self):
        """Test retry logic with exponential backoff."""
        provider = TritonProvider(config={"max_retries": 3, "retry_delay": 0.01})

        call_count = 0

        def mock_call_triton(messages):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Triton API error")
            return "Success"

        provider._call_triton = mock_call_triton

        result = provider._call_triton_with_retry(
            [{"role": "user", "content": "test"}]
        )
        assert result == "Success"
        assert call_count == 3

    def test_triton_provider_retry_exhausted(self):
        """Test that retry raises error when exhausted."""
        provider = TritonProvider(config={"max_retries": 2, "retry_delay": 0.01})

        def mock_call_triton(messages):
            raise Exception("Triton API error")

        provider._call_triton = mock_call_triton

        with pytest.raises(RuntimeError, match="Failed to call Triton API"):
            provider._call_triton_with_retry([{"role": "user", "content": "test"}])

    def test_triton_provider_validate_config(self):
        """Test configuration validation."""
        provider = TritonProvider()
        assert provider.validate_config() is True

        provider.temperature = 3.0
        with pytest.raises(ValueError, match="Temperature must be between"):
            provider.validate_config()

        provider.temperature = 0.7
        provider.max_tokens = 0
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            provider.validate_config()

        provider.max_tokens = 4096
        provider.max_retries = 0
        with pytest.raises(ValueError, match="max_retries must be at least 1"):
            provider.validate_config()

    def test_triton_provider_repr(self):
        """Test string representation."""
        provider = TritonProvider()
        assert "TritonProvider" in repr(provider)
        assert "triton-ternary-coder-8b" in repr(provider)

    def test_triton_provider_exported_from_agents_package(self):
        """Test that TritonProvider is exported from the agents package."""
        from orchestra.providers.agents import TritonProvider as TP
        assert TP is TritonProvider
