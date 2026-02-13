"""Tests for Agent module."""

import pytest
from orchestra.core.agent import Agent


class TestAgent:
    """Test cases for Agent class."""

    def test_agent_creation(self):
        """Test basic agent creation."""
        agent = Agent(name="test_agent", provider="llm")
        assert agent.name == "test_agent"
        assert agent.provider == "llm"
        assert agent.config == {}
        assert agent.tools == []

    def test_agent_with_config(self):
        """Test agent creation with configuration."""
        config = {"model": "gpt-4", "temperature": 0.7}
        agent = Agent(
            name="configured_agent",
            provider="openai",
            config=config,
            system_prompt="You are a helpful assistant",
        )
        assert agent.name == "configured_agent"
        assert agent.config == config
        assert agent.system_prompt == "You are a helpful assistant"

    def test_agent_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            Agent(name="")

    def test_agent_repr(self):
        """Test agent string representation."""
        agent = Agent(name="test", provider="llm")
        assert "test" in repr(agent)
        assert "llm" in repr(agent)

    def test_agent_execute_not_implemented(self):
        """Test that execute raises NotImplementedError without executor."""
        agent = Agent(name="test", provider="llm")
        with pytest.raises(NotImplementedError):
            agent.execute("test task")
