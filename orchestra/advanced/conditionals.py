"""
Orchestra DSL - Conditional Execution Engine
Version 2.0

Implements dynamic workflow branching:
- If/then/else execution
- Guard clauses for validation
- Pattern matching
- Parallel conditional execution
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import asyncio


# ============================================================================
# CONDITIONAL TYPES
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


# ============================================================================
# EXCEPTIONS
# ============================================================================

class GuardViolationError(Exception):
    """Guard clause violated"""
    pass


class MatchError(Exception):
    """Pattern match failed"""
    pass


# ============================================================================
# CONDITIONAL EXECUTOR
# ============================================================================

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
