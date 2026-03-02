"""
Orchestra DSL - Advanced Features Implementation
Version 2.0 - March 2, 2026

Implements:
- Advanced routing syntax
- Conditional execution
- Error handling patterns
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum
import time
import asyncio
from functools import wraps


# ============================================================================
# ROUTING TYPES
# ============================================================================

class RoutingStrategy(Enum):
    """Agent routing strategies"""
    BEST_FOR = "best_for"
    CASCADE = "cascade"
    ROUND_ROBIN = "round_robin"
    LOAD_BALANCE = "load_balance"
    CHEAPEST_ABOVE = "cheapest_above"
    DYNAMIC_SELECT = "dynamic_select"


@dataclass
class RoutingCriteria:
    """Criteria for agent selection"""
    complexity: Optional[float] = None
    max_cost: Optional[float] = None
    quality: Optional[str] = None
    max_latency: Optional[float] = None
    min_quality: Optional[float] = None


@dataclass
class CascadeRoute:
    """Cascade routing configuration"""
    try_agent: str
    fallback: Optional[str] = None
    last_resort: Optional[str] = None
    

@dataclass
class BalanceRoute:
    """Load balancing configuration"""
    strategy: str = "round_robin"  # or "least_loaded", "random"
    pool: List[str] = field(default_factory=list)
    max_concurrent: int = 10


@dataclass
class BudgetConstraints:
    """Budget management"""
    per_task: Optional[float] = None
    hourly_limit: Optional[float] = None
    alert_at: Optional[float] = None  # Percentage
    

class AgentRouter:
    """Advanced agent routing engine"""
    
    def __init__(self):
        self.performance_history = {}
        self.current_loads = {}
        self.hourly_spend = 0.0
        self.last_reset = time.time()
        
    async def route(
        self,
        strategy: RoutingStrategy,
        criteria: Optional[RoutingCriteria] = None,
        cascade: Optional[CascadeRoute] = None,
        balance: Optional[BalanceRoute] = None,
        budget: Optional[BudgetConstraints] = None
    ) -> str:
        """Route task to optimal agent"""
        
        # Check budget first
        if budget:
            self._check_budget(budget)
        
        # Route based on strategy
        if strategy == RoutingStrategy.BEST_FOR:
            return self._route_best_for(criteria)
        elif strategy == RoutingStrategy.CASCADE:
            return await self._route_cascade(cascade)
        elif strategy == RoutingStrategy.ROUND_ROBIN:
            return self._route_round_robin(balance.pool)
        elif strategy == RoutingStrategy.LOAD_BALANCE:
            return self._route_load_balance(balance)
        elif strategy == RoutingStrategy.CHEAPEST_ABOVE:
            return self._route_cheapest_above(criteria)
        elif strategy == RoutingStrategy.DYNAMIC_SELECT:
            return self._route_dynamic(criteria)
        else:
            raise ValueError(f"Unknown routing strategy: {strategy}")
    
    def _route_best_for(self, criteria: RoutingCriteria) -> str:
        """Select best agent for criteria"""
        # Simplified - real implementation would use cost tables
        if criteria.complexity and criteria.complexity < 0.3:
            return "drone_ultra_cheap"
        elif criteria.max_cost and criteria.max_cost < 0.005:
            return "drone_cheap"
        elif criteria.quality == "premium":
            return "guardian_claude"
        else:
            return "hydra_financial"
    
    async def _route_cascade(self, cascade: CascadeRoute) -> str:
        """Try agents in sequence"""
        # Try primary first
        try:
            # In real implementation, would actually try the agent
            return cascade.try_agent
        except Exception:
            if cascade.fallback:
                return cascade.fallback
            elif cascade.last_resort:
                return cascade.last_resort
            raise
    
    def _route_round_robin(self, pool: List[str]) -> str:
        """Round-robin selection"""
        if not hasattr(self, '_rr_index'):
            self._rr_index = 0
        agent = pool[self._rr_index % len(pool)]
        self._rr_index += 1
        return agent
    
    def _route_load_balance(self, balance: BalanceRoute) -> str:
        """Select least loaded agent"""
        if balance.strategy == "round_robin":
            return self._route_round_robin(balance.pool)
        elif balance.strategy == "least_loaded":
            # Find agent with lowest current load
            loads = {agent: self.current_loads.get(agent, 0) for agent in balance.pool}
            return min(loads, key=loads.get)
        elif balance.strategy == "random":
            import random
            return random.choice(balance.pool)
        else:
            return balance.pool[0]
    
    def _route_cheapest_above(self, criteria: RoutingCriteria) -> str:
        """Cheapest agent above quality threshold"""
        # Simplified cost/quality mapping
        agents = [
            ("drone_ultra_cheap", 0.001, 0.75),
            ("hydra_financial", 0.003, 0.85),
            ("ultra_reasoning", 0.008, 0.90),
            ("guardian_claude", 0.015, 0.95),
        ]
        
        threshold = criteria.min_quality or 0.8
        valid = [(name, cost) for name, cost, quality in agents if quality >= threshold]
        
        if not valid:
            return "guardian_claude"  # Fallback to premium
        
        return min(valid, key=lambda x: x[1])[0]
    
    def _route_dynamic(self, criteria: RoutingCriteria) -> str:
        """Dynamic selection based on performance history"""
        # Use performance metrics to select best agent
        # Simplified - would use real metrics
        return "ultra_reasoning"
    
    def _check_budget(self, budget: BudgetConstraints):
        """Verify budget constraints"""
        # Reset hourly counter if needed
        if time.time() - self.last_reset > 3600:
            self.hourly_spend = 0.0
            self.last_reset = time.time()
        
        # Check limits
        if budget.hourly_limit and self.hourly_spend >= budget.hourly_limit:
            raise BudgetExceededError(f"Hourly limit of ${budget.hourly_limit} exceeded")
        
        # Check alert threshold
        if budget.alert_at and budget.hourly_limit:
            threshold = budget.hourly_limit * (budget.alert_at / 100.0)
            if self.hourly_spend >= threshold:
                print(f"⚠️  Budget alert: ${self.hourly_spend:.2f} / ${budget.hourly_limit:.2f}")


# ============================================================================
# CONDITIONAL EXECUTION
# ============================================================================

@dataclass
class Condition:
    """Conditional execution branch"""
    predicate: Callable[[], bool]
    action: Callable[[], Any]
    

@dataclass
class GuardClause:
    """Guard clause for validation"""
    requirement: Callable[[], bool]
    error_message: str
    

class ConditionalExecutor:
    """Execute conditional workflows"""
    
    def __init__(self, context: Dict[str, Any]):
        self.context = context
        
    async def if_then_else(
        self,
        condition: bool,
        then_block: Callable,
        else_block: Optional[Callable] = None
    ) -> Any:
        """Execute if/then/else"""
        if condition:
            return await self._execute(then_block)
        elif else_block:
            return await self._execute(else_block)
        return None
    
    async def guard(self, guards: List[GuardClause]):
        """Execute guard clauses"""
        for guard in guards:
            if not guard.requirement():
                raise GuardViolationError(guard.error_message)
    
    async def match(self, value: Any, cases: Dict[Any, Callable], default: Optional[Callable] = None) -> Any:
        """Pattern matching"""
        if value in cases:
            return await self._execute(cases[value])
        elif default:
            return await self._execute(default)
        raise MatchError(f"No case matched: {value}")
    
    async def parallel_conditional(self, conditions: List[Condition]) -> List[Any]:
        """Execute multiple conditions in parallel"""
        tasks = []
        for condition in conditions:
            if condition.predicate():
                tasks.append(self._execute(condition.action))
        
        if tasks:
            return await asyncio.gather(*tasks)
        return []
    
    async def _execute(self, func: Callable) -> Any:
        """Execute function (async or sync)"""
        if asyncio.iscoroutinefunction(func):
            return await func()
        else:
            return func()


# ============================================================================
# ERROR HANDLING
# ============================================================================

class RetryStrategy(Enum):
    """Retry strategies"""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


@dataclass
class RetryConfig:
    """Retry configuration"""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    multiplier: float = 2.0
    jitter: float = 0.1


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    timeout: float = 60.0
    half_open_after: float = 30.0
    

@dataclass
class TimeoutConfig:
    """Timeout configuration"""
    soft: Optional[float] = None
    hard: Optional[float] = None
    

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for error protection"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        
    async def execute(self, func: Callable) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            # Check if ready to half-open
            if time.time() - self.last_failure_time > self.config.half_open_after:
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            result = await self._execute(func)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
    
    async def _execute(self, func: Callable) -> Any:
        """Execute function"""
        if asyncio.iscoroutinefunction(func):
            return await func()
        else:
            return func()


class ErrorHandler:
    """Advanced error handling"""
    
    @staticmethod
    async def retry(
        func: Callable,
        config: RetryConfig = RetryConfig()
    ) -> Any:
        """Retry function with backoff"""
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func()
                else:
                    return func()
            except Exception as e:
                last_exception = e
                
                if attempt < config.max_attempts - 1:
                    delay = ErrorHandler._calculate_delay(attempt, config)
                    await asyncio.sleep(delay)
        
        raise last_exception
    
    @staticmethod
    def _calculate_delay(attempt: int, config: RetryConfig) -> float:
        """Calculate retry delay"""
        if config.strategy == RetryStrategy.FIXED:
            delay = config.initial_delay
        elif config.strategy == RetryStrategy.LINEAR:
            delay = config.initial_delay * (attempt + 1)
        else:  # EXPONENTIAL
            delay = min(
                config.initial_delay * (config.multiplier ** attempt),
                config.max_delay
            )
        
        # Add jitter
        import random
        jitter = delay * config.jitter * random.uniform(-1, 1)
        return delay + jitter
    
    @staticmethod
    async def with_timeout(
        func: Callable,
        config: TimeoutConfig
    ) -> Any:
        """Execute with timeout"""
        if config.hard:
            try:
                return await asyncio.wait_for(
                    func() if asyncio.iscoroutinefunction(func) else asyncio.to_thread(func),
                    timeout=config.hard
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Operation exceeded {config.hard}s timeout")
        else:
            if asyncio.iscoroutinefunction(func):
                return await func()
            else:
                return func()
    
    @staticmethod
    async def graceful_degradation(
        primary: Callable,
        fallbacks: List[Callable]
    ) -> Any:
        """Try primary, fall back through chain on failure"""
        try:
            return await ErrorHandler._execute(primary)
        except Exception:
            for fallback in fallbacks:
                try:
                    return await ErrorHandler._execute(fallback)
                except Exception:
                    continue
            raise
    
    @staticmethod
    async def _execute(func: Callable) -> Any:
        """Execute function"""
        if asyncio.iscoroutinefunction(func):
            return await func()
        else:
            return func()


# ============================================================================
# EXCEPTIONS
# ============================================================================

class OrchestraError(Exception):
    """Base Orchestra exception"""
    pass


class BudgetExceededError(OrchestraError):
    """Budget limit exceeded"""
    pass


class GuardViolationError(OrchestraError):
    """Guard clause violated"""
    pass


class MatchError(OrchestraError):
    """Pattern match failed"""
    pass


class CircuitBreakerOpenError(OrchestraError):
    """Circuit breaker is open"""
    pass


# ============================================================================
# DECORATORS
# ============================================================================

def with_retry(config: RetryConfig = RetryConfig()):
    """Decorator for automatic retry"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await ErrorHandler.retry(lambda: func(*args, **kwargs), config)
        return wrapper
    return decorator


