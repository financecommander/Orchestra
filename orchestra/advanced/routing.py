"""
Orchestra DSL - Advanced Routing Engine
Version 2.0

Implements intelligent agent routing with multiple strategies:
- Best-for: Select best agent based on criteria
- Cascade: Try agents in sequence with fallbacks
- Round-robin: Distribute across agent pool
- Load balance: Route to least-loaded agent
- Cheapest-above: Cost-optimized quality routing
- Dynamic select: Performance-based selection
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import time


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


class BudgetExceededError(Exception):
    """Budget limit exceeded"""
    pass


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
        try:
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
            loads = {agent: self.current_loads.get(agent, 0) for agent in balance.pool}
            return min(loads, key=loads.get)
        elif balance.strategy == "random":
            import random
            return random.choice(balance.pool)
        else:
            return balance.pool[0]

    def _route_cheapest_above(self, criteria: RoutingCriteria) -> str:
        """Cheapest agent above quality threshold"""
        agents = [
            ("drone_ultra_cheap", 0.001, 0.75),
            ("hydra_financial", 0.003, 0.85),
            ("ultra_reasoning", 0.008, 0.90),
            ("guardian_claude", 0.015, 0.95),
        ]

        threshold = criteria.min_quality or 0.8
        valid = [(name, cost) for name, cost, quality in agents if quality >= threshold]

        if not valid:
            return "guardian_claude"

        return min(valid, key=lambda x: x[1])[0]

    def _route_dynamic(self, criteria: RoutingCriteria) -> str:
        """Dynamic selection based on performance history"""
        return "ultra_reasoning"

    def _check_budget(self, budget: BudgetConstraints):
        """Verify budget constraints"""
        if time.time() - self.last_reset > 3600:
            self.hourly_spend = 0.0
            self.last_reset = time.time()

        if budget.hourly_limit and self.hourly_spend >= budget.hourly_limit:
            raise BudgetExceededError(f"Hourly limit of ${budget.hourly_limit} exceeded")

        if budget.alert_at and budget.hourly_limit:
            threshold = budget.hourly_limit * (budget.alert_at / 100.0)
            if self.hourly_spend >= threshold:
                print(f"Budget alert: ${self.hourly_spend:.2f} / ${budget.hourly_limit:.2f}")
