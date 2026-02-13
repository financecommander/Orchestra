"""Context module for Orchestra DSL."""

from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Context:
    """Execution context for Orchestra workflows.
    
    The context holds shared state, variables, and execution metadata
    that can be accessed by agents and tasks during workflow execution.
    """
    
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_id: Optional[str] = None
    start_time: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize context with default values."""
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.execution_id is None:
            self.execution_id = f"exec_{self.start_time.strftime('%Y%m%d_%H%M%S')}"
    
    def set(self, key: str, value: Any) -> 'Context':
        """Set a variable in the context.
        
        Args:
            key: Variable name
            value: Variable value
            
        Returns:
            Self for method chaining
        """
        self.variables[key] = value
        return self
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a variable from the context.
        
        Args:
            key: Variable name
            default: Default value if key not found
            
        Returns:
            Variable value or default
        """
        return self.variables.get(key, default)
    
    def has(self, key: str) -> bool:
        """Check if a variable exists in the context.
        
        Args:
            key: Variable name
            
        Returns:
            True if variable exists
        """
        return key in self.variables
    
    def update(self, variables: Dict[str, Any]) -> 'Context':
        """Update multiple variables in the context.
        
        Args:
            variables: Dictionary of variables to update
            
        Returns:
            Self for method chaining
        """
        self.variables.update(variables)
        return self
    
    def clear(self) -> 'Context':
        """Clear all variables from the context.
        
        Returns:
            Self for method chaining
        """
        self.variables.clear()
        return self
    
    def __repr__(self) -> str:
        """String representation of the context."""
        return f"Context(execution_id='{self.execution_id}', variables={len(self.variables)})"
