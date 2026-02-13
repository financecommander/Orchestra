"""Tests for Provider modules."""

import pytest
from orchestra.providers.base import BaseProvider
from orchestra.providers.llm import LLMProvider
from orchestra.core.agent import Agent
from orchestra.core.task import Task
from orchestra.core.context import Context


class MockProvider(BaseProvider):
    """Mock provider for testing."""
    
    def execute(self, agent: Agent, task: Task, context: Context):
        """Execute a task."""
        return {"status": "completed", "mock": True}
    
    def validate_config(self) -> bool:
        """Validate configuration."""
        return True


class TestBaseProvider:
    """Test cases for BaseProvider class."""
    
    def test_base_provider_creation(self):
        """Test basic provider creation."""
        provider = MockProvider()
        assert provider.config == {}
    
    def test_base_provider_with_config(self):
        """Test provider creation with config."""
        config = {"key": "value"}
        provider = MockProvider(config=config)
        assert provider.config == config
    
    def test_base_provider_execute(self):
        """Test provider execute method."""
        provider = MockProvider()
        agent = Agent(name="test", provider="mock")
        task = Task(name="task1", description="test")
        context = Context()
        
        result = provider.execute(agent, task, context)
        assert result["status"] == "completed"
        assert result["mock"] is True
    
    def test_base_provider_repr(self):
        """Test provider string representation."""
        provider = MockProvider()
        assert "MockProvider" in repr(provider)


class TestLLMProvider:
    """Test cases for LLMProvider class."""
    
    def test_llm_provider_creation(self):
        """Test basic LLM provider creation."""
        provider = LLMProvider()
        assert provider.model == "gpt-4"
        assert provider.temperature == 0.7
        assert provider.max_tokens == 1000
        assert provider.provider_type == "openai"
    
    def test_llm_provider_with_config(self):
        """Test LLM provider creation with config."""
        config = {
            "model": "gpt-3.5-turbo",
            "temperature": 0.5,
            "max_tokens": 500,
            "provider_type": "anthropic",
            "api_key": "test_key"
        }
        provider = LLMProvider(config=config)
        
        assert provider.model == "gpt-3.5-turbo"
        assert provider.temperature == 0.5
        assert provider.max_tokens == 500
        assert provider.provider_type == "anthropic"
        assert provider.api_key == "test_key"
    
    def test_llm_provider_execute(self):
        """Test LLM provider execute method."""
        provider = LLMProvider()
        agent = Agent(
            name="test_agent",
            provider="llm",
            system_prompt="You are helpful"
        )
        task = Task(
            name="task1",
            description="Generate a summary",
            inputs={"text": "Sample text"}
        )
        context = Context()
        context.set("key", "value")
        
        result = provider.execute(agent, task, context)
        
        assert result["status"] == "completed"
        assert result["agent"] == "test_agent"
        assert result["task"] == "task1"
        assert "prompt" in result
        assert "response" in result
        assert result["model"] == "gpt-4"
    
    def test_llm_provider_build_prompt(self):
        """Test prompt building."""
        provider = LLMProvider()
        agent = Agent(
            name="test",
            provider="llm",
            system_prompt="System message"
        )
        task = Task(
            name="task1",
            description="Task description",
            inputs={"input": "value"}
        )
        context = Context()
        context.set("ctx_key", "ctx_value")
        
        prompt = provider._build_prompt(agent, task, context)
        
        assert "System message" in prompt
        assert "Task description" in prompt
        assert "input" in prompt
        assert "ctx_key" in prompt
    
    def test_llm_provider_validate_config(self):
        """Test LLM provider config validation."""
        # Valid config
        provider = LLMProvider(config={"model": "gpt-4"})
        assert provider.validate_config() is True
        
        # Invalid model
        provider = LLMProvider(config={"model": ""})
        with pytest.raises(ValueError, match="Model name is required"):
            provider.validate_config()
        
        # Invalid temperature
        provider = LLMProvider(config={"temperature": 3.0})
        with pytest.raises(ValueError, match="Temperature must be between"):
            provider.validate_config()
        
        # Invalid max_tokens
        provider = LLMProvider(config={"max_tokens": 0})
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            provider.validate_config()
    
    def test_llm_provider_repr(self):
        """Test LLM provider string representation."""
        provider = LLMProvider(config={
            "model": "gpt-3.5-turbo",
            "provider_type": "openai"
        })
        
        repr_str = repr(provider)
        assert "LLMProvider" in repr_str
        assert "gpt-3.5-turbo" in repr_str
        assert "openai" in repr_str
