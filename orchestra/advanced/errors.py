"""
Orchestra DSL - Error Handling Patterns
Version 2.0

Implements resilient failure management:
- Retry with configurable strategies (fixed, exponential, linear)
- Circuit breaker pattern for API protection
- Timeout handling (soft and hard)
- Graceful degradation chains
- Decorator utilities
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional
from enum import Enum
from functools import wraps
import time
import asyncio


# ============================================================================
# ERROR HANDLING TYPES
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


# ============================================================================
# EXCEPTIONS
# ============================================================================

class OrchestraError(Exception):
    """Base Orchestra exception"""
    pass


class CircuitBreakerOpenError(OrchestraError):
    """Circuit breaker is open"""
    pass


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================

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


# ============================================================================
# ERROR HANDLER
# ============================================================================

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
