"""Compiler bridge: converts parsed .orc AST into Orchestra core objects.

Takes WorkflowNode trees produced by the Parser and creates
Workflow / Task / Agent instances that the existing Executor understands.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestra.core.agent import Agent
from orchestra.core.context import Context
from orchestra.core.task import Task
from orchestra.core.workflow import Workflow
from orchestra.parser.ast_nodes import (
    AgentRef,
    AgentType,
    BalanceAgent,
    BestForAgent,
    BudgetNode,
    CascadeAgent,
    CheapestAboveAgent,
    CircuitBreakerNode,
    ForEachNode,
    GuardNode,
    IfNode,
    MatchNode,
    OnPartialFailureNode,
    ParallelNode,
    PropertyAssignment,
    QualityGateNode,
    RouteAgent,
    SelectAgent,
    StepNode,
    TimeoutNode,
    TritonAgent,
    TryNode,
    FinallyNode,
    ValidateOutputNode,
    WorkflowNode,
)
from orchestra.parser.parser import Parser, ParseError


class CompilationError(Exception):
    """Raised when AST -> Workflow conversion fails."""


class OrcCompiler:
    """Compiles ``.orc`` source text into executable Workflow objects.

    Usage::

        compiler = OrcCompiler()
        workflows = compiler.compile_source(source_text)
        # or
        workflows = compiler.compile_file("path/to/workflow.orc")

        # Inspect compilation results
        for wf in workflows:
            print(wf.name, wf.metadata)
    """

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile_file(self, path: str) -> List[Workflow]:
        """Parse and compile a ``.orc`` file.

        Args:
            path: Filesystem path to the .orc file.

        Returns:
            List of compiled Workflow objects.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            ParseError: If the file has syntax errors.
            CompilationError: If the AST can't be converted.
        """
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {path}")
        source = filepath.read_text(encoding="utf-8")
        return self.compile_source(source, origin=str(filepath))

    def compile_source(self, source: str, origin: str = "<string>") -> List[Workflow]:
        """Parse and compile raw .orc source text.

        Args:
            source: The .orc source code.
            origin: Label for error messages (e.g. filename).

        Returns:
            List of compiled Workflow objects.
        """
        self.errors = []
        self.warnings = []

        parser = Parser(source)
        ast_nodes = parser.parse()

        if not ast_nodes:
            self.warnings.append(f"{origin}: No workflow definitions found")
            return []

        workflows: List[Workflow] = []
        for wf_node in ast_nodes:
            try:
                wf = self._compile_workflow(wf_node)
                workflows.append(wf)
            except Exception as e:
                self.errors.append(f"{origin}: {e}")

        if self.errors:
            raise CompilationError(
                f"Compilation failed with {len(self.errors)} error(s):\n"
                + "\n".join(f"  - {e}" for e in self.errors)
            )

        return workflows

    def validate_file(self, path: str) -> dict:
        """Validate a .orc file without producing executable workflows.

        Returns a dict with ``valid``, ``errors``, ``warnings``, and
        ``workflows`` (summary info).
        """
        try:
            workflows = self.compile_file(path)
            return {
                "valid": True,
                "errors": [],
                "warnings": list(self.warnings),
                "workflows": [
                    {
                        "name": wf.name,
                        "agents": list(wf.agents.keys()),
                        "tasks": list(wf.tasks.keys()),
                    }
                    for wf in workflows
                ],
            }
        except (ParseError, CompilationError, FileNotFoundError) as e:
            return {
                "valid": False,
                "errors": [str(e)] + list(self.errors),
                "warnings": list(self.warnings),
                "workflows": [],
            }

    def to_execution_plan(self, workflows: List[Workflow]) -> dict:
        """Generate a JSON-serialisable execution plan from compiled workflows."""
        plan = {
            "version": "2.0",
            "workflows": [],
        }
        for wf in workflows:
            wf_plan: dict[str, Any] = {
                "name": wf.name,
                "metadata": wf.metadata,
                "agents": {
                    name: {
                        "provider": agent.provider,
                        "config": agent.config,
                    }
                    for name, agent in wf.agents.items()
                },
                "tasks": [],
            }
            # Build task list with dependency info
            for name, task in wf.tasks.items():
                wf_plan["tasks"].append({
                    "name": task.name,
                    "description": task.description,
                    "agent": task.agent,
                    "dependencies": list(task.dependencies),
                    "timeout": task.timeout,
                    "metadata": task.metadata,
                })
            plan["workflows"].append(wf_plan)
        return plan

    # ------------------------------------------------------------------
    # Internal: WorkflowNode → Workflow
    # ------------------------------------------------------------------

    def _compile_workflow(self, node: WorkflowNode) -> Workflow:
        description = node.description or f"Workflow: {node.name}"
        wf = Workflow(name=node.name, description=description)

        # Store metadata from the .orc file
        wf.metadata["orc_version"] = node.version
        wf.metadata["owner"] = node.owner
        wf.metadata["protected_by"] = node.protected_by
        wf.metadata["criticality"] = node.criticality

        # Compile guard into metadata
        if node.guard:
            wf.metadata["guard"] = self._compile_guard(node.guard)

        # Compile budget into metadata
        if node.budget:
            wf.metadata["budget"] = self._compile_budget(node.budget)

        # Compile circuit breaker into metadata
        if node.circuit_breaker:
            wf.metadata["circuit_breaker"] = self._compile_circuit_breaker(
                node.circuit_breaker
            )

        # Compile quality gate into metadata
        if node.quality_gate:
            wf.metadata["quality_gate"] = self._compile_quality_gate(node.quality_gate)

        # Workflow-level agent declaration → stored in metadata for runtime
        if node.agent:
            wf.metadata["default_agent"] = self._agent_to_dict(node.agent)

        # Walk body and flatten to tasks + agents
        task_counter = _Counter()
        self._compile_body(node.body, wf, task_counter, parent_deps=[])

        # Finally block becomes a special task that depends on everything else
        if node.finally_block:
            all_task_names = list(wf.tasks.keys())
            self._compile_body(
                node.finally_block.body, wf, task_counter,
                parent_deps=all_task_names,
                tag="finally",
            )

        return wf

    # ------------------------------------------------------------------
    # Body flattening — recursively walk AST, emit Tasks + Agents
    # ------------------------------------------------------------------

    def _compile_body(
        self,
        items: List[Any],
        wf: Workflow,
        counter: _Counter,
        parent_deps: List[str],
        tag: str = "",
    ) -> List[str]:
        """Compile a list of AST body items into tasks/agents on *wf*.

        Returns a list of task names that were created at this level
        (so downstream items can depend on them).
        """
        created: List[str] = []
        prev_deps = list(parent_deps)

        for item in items:
            if isinstance(item, StepNode):
                task_name = self._compile_step(item, wf, counter, prev_deps, tag)
                created.append(task_name)
                prev_deps = [task_name]

            elif isinstance(item, ParallelNode):
                names = self._compile_parallel(item, wf, counter, prev_deps, tag)
                created.extend(names)
                prev_deps = list(names)

            elif isinstance(item, IfNode):
                names = self._compile_if(item, wf, counter, prev_deps, tag)
                created.extend(names)
                if names:
                    prev_deps = list(names)

            elif isinstance(item, MatchNode):
                names = self._compile_match(item, wf, counter, prev_deps, tag)
                created.extend(names)
                if names:
                    prev_deps = list(names)

            elif isinstance(item, TryNode):
                names = self._compile_try(item, wf, counter, prev_deps, tag)
                created.extend(names)
                if names:
                    prev_deps = list(names)

            elif isinstance(item, ForEachNode):
                names = self._compile_for_each(item, wf, counter, prev_deps, tag)
                created.extend(names)
                if names:
                    prev_deps = list(names)

            elif isinstance(item, PropertyAssignment):
                # Standalone properties in body — store as workflow metadata
                pass  # These are consumed by the parent context

        return created

    # ------------------------------------------------------------------
    # Step → Task + Agent
    # ------------------------------------------------------------------

    def _compile_step(
        self,
        step: StepNode,
        wf: Workflow,
        counter: _Counter,
        deps: List[str],
        tag: str,
    ) -> str:
        task_name = step.name
        # Deduplicate names
        if task_name in wf.tasks:
            task_name = f"{task_name}_{counter.next()}"

        # Register agent
        agent_name: Optional[str] = None
        if step.agent:
            agent_name = self._register_agent(step.agent, wf)

        # Build task
        description = step.task or f"Step: {step.name}"
        timeout_val = None
        if step.timeout:
            timeout_val = int(step.timeout.hard or step.timeout.soft or 0) or None

        task = Task(
            name=task_name,
            description=description,
            agent=agent_name,
            dependencies=list(deps),
            timeout=timeout_val,
            metadata={},
        )

        # Store step-level metadata
        if step.model:
            task.metadata["model"] = step.model
        if step.validate_output:
            task.metadata["validate_output"] = {
                "assertions": [a.raw for a in step.validate_output.assertions],
            }
        if step.timeout:
            task.metadata["timeout_config"] = {
                "soft": step.timeout.soft,
                "hard": step.timeout.hard,
            }
        if tag:
            task.metadata["tag"] = tag
        for prop in step.properties:
            task.metadata[prop.key] = prop.value

        # Handle nested try blocks
        if step.body:
            for item in step.body:
                if isinstance(item, TryNode):
                    task.metadata["try_config"] = self._try_to_dict(item)

        wf.add_task(task)
        return task_name

    # ------------------------------------------------------------------
    # Parallel → multiple Tasks (same deps, no inter-deps)
    # ------------------------------------------------------------------

    def _compile_parallel(
        self,
        node: ParallelNode,
        wf: Workflow,
        counter: _Counter,
        deps: List[str],
        tag: str,
    ) -> List[str]:
        names: List[str] = []
        for step in node.steps:
            name = self._compile_step(step, wf, counter, deps, tag)
            names.append(name)

        # Store partial-failure config on all parallel tasks
        if node.on_partial_failure:
            pf = {
                "strategy": node.on_partial_failure.strategy,
                "min_success_rate": node.on_partial_failure.min_success_rate,
            }
            for name in names:
                wf.tasks[name].metadata["on_partial_failure"] = pf

        return names

    # ------------------------------------------------------------------
    # If/else → conditional tasks
    # ------------------------------------------------------------------

    def _compile_if(
        self,
        node: IfNode,
        wf: Workflow,
        counter: _Counter,
        deps: List[str],
        tag: str,
    ) -> List[str]:
        all_created: List[str] = []

        # True branch
        true_names = self._compile_body(node.body, wf, counter, deps, tag)
        for n in true_names:
            wf.tasks[n].metadata["condition"] = node.condition.raw
            wf.tasks[n].metadata["branch"] = "if"
        all_created.extend(true_names)

        # Elif branches
        for elif_node in node.elif_branches:
            elif_names = self._compile_if(elif_node, wf, counter, deps, tag)
            all_created.extend(elif_names)

        # Else branch
        if node.else_body:
            else_names = self._compile_body(node.else_body, wf, counter, deps, tag)
            for n in else_names:
                wf.tasks[n].metadata["condition"] = f"NOT ({node.condition.raw})"
                wf.tasks[n].metadata["branch"] = "else"
            all_created.extend(else_names)

        return all_created

    # ------------------------------------------------------------------
    # Match → case tasks
    # ------------------------------------------------------------------

    def _compile_match(
        self,
        node: MatchNode,
        wf: Workflow,
        counter: _Counter,
        deps: List[str],
        tag: str,
    ) -> List[str]:
        all_created: List[str] = []
        for case in node.cases:
            names = self._compile_body(case.body, wf, counter, deps, tag)
            for n in names:
                wf.tasks[n].metadata["match_expr"] = node.expression
                wf.tasks[n].metadata["match_case"] = case.value
            all_created.extend(names)

        if node.default:
            names = self._compile_body(node.default.body, wf, counter, deps, tag)
            for n in names:
                wf.tasks[n].metadata["match_expr"] = node.expression
                wf.tasks[n].metadata["match_case"] = "default"
            all_created.extend(names)

        return all_created

    # ------------------------------------------------------------------
    # Try → tasks with retry/catch metadata
    # ------------------------------------------------------------------

    def _compile_try(
        self,
        node: TryNode,
        wf: Workflow,
        counter: _Counter,
        deps: List[str],
        tag: str,
    ) -> List[str]:
        names = self._compile_body(node.body, wf, counter, deps, tag)
        meta = self._try_to_dict(node)
        for n in names:
            wf.tasks[n].metadata["try_config"] = meta
        return names

    # ------------------------------------------------------------------
    # For each → tasks with iteration metadata
    # ------------------------------------------------------------------

    def _compile_for_each(
        self,
        node: ForEachNode,
        wf: Workflow,
        counter: _Counter,
        deps: List[str],
        tag: str,
    ) -> List[str]:
        names = self._compile_body(node.body, wf, counter, deps, tag)
        for n in names:
            wf.tasks[n].metadata["for_each"] = {
                "variable": node.variable,
                "collection": node.collection,
            }
        return names

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def _register_agent(self, agent_spec: AgentType, wf: Workflow) -> str:
        """Register an agent on the workflow and return its name."""
        if isinstance(agent_spec, AgentRef):
            name = agent_spec.name
            if name not in wf.agents:
                wf.agents[name] = Agent(name=name, provider="orc", metadata={})
            return name

        if isinstance(agent_spec, TritonAgent):
            name = f"triton_{agent_spec.model_name.replace('-', '_')}"
            if name not in wf.agents:
                wf.agents[name] = Agent(
                    name=name,
                    provider="triton_ternary",
                    config={"model_name": agent_spec.model_name},
                    metadata={"type": "triton_ternary"},
                )
            return name

        if isinstance(agent_spec, CascadeAgent):
            name = f"cascade_{agent_spec.try_agent}"
            if name not in wf.agents:
                wf.agents[name] = Agent(
                    name=name,
                    provider="cascade",
                    config={
                        "try": agent_spec.try_agent,
                        "fallback": agent_spec.fallback,
                        "last_resort": agent_spec.last_resort,
                    },
                    metadata={"type": "cascade"},
                )
            return name

        if isinstance(agent_spec, BalanceAgent):
            name = f"balance_{agent_spec.strategy}"
            if name not in wf.agents:
                wf.agents[name] = Agent(
                    name=name,
                    provider="balance",
                    config={
                        "strategy": agent_spec.strategy,
                        "pool": agent_spec.pool,
                        "max_concurrent": agent_spec.max_concurrent,
                    },
                    metadata={"type": "balance"},
                )
            return name

        if isinstance(agent_spec, RouteAgent):
            name = f"route_{id(agent_spec)}"
            if name not in wf.agents:
                wf.agents[name] = Agent(
                    name=name,
                    provider="route",
                    config={
                        "rules": [
                            {"condition": r.key, "target": r.value}
                            for r in agent_spec.rules
                        ],
                        "default": agent_spec.default,
                    },
                    metadata={"type": "route"},
                )
            return name

        if isinstance(agent_spec, SelectAgent):
            name = "select_agent"
            if name not in wf.agents:
                wf.agents[name] = Agent(
                    name=name,
                    provider="select",
                    config={
                        "metric": agent_spec.metric,
                        "timeframe": agent_spec.timeframe,
                        "optimize_for": agent_spec.optimize_for,
                        "weights": agent_spec.weights,
                        "candidates": agent_spec.candidates,
                        "fallback": agent_spec.fallback,
                    },
                    metadata={"type": "select"},
                )
            return name

        if isinstance(agent_spec, CheapestAboveAgent):
            name = "cheapest_above"
            if name not in wf.agents:
                wf.agents[name] = Agent(
                    name=name,
                    provider="cheapest_above",
                    config={"quality_threshold": agent_spec.quality_threshold},
                    metadata={"type": "cheapest_above"},
                )
            return name

        if isinstance(agent_spec, BestForAgent):
            name = "best_for"
            if name not in wf.agents:
                wf.agents[name] = Agent(
                    name=name,
                    provider="best_for",
                    config=agent_spec.properties,
                    metadata={"type": "best_for"},
                )
            return name

        # Fallback
        name = f"agent_{id(agent_spec)}"
        wf.agents[name] = Agent(name=name, provider="unknown", metadata={})
        return name

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _agent_to_dict(self, spec: AgentType) -> dict:
        if isinstance(spec, AgentRef):
            return {"type": "ref", "name": spec.name}
        if isinstance(spec, TritonAgent):
            return {"type": "triton_ternary", "model": spec.model_name}
        if isinstance(spec, CascadeAgent):
            return {"type": "cascade", "try": spec.try_agent,
                    "fallback": spec.fallback, "last_resort": spec.last_resort}
        if isinstance(spec, BalanceAgent):
            return {"type": "balance", "strategy": spec.strategy,
                    "pool": spec.pool, "max_concurrent": spec.max_concurrent}
        return {"type": "unknown"}

    def _compile_guard(self, node: GuardNode) -> dict:
        return {
            "requirements": [r.raw for r in node.requirements],
            "on_violation": node.on_violation,
        }

    def _compile_budget(self, node: BudgetNode) -> dict:
        return {
            "per_task": node.per_task,
            "hourly_limit": node.hourly_limit,
            "alert_at": node.alert_at,
        }

    def _compile_circuit_breaker(self, node: CircuitBreakerNode) -> dict:
        return {
            "failure_threshold": node.failure_threshold,
            "timeout": node.timeout,
            "half_open_after": node.half_open_after,
        }

    def _compile_quality_gate(self, node: QualityGateNode) -> dict:
        return {
            "metrics": node.metrics,
            "has_on_failure": node.on_failure is not None,
        }

    def _try_to_dict(self, node: TryNode) -> dict:
        result: dict[str, Any] = {}
        if node.retry:
            result["retry"] = {
                "strategy": node.retry.strategy,
                "max_attempts": node.retry.max_attempts,
                "initial_delay": node.retry.initial_delay,
                "max_delay": node.retry.max_delay,
            }
        if node.catches:
            result["catches"] = [
                {"error_type": c.error_type} for c in node.catches
            ]
        return result


class _Counter:
    """Simple auto-incrementing counter for deduplicating names."""

    def __init__(self):
        self._n = 0

    def next(self) -> int:
        self._n += 1
        return self._n
