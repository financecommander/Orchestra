"""Orchestra - Python DSL for multi-agent orchestration."""

__version__ = "2.0.0"

# Core v1.x
from orchestra.core.agent import Agent
from orchestra.core.task import Task
from orchestra.core.workflow import Workflow
from orchestra.core.context import Context

# Advanced v2.0 - Routing
from orchestra.advanced.routing import (
    AgentRouter,
    RoutingStrategy,
    RoutingCriteria,
    CascadeRoute,
    BalanceRoute,
    BudgetConstraints,
    BudgetExceededError,
)

# Advanced v2.0 - Conditionals
from orchestra.advanced.conditionals import (
    ConditionalExecutor,
    Condition,
    GuardClause,
    GuardViolationError,
    MatchError,
)

# Advanced v2.0 - Error Handling
from orchestra.advanced.errors import (
    ErrorHandler,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    CircuitBreakerOpenError,
    RetryStrategy,
    RetryConfig,
    TimeoutConfig,
    OrchestraError,
    with_retry,
    with_circuit_breaker,
    with_timeout,
)

__all__ = [
    # Core
    "Agent",
    "Task",
    "Workflow",
    "Context",
    # Routing
    "AgentRouter",
    "RoutingStrategy",
    "RoutingCriteria",
    "CascadeRoute",
    "BalanceRoute",
    "BudgetConstraints",
    "BudgetExceededError",
    # Conditionals
    "ConditionalExecutor",
    "Condition",
    "GuardClause",
    "GuardViolationError",
    "MatchError",
    # Error Handling
    "ErrorHandler",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerState",
    "CircuitBreakerOpenError",
    "RetryStrategy",
    "RetryConfig",
    "TimeoutConfig",
    "OrchestraError",
    # Decorators
    "with_retry",
    "with_circuit_breaker",
    "with_timeout",
]
