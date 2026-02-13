"""Agent module for Orchestra DSL."""

from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class Agent:
    """Represents an agent in the Orchestra DSL.
    
    An agent is an autonomous entity that can execute tasks using
    a specified provider (e.g., LLM, API, custom function).
    """
    
    name: str
    provider: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    system_prompt: Optional[str] = None
    tools: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate agent configuration."""
        if not self.name:
            raise ValueError("Agent name cannot be empty")
    
    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a task with this agent.
        
        Args:
            task: The task description or instruction
            context: Optional context for task execution
            
        Returns:
            The result of task execution
        """
        # This will be implemented by the compiler/executor
        raise NotImplementedError("Agent execution requires a compiler/executor")
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"Agent(name='{self.name}', provider='{self.provider}')"
