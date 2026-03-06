"""AST node definitions for the Orchestra .orc DSL.

Every construct in an .orc file maps to one of these nodes.
The parser builds a tree of these nodes; the compiler bridge
converts them into the existing Workflow/Task/Agent objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Union


# ── Expressions ──────────────────────────────────────────────────────

@dataclass
class Expression:
    """A simple expression (used in guards, conditionals, asserts).

    We store these semi-opaquely: the raw text plus a parsed structure
    where possible.  Full expression evaluation happens at runtime; the
    parser only needs to capture the structure.
    """
    raw: str
    left: Optional[str] = None
    operator: Optional[str] = None
    right: Optional[Any] = None

    def __repr__(self) -> str:
        return f"Expr({self.raw})"


# ── Property assignment ─────────────────────────────────────────────

@dataclass
class PropertyAssignment:
    """key: value inside a block (e.g., ``strategy: exponential_backoff``)."""
    key: str
    value: Any            # str | float | bool | list | dict | Expression
    line: int = 0


# ── Agent references ────────────────────────────────────────────────

@dataclass
class AgentRef:
    """Simple named agent reference: ``agent: guardian_claude``."""
    name: str


@dataclass
class CascadeAgent:
    """``agent: cascade [ try: …, fallback: …, last_resort: … ]``"""
    try_agent: str
    fallback: Optional[str] = None
    last_resort: Optional[str] = None


@dataclass
class BalanceAgent:
    """``agent: balance { strategy: …, pool: […], max_concurrent: N }``"""
    strategy: str
    pool: List[str] = field(default_factory=list)
    max_concurrent: Optional[int] = None


@dataclass
class RouteAgent:
    """``agent: route { if … then …; else … }``"""
    rules: List[PropertyAssignment] = field(default_factory=list)
    default: Optional[str] = None


@dataclass
class SelectAgent:
    """``agent: select { metric: …, candidates: […], … }``"""
    metric: Optional[str] = None
    timeframe: Optional[str] = None
    optimize_for: List[str] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)
    candidates: List[str] = field(default_factory=list)
    fallback: Optional[str] = None


@dataclass
class TritonAgent:
    """``agent: triton_ternary("model-name")``"""
    model_name: str


@dataclass
class CheapestAboveAgent:
    """``agent: cheapest_above(quality_threshold: 0.85)``"""
    quality_threshold: float = 0.8


@dataclass
class BestForAgent:
    """``agent: best_for(complexity: …, max_cost: …, quality: …)``"""
    properties: dict = field(default_factory=dict)


AgentType = Union[
    AgentRef, CascadeAgent, BalanceAgent, RouteAgent,
    SelectAgent, TritonAgent, CheapestAboveAgent, BestForAgent,
]


# ── Timeout ──────────────────────────────────────────────────────────

@dataclass
class TimeoutNode:
    """``timeout { soft: …, hard: … }`` or ``timeout: N``."""
    soft: Optional[float] = None
    hard: Optional[float] = None
    on_soft_timeout: Optional[Any] = None
    on_hard_timeout: Optional[Any] = None
    on_timeout: Optional[Any] = None


# ── Validate output ──────────────────────────────────────────────────

@dataclass
class ValidateOutputNode:
    """``validate_output { assert: … }``"""
    assertions: List[Expression] = field(default_factory=list)
    on_validation_failure: Optional[Any] = None


# ── On-partial-failure ───────────────────────────────────────────────

@dataclass
class OnPartialFailureNode:
    """``on_partial_failure { strategy: continue, min_success_rate: … }``"""
    strategy: str = "continue"
    min_success_rate: Optional[float] = None
    on_below_threshold: Optional[Any] = None


# ── Steps ────────────────────────────────────────────────────────────

@dataclass
class StepNode:
    """``step name { agent: … task: "…" }``"""
    name: str
    agent: Optional[AgentType] = None
    model: Optional[str] = None
    task: Optional[str] = None
    timeout: Optional[TimeoutNode] = None
    validate_output: Optional[ValidateOutputNode] = None
    properties: List[PropertyAssignment] = field(default_factory=list)
    body: List[Any] = field(default_factory=list)   # nested nodes (try blocks etc.)
    line: int = 0


# ── Parallel ─────────────────────────────────────────────────────────

@dataclass
class ParallelNode:
    """``parallel { step … step … }``"""
    steps: List[StepNode] = field(default_factory=list)
    on_partial_failure: Optional[OnPartialFailureNode] = None
    line: int = 0


# ── Conditionals ─────────────────────────────────────────────────────

@dataclass
class IfNode:
    """``if expr { … } else if expr { … } else { … }``"""
    condition: Expression
    body: List[Any] = field(default_factory=list)
    elif_branches: List["IfNode"] = field(default_factory=list)
    else_body: List[Any] = field(default_factory=list)
    line: int = 0


@dataclass
class MatchCase:
    """``case "value" => { … }``"""
    value: str                    # the literal to match or "default"
    body: List[Any] = field(default_factory=list)
    line: int = 0


@dataclass
class MatchNode:
    """``match expr { case … case … default … }``"""
    expression: str               # e.g. "input.source_type"
    cases: List[MatchCase] = field(default_factory=list)
    default: Optional[MatchCase] = None
    line: int = 0


# ── For-each ─────────────────────────────────────────────────────────

@dataclass
class ForEachNode:
    """``for each item in collection { … }``"""
    variable: str
    collection: str
    body: List[Any] = field(default_factory=list)
    line: int = 0


# ── Guard ────────────────────────────────────────────────────────────

@dataclass
class GuardNode:
    """``guard { require: expr … on_violation: … }``"""
    requirements: List[Expression] = field(default_factory=list)
    on_violation: Optional[str] = None
    line: int = 0


# ── Budget ───────────────────────────────────────────────────────────

@dataclass
class BudgetNode:
    """``budget { per_task: …, hourly_limit: …, alert_at: … }``"""
    per_task: Optional[float] = None
    hourly_limit: Optional[float] = None
    alert_at: Optional[float] = None
    line: int = 0


# ── Circuit breaker ──────────────────────────────────────────────────

@dataclass
class CircuitBreakerNode:
    """``circuit_breaker { failure_threshold: …, timeout: … }``"""
    failure_threshold: Optional[int] = None
    timeout: Optional[float] = None
    half_open_after: Optional[float] = None
    on_open: Optional[Any] = None
    line: int = 0


# ── Quality gate ─────────────────────────────────────────────────────

@dataclass
class QualityGateNode:
    """``quality_gate { metrics: { … }, on_failure { … } }``"""
    metrics: dict = field(default_factory=dict)
    on_failure: Optional[List[Any]] = None
    line: int = 0


# ── Try / retry / catch ─────────────────────────────────────────────

@dataclass
class CatchClause:
    """``catch error_type { … }``"""
    error_type: str               # e.g. "timeout_error", "any_error", "validation_error"
    body: List[Any] = field(default_factory=list)
    line: int = 0


@dataclass
class RetryConfig:
    """``retry { strategy: …, max_attempts: … }``"""
    strategy: str = "exponential_backoff"
    max_attempts: int = 3
    initial_delay: Optional[float] = None
    max_delay: Optional[float] = None
    line: int = 0


@dataclass
class TryNode:
    """``try { … } retry { … } catch err { … }``"""
    body: List[Any] = field(default_factory=list)
    retry: Optional[RetryConfig] = None
    catches: List[CatchClause] = field(default_factory=list)
    line: int = 0


# ── Finally ──────────────────────────────────────────────────────────

@dataclass
class FinallyNode:
    """``finally { … }``"""
    body: List[Any] = field(default_factory=list)
    line: int = 0


# ── Workflow (top-level) ──────────────────────────────────────────────

@dataclass
class WorkflowNode:
    """Top-level workflow definition.

    ``workflow name { version: "…" … }``
    """
    name: str
    version: Optional[str] = None
    owner: Optional[str] = None
    protected_by: Optional[str] = None
    criticality: Optional[str] = None
    description: Optional[str] = None
    agent: Optional[AgentType] = None
    guard: Optional[GuardNode] = None
    budget: Optional[BudgetNode] = None
    circuit_breaker: Optional[CircuitBreakerNode] = None
    body: List[Any] = field(default_factory=list)
    quality_gate: Optional[QualityGateNode] = None
    finally_block: Optional[FinallyNode] = None
    line: int = 0

    # convenience for the compiler bridge
    @property
    def steps(self) -> List[StepNode]:
        return [n for n in self.body if isinstance(n, StepNode)]

    @property
    def parallels(self) -> List[ParallelNode]:
        return [n for n in self.body if isinstance(n, ParallelNode)]

    @property
    def conditionals(self) -> List[IfNode]:
        return [n for n in self.body if isinstance(n, IfNode)]