def with_circuit_breaker(config: CircuitBreakerConfig):
    """Decorator for circuit breaker"""
    breaker = CircuitBreaker(config)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.execute(lambda: func(*args, **kwargs))
        return wrapper
    return decorator


def with_timeout(config: TimeoutConfig):
    """Decorator for timeout"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await ErrorHandler.with_timeout(lambda: func(*args, **kwargs), config)
        return wrapper
    return decorator


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

async def example_advanced_routing():
    """Example: Advanced routing"""
    router = AgentRouter()
    
    # Best-for routing
    agent = await router.route(
        strategy=RoutingStrategy.BEST_FOR,
        criteria=RoutingCriteria(complexity=0.5, max_cost=0.01, quality="mid")
    )
    print(f"Selected agent: {agent}")
    
    # Cascade routing
    agent = await router.route(
        strategy=RoutingStrategy.CASCADE,
        cascade=CascadeRoute(
            try_agent="ultra_reasoning",
            fallback="guardian_claude",
            last_resort="hydra_financial"
        )
    )
    print(f"Cascade agent: {agent}")
    
    # Load balancing
    agent = await router.route(
        strategy=RoutingStrategy.LOAD_BALANCE,
        balance=BalanceRoute(
            strategy="round_robin",
            pool=["drone_1", "drone_2", "drone_3"],
            max_concurrent=10
        )
    )
    print(f"Balanced agent: {agent}")


async def example_conditionals():
    """Example: Conditional execution"""
    context = {"loan_amount": 50000, "country": "US"}
    executor = ConditionalExecutor(context)
    
    # If/then/else
    result = await executor.if_then_else(
        condition=context["loan_amount"] > 100000,
        then_block=lambda: "premium_analysis",
        else_block=lambda: "standard_analysis"
    )
    print(f"Analysis type: {result}")
    
    # Guard clauses
    try:
        await executor.guard([
            GuardClause(lambda: context["loan_amount"] > 0, "Amount must be positive"),
            GuardClause(lambda: context["loan_amount"] < 1000000, "Amount too large")
        ])
        print("Guards passed")
    except GuardViolationError as e:
        print(f"Guard failed: {e}")
    
    # Pattern matching
    result = await executor.match(
        value=context["country"],
        cases={
            "US": lambda: "us_compliance",
            "EU": lambda: "gdpr_compliance",
            "UK": lambda: "uk_compliance"
        },
        default=lambda: "international_compliance"
    )
    print(f"Compliance: {result}")


async def example_error_handling():
    """Example: Error handling"""
    
    # Retry with exponential backoff
    @with_retry(RetryConfig(max_attempts=3, initial_delay=1.0))
    async def flaky_operation():
        import random
        if random.random() < 0.7:  # 70% failure rate
            raise Exception("Temporary failure")
        return "Success!"
    
    try:
        result = await flaky_operation()
        print(f"Retry result: {result}")
    except Exception as e:
        print(f"Failed after retries: {e}")
    
    # Circuit breaker
    @with_circuit_breaker(CircuitBreakerConfig(failure_threshold=3, timeout=60.0))
    async def protected_operation():
        # Simulate operation
        return "Protected result"
    
    result = await protected_operation()
    print(f"Circuit breaker result: {result}")
    
    # Graceful degradation
    async def primary_analysis():
        raise Exception("Primary failed")
    
    async def fallback_analysis():
        return "Fallback result"
    
    result = await ErrorHandler.graceful_degradation(
        primary=primary_analysis,
        fallbacks=[fallback_analysis]
    )
    print(f"Degradation result: {result}")


if __name__ == "__main__":
    print("Orchestra Advanced Features v2.0")
    print("=" * 50)
    
    asyncio.run(example_advanced_routing())
    print()
    asyncio.run(example_conditionals())
    print()
    asyncio.run(example_error_handling())
