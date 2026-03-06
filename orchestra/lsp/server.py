"""Orchestra Language Server — LSP implementation for .orc files.

Implements the Language Server Protocol to provide IDE features:
- Real-time diagnostics from the Orchestra lexer/parser
- Autocompletion for keywords, agent types, and workflow constructs
- Hover documentation for Orchestra DSL elements
- Document symbol outlines (workflows, steps, gates)
- Semantic token highlighting
"""

from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

from orchestra.parser.lexer import Lexer, LexerError, TokenType, KEYWORDS
from orchestra.parser.parser import Parser, ParseError
from orchestra.parser.compiler_bridge import OrcCompiler, CompilationError

logger = logging.getLogger("orchestra-lsp")


# ── LSP Protocol Constants ───────────────────────────────────────────

class DiagnosticSeverity(IntEnum):
    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


class CompletionItemKind(IntEnum):
    TEXT = 1
    METHOD = 2
    FUNCTION = 3
    CONSTRUCTOR = 4
    FIELD = 5
    VARIABLE = 6
    CLASS = 7
    INTERFACE = 8
    MODULE = 9
    PROPERTY = 10
    KEYWORD = 14
    SNIPPET = 15
    VALUE = 12
    ENUM = 13
    ENUM_MEMBER = 20
    STRUCT = 22
    OPERATOR = 24


class SymbolKind(IntEnum):
    FILE = 1
    MODULE = 2
    NAMESPACE = 3
    PACKAGE = 4
    CLASS = 5
    METHOD = 6
    PROPERTY = 7
    FIELD = 8
    CONSTRUCTOR = 9
    ENUM = 10
    FUNCTION = 12
    VARIABLE = 13
    CONSTANT = 14
    STRING = 15
    NUMBER = 16
    BOOLEAN = 17
    OBJECT = 19
    KEY = 20
    EVENT = 24
    OPERATOR = 25


# ── Data Structures ──────────────────────────────────────────────────

@dataclass
class Position:
    line: int
    character: int

    def to_dict(self) -> dict:
        return {"line": self.line, "character": self.character}


@dataclass
class Range:
    start: Position
    end: Position

    def to_dict(self) -> dict:
        return {"start": self.start.to_dict(), "end": self.end.to_dict()}


@dataclass
class Diagnostic:
    range: Range
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    source: str = "orchestra"

    def to_dict(self) -> dict:
        return {
            "range": self.range.to_dict(),
            "message": self.message,
            "severity": self.severity.value,
            "source": self.source,
        }


@dataclass
class CompletionItem:
    label: str
    kind: CompletionItemKind
    detail: str = ""
    documentation: str = ""
    insert_text: str | None = None
    insert_text_format: int = 1  # 1=PlainText, 2=Snippet

    def to_dict(self) -> dict:
        result: dict[str, Any] = {
            "label": self.label,
            "kind": self.kind.value,
        }
        if self.detail:
            result["detail"] = self.detail
        if self.documentation:
            result["documentation"] = {
                "kind": "markdown",
                "value": self.documentation,
            }
        if self.insert_text:
            result["insertText"] = self.insert_text
            result["insertTextFormat"] = self.insert_text_format
        return result


@dataclass
class DocumentSymbol:
    name: str
    kind: SymbolKind
    range: Range
    selection_range: Range
    children: list[DocumentSymbol] = field(default_factory=list)

    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "kind": self.kind.value,
            "range": self.range.to_dict(),
            "selectionRange": self.selection_range.to_dict(),
        }
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        return result


# ── Keyword Documentation ────────────────────────────────────────────

KEYWORD_DOCS: dict[str, dict[str, str]] = {
    "workflow": {
        "detail": "Workflow definition",
        "documentation": "Top-level container for a workflow. Contains steps, agents, gates, and routing logic.\n\n```orc\nworkflow my_workflow {\n    version: \"2.0\"\n    ...\n}\n```",
    },
    "step": {
        "detail": "Execution step",
        "documentation": "A single unit of work assigned to an agent.\n\n```orc\nstep analyze {\n    agent: guardian_claude\n    task: \"Perform analysis\"\n    timeout: 10.0\n}\n```",
    },
    "parallel": {
        "detail": "Parallel execution block",
        "documentation": "Run multiple steps concurrently.\n\n```orc\nparallel {\n    step a { ... }\n    step b { ... }\n}\n```",
    },
    "guard": {
        "detail": "Input guard clause",
        "documentation": "Validate inputs before workflow execution.\n\n```orc\nguard {\n    require: input.id != null\n    on_violation: reject(\"Invalid input\")\n}\n```",
    },
    "budget": {
        "detail": "Budget constraints",
        "documentation": "Cost controls for workflow execution.\n\n```orc\nbudget {\n    per_task: 0.01\n    hourly_limit: 500.0\n    alert_at: 80.0\n}\n```",
    },
    "quality_gate": {
        "detail": "Quality gate check",
        "documentation": "Validate outputs against quality thresholds.\n\n```orc\nquality_gate {\n    metrics: { accuracy: 0.95 }\n    on_failure { ... }\n}\n```",
    },
    "circuit_breaker": {
        "detail": "Circuit breaker pattern",
        "documentation": "Prevent cascading failures with automatic trip.\n\n```orc\ncircuit_breaker {\n    failure_threshold: 5\n    timeout: 30.0\n    half_open_after: 60.0\n}\n```",
    },
    "try": {
        "detail": "Try block with error handling",
        "documentation": "Error handling with retry and catch.\n\n```orc\ntry {\n    step ... { ... }\n} retry {\n    strategy: exponential_backoff\n    max_attempts: 3\n} catch timeout_error {\n    ...\n}\n```",
    },
    "if": {
        "detail": "Conditional execution",
        "documentation": "Branch workflow based on conditions.\n\n```orc\nif score > 80 {\n    step ... { ... }\n} else {\n    step ... { ... }\n}\n```",
    },
    "match": {
        "detail": "Pattern matching",
        "documentation": "Route based on value patterns.\n\n```orc\nmatch input.type {\n    case \"a\" => { ... }\n    case \"b\" => { ... }\n    default => { ... }\n}\n```",
    },
    "agent": {
        "detail": "Agent assignment",
        "documentation": "Assign an agent to execute a step. Supports simple references, cascades, load balancing, routing, and Triton ternary models.\n\n```orc\nagent: guardian_claude\nagent: cascade [try: a, fallback: b]\nagent: triton_ternary(\"model-v1\")\n```",
    },
    "cascade": {
        "detail": "Cascade agent routing",
        "documentation": "Try agents sequentially with fallbacks.\n\n```orc\nagent: cascade [\n    try: primary_agent,\n    fallback: secondary_agent,\n    last_resort: guardian_claude\n]\n```",
    },
    "balance": {
        "detail": "Load-balanced agent pool",
        "documentation": "Distribute work across agents.\n\n```orc\nagent: balance {\n    strategy: least_loaded\n    pool: [agent_1, agent_2, agent_3]\n    max_concurrent: 5\n}\n```",
    },
    "triton_ternary": {
        "detail": "Triton ternary model agent",
        "documentation": "Reference a Triton-compiled ternary model for efficient inference.\n\n```orc\nagent: triton_ternary(\"credit-risk-v4\")\n```\n\nTernary models deliver 4–16× compression over FP32.",
    },
    "validate_output": {
        "detail": "Output validation",
        "documentation": "Assert conditions on step outputs.\n\n```orc\nvalidate_output {\n    assert: result.score >= 0\n    assert: result.score <= 100\n}\n```",
    },
    "finally": {
        "detail": "Finally block",
        "documentation": "Always executed, regardless of success or failure.\n\n```orc\nfinally {\n    step cleanup {\n        action: log_metrics\n    }\n}\n```",
    },
    "version": {
        "detail": "Workflow version",
        "documentation": "Semantic version string for the workflow.\n\n```orc\nversion: \"2.0\"\n```",
    },
    "owner": {
        "detail": "Workflow owner",
        "documentation": "Team or individual responsible for the workflow.\n\n```orc\nowner: \"Platform Team\"\n```",
    },
    "protected_by": {
        "detail": "Security protector",
        "documentation": "Assign a guardian agent for security enforcement.\n\n```orc\nprotected_by: bunny_guardian\n```",
    },
    "timeout": {
        "detail": "Timeout configuration",
        "documentation": "Set soft and hard timeouts for steps.\n\n```orc\ntimeout: 10.0\ntimeout { soft: 8.0, hard: 15.0 }\n```",
    },
    "task": {
        "detail": "Task description",
        "documentation": "Natural language description of the work to be done.\n\n```orc\ntask: \"Analyze the input data and produce a summary\"\n```",
    },
    "route": {
        "detail": "Conditional agent routing",
        "documentation": "Route to different agents based on conditions.\n\n```orc\nagent: route {\n    if complexity > 0.8 then use: advanced_agent\n    else use: simple_agent\n}\n```",
    },
    "select": {
        "detail": "Performance-based agent selection",
        "documentation": "Select agents based on performance metrics.\n\n```orc\nagent: select {\n    metric: accuracy\n    candidates: [agent_a, agent_b]\n}\n```",
    },
    "best_for": {
        "detail": "Best-fit agent selection",
        "documentation": "Select the best agent based on multiple criteria.\n\n```orc\nagent: best_for(complexity: 0.9, max_cost: 0.05, quality: 0.95)\n```",
    },
    "cheapest_above": {
        "detail": "Cost-optimized agent selection",
        "documentation": "Select the cheapest agent above a quality threshold.\n\n```orc\nagent: cheapest_above(quality_threshold: 0.8)\n```",
    },
    "on_partial_failure": {
        "detail": "Partial failure handler",
        "documentation": "Handle partial failures in parallel blocks.\n\n```orc\non_partial_failure {\n    strategy: continue\n    min_success_rate: 0.75\n}\n```",
    },
    "retry": {
        "detail": "Retry configuration",
        "documentation": "Configure retry behavior for failed steps.\n\n```orc\nretry {\n    strategy: exponential_backoff\n    max_attempts: 3\n    initial_delay: 1.0\n    max_delay: 30.0\n}\n```",
    },
    "catch": {
        "detail": "Error catch handler",
        "documentation": "Handle specific error types.\n\n```orc\ncatch timeout_error {\n    agent: fallback_agent\n    alert: \"Primary agent timed out\"\n}\n```",
    },
    "metrics": {
        "detail": "Quality metrics",
        "documentation": "Define metric thresholds.\n\n```orc\nmetrics: {\n    accuracy: 0.95,\n    completeness: 0.90\n}\n```",
    },
    "for": {
        "detail": "Iteration construct",
        "documentation": "Iterate over collections.\n\n```orc\nfor each item in input.items {\n    step process { ... }\n}\n```",
    },
    "criticality": {
        "detail": "Workflow criticality level",
        "documentation": "Set the criticality level of the workflow.\n\n```orc\ncriticality: high\n```",
    },
}


# ── Snippet Templates ────────────────────────────────────────────────

SNIPPETS: list[dict[str, str]] = [
    {
        "label": "workflow",
        "detail": "New workflow definition",
        "insert_text": 'workflow ${1:name} {\n    version: "${2:2.0}"\n    owner: "${3:Team}"\n    protected_by: bunny_guardian\n\n    $0\n}',
        "documentation": "Create a new workflow definition with standard boilerplate.",
    },
    {
        "label": "step",
        "detail": "New step",
        "insert_text": 'step ${1:name} {\n    agent: ${2:agent_name}\n    task: "${3:description}"\n    timeout: ${4:10.0}\n}',
        "documentation": "Create a new execution step.",
    },
    {
        "label": "parallel",
        "detail": "Parallel execution block",
        "insert_text": "parallel {\n    step ${1:step_a} {\n        agent: ${2:agent}\n        task: \"${3:task}\"\n    }\n\n    step ${4:step_b} {\n        agent: ${5:agent}\n        task: \"${6:task}\"\n    }\n}",
        "documentation": "Create a parallel execution block with multiple steps.",
    },
    {
        "label": "guard",
        "detail": "Guard clause",
        "insert_text": 'guard {\n    require: ${1:condition}\n    on_violation: reject("${2:error message}")\n}',
        "documentation": "Add input validation guards.",
    },
    {
        "label": "budget",
        "detail": "Budget constraints",
        "insert_text": "budget {\n    per_task: ${1:0.01}\n    hourly_limit: ${2:500.0}\n    alert_at: ${3:80.0}\n}",
        "documentation": "Add cost controls to the workflow.",
    },
    {
        "label": "quality_gate",
        "detail": "Quality gate",
        "insert_text": "quality_gate {\n    metrics: {\n        ${1:accuracy}: ${2:0.95}\n    }\n    on_failure {\n        step ${3:review} {\n            agent: ${4:reviewer}\n            task: \"${5:Review failed items}\"\n        }\n    }\n}",
        "documentation": "Add output quality validation.",
    },
    {
        "label": "circuit_breaker",
        "detail": "Circuit breaker",
        "insert_text": "circuit_breaker {\n    failure_threshold: ${1:5}\n    timeout: ${2:30.0}\n    half_open_after: ${3:60.0}\n}",
        "documentation": "Add circuit breaker failure protection.",
    },
    {
        "label": "try-retry-catch",
        "detail": "Error handling block",
        "insert_text": 'try {\n    step ${1:name} {\n        agent: ${2:agent}\n        task: "${3:task}"\n    }\n} retry {\n    strategy: exponential_backoff\n    max_attempts: ${4:3}\n    initial_delay: ${5:1.0}\n} catch ${6:error_type} {\n    alert: "${7:Error occurred}"\n}',
        "documentation": "Add error handling with retry and catch.",
    },
    {
        "label": "if-else",
        "detail": "Conditional block",
        "insert_text": "if ${1:condition} {\n    $2\n} else {\n    $3\n}",
        "documentation": "Add conditional workflow branching.",
    },
    {
        "label": "match-case",
        "detail": "Pattern matching block",
        "insert_text": "match ${1:value} {\n    case ${2:\"pattern_a\"} => {\n        $3\n    }\n    case ${4:\"pattern_b\"} => {\n        $5\n    }\n    default => {\n        $6\n    }\n}",
        "documentation": "Add pattern matching routing.",
    },
    {
        "label": "validate_output",
        "detail": "Output validation",
        "insert_text": "validate_output {\n    assert: ${1:result.field} ${2:>=} ${3:0}\n}",
        "documentation": "Add output assertions to a step.",
    },
    {
        "label": "cascade-agent",
        "detail": "Cascade agent with fallbacks",
        "insert_text": "agent: cascade [\n    try: ${1:primary_agent},\n    fallback: ${2:secondary_agent},\n    last_resort: ${3:guardian_claude}\n]",
        "documentation": "Cascade agent routing with sequential fallbacks.",
    },
    {
        "label": "triton-agent",
        "detail": "Triton ternary agent",
        "insert_text": 'agent: triton_ternary("${1:model-name-v1}")',
        "documentation": "Reference a Triton-compiled ternary model.",
    },
    {
        "label": "balance-agent",
        "detail": "Load-balanced agent pool",
        "insert_text": "agent: balance {\n    strategy: ${1:least_loaded}\n    pool: [${2:agent_1, agent_2}]\n    max_concurrent: ${3:5}\n}",
        "documentation": "Load-balanced agent pool distribution.",
    },
    {
        "label": "finally",
        "detail": "Finally cleanup block",
        "insert_text": "finally {\n    step ${1:cleanup} {\n        action: ${2:log_metrics}\n        data: { ${3:workflow_duration, total_cost} }\n    }\n}",
        "documentation": "Add a cleanup block that always executes.",
    },
    {
        "label": "for-each",
        "detail": "Iteration block",
        "insert_text": 'for each ${1:item} in ${2:input.items} {\n    step ${3:process} {\n        agent: ${4:agent}\n        task: "${5:Process item}"\n    }\n}',
        "documentation": "Iterate over a collection.",
    },
]


# ── Semantic Token Types ─────────────────────────────────────────────

SEMANTIC_TOKEN_TYPES = [
    "keyword",
    "type",
    "function",
    "variable",
    "string",
    "number",
    "operator",
    "comment",
    "property",
    "namespace",
]

SEMANTIC_TOKEN_MODIFIERS = [
    "declaration",
    "definition",
    "readonly",
]

# Map Orchestra token types to semantic token indices
_TOKEN_TYPE_MAP: dict[TokenType, int] = {
    # Keywords
    TokenType.WORKFLOW: 0,
    TokenType.STEP: 0,
    TokenType.PARALLEL: 0,
    TokenType.IF: 0,
    TokenType.ELSE: 0,
    TokenType.MATCH: 0,
    TokenType.CASE: 0,
    TokenType.DEFAULT: 0,
    TokenType.GUARD: 0,
    TokenType.BUDGET: 0,
    TokenType.CIRCUIT_BREAKER: 0,
    TokenType.QUALITY_GATE: 0,
    TokenType.TRY: 0,
    TokenType.RETRY: 0,
    TokenType.CATCH: 0,
    TokenType.FINALLY: 0,
    TokenType.FOR: 0,
    TokenType.EACH: 0,
    TokenType.IN: 0,
    TokenType.THEN: 0,
    TokenType.REQUIRE: 0,
    TokenType.ASSERT: 0,
    TokenType.VALIDATE_OUTPUT: 0,
    TokenType.AGENT: 8,    # property
    TokenType.MODEL: 8,
    TokenType.TASK: 8,
    TokenType.TIMEOUT: 8,
    TokenType.VERSION: 8,
    TokenType.OWNER: 8,
    TokenType.PROTECTED_BY: 8,
    TokenType.CRITICALITY: 8,
    TokenType.CASCADE: 1,  # type
    TokenType.BALANCE: 1,
    TokenType.ROUTE: 1,
    TokenType.SELECT: 1,
    TokenType.TRITON_TERNARY: 2,  # function
    TokenType.BEST_FOR: 2,
    TokenType.CHEAPEST_ABOVE: 2,
    # Literals
    TokenType.STRING: 4,
    TokenType.NUMBER: 5,
    TokenType.BOOL_TRUE: 0,
    TokenType.BOOL_FALSE: 0,
    TokenType.NULL: 0,
    TokenType.IDENTIFIER: 3,
    # Operators
    TokenType.GT: 6,
    TokenType.LT: 6,
    TokenType.GTE: 6,
    TokenType.LTE: 6,
    TokenType.EQ: 6,
    TokenType.NEQ: 6,
    TokenType.ARROW: 6,
}


# ── Language Server ──────────────────────────────────────────────────

class OrchestraLanguageServer:
    """Language Server for Orchestra .orc files.

    Provides LSP-compatible methods that can be wired to any
    JSON-RPC transport (stdio, TCP, WebSocket).
    """

    def __init__(self) -> None:
        self._documents: dict[str, str] = {}
        self._diagnostics_cache: dict[str, list[Diagnostic]] = {}
        self._symbols_cache: dict[str, list[DocumentSymbol]] = {}
        self._compiler = OrcCompiler()
        # Triton model registry for autocomplete (populated externally)
        self._triton_models: list[dict[str, str]] = []

    # ── Document Management ──────────────────────────────────────

    def did_open(self, uri: str, text: str) -> list[dict]:
        """Handle textDocument/didOpen."""
        self._documents[uri] = text
        return self._publish_diagnostics(uri)

    def did_change(self, uri: str, text: str) -> list[dict]:
        """Handle textDocument/didChange (full sync)."""
        self._documents[uri] = text
        return self._publish_diagnostics(uri)

    def did_close(self, uri: str) -> None:
        """Handle textDocument/didClose."""
        self._documents.pop(uri, None)
        self._diagnostics_cache.pop(uri, None)
        self._symbols_cache.pop(uri, None)

    # ── Diagnostics ──────────────────────────────────────────────

    def _publish_diagnostics(self, uri: str) -> list[dict]:
        """Run lexer + parser + compiler validation and return diagnostics."""
        text = self._documents.get(uri, "")
        diagnostics: list[Diagnostic] = []

        # Phase 1: Lexer validation
        try:
            lexer = Lexer(text)
            tokens = lexer.tokenize()
        except LexerError as e:
            line = getattr(e, "line", 0)
            col = getattr(e, "column", 0)
            diagnostics.append(Diagnostic(
                range=Range(Position(max(0, line - 1), col), Position(max(0, line - 1), col + 10)),
                message=f"Lexer error: {e}",
                severity=DiagnosticSeverity.ERROR,
            ))
            self._diagnostics_cache[uri] = diagnostics
            return [d.to_dict() for d in diagnostics]

        # Phase 2: Parser validation
        try:
            parser = Parser(text)
            workflows = parser.parse()
        except ParseError as e:
            line = getattr(e, "line", 0)
            col = getattr(e, "column", 0)
            diagnostics.append(Diagnostic(
                range=Range(Position(max(0, line - 1), col), Position(max(0, line - 1), col + 10)),
                message=f"Parse error: {e}",
                severity=DiagnosticSeverity.ERROR,
            ))
            self._diagnostics_cache[uri] = diagnostics
            return [d.to_dict() for d in diagnostics]
        except Exception as e:
            diagnostics.append(Diagnostic(
                range=Range(Position(0, 0), Position(0, 10)),
                message=f"Parse error: {e}",
                severity=DiagnosticSeverity.ERROR,
            ))

        # Phase 3: Compilation validation
        try:
            result = self._compiler.validate_source(text)
            if not result.get("valid", True):
                for err in result.get("errors", []):
                    diagnostics.append(Diagnostic(
                        range=Range(Position(0, 0), Position(0, 0)),
                        message=str(err),
                        severity=DiagnosticSeverity.ERROR,
                    ))
                for warn in result.get("warnings", []):
                    diagnostics.append(Diagnostic(
                        range=Range(Position(0, 0), Position(0, 0)),
                        message=str(warn),
                        severity=DiagnosticSeverity.WARNING,
                    ))
        except (CompilationError, Exception) as e:
            diagnostics.append(Diagnostic(
                range=Range(Position(0, 0), Position(0, 0)),
                message=f"Compilation warning: {e}",
                severity=DiagnosticSeverity.WARNING,
            ))

        # Phase 4: Semantic checks
        diagnostics.extend(self._semantic_checks(text, workflows if 'workflows' in dir() else []))

        # Build symbols cache
        if 'workflows' in locals() and workflows:
            self._symbols_cache[uri] = self._build_symbols(text, workflows)

        self._diagnostics_cache[uri] = diagnostics
        return [d.to_dict() for d in diagnostics]

    def _semantic_checks(self, text: str, workflows: list) -> list[Diagnostic]:
        """Additional semantic validation beyond parser."""
        diagnostics: list[Diagnostic] = []
        lines = text.split("\n")

        for wf in workflows:
            # Check for missing version
            if not getattr(wf, "version", None):
                line_num = self._find_keyword_line(lines, "workflow", getattr(wf, "name", ""))
                diagnostics.append(Diagnostic(
                    range=Range(Position(line_num, 0), Position(line_num, 20)),
                    message=f"Workflow '{getattr(wf, 'name', '?')}' is missing a version declaration.",
                    severity=DiagnosticSeverity.WARNING,
                ))

            # Check for missing protected_by
            if not getattr(wf, "protected_by", None):
                line_num = self._find_keyword_line(lines, "workflow", getattr(wf, "name", ""))
                diagnostics.append(Diagnostic(
                    range=Range(Position(line_num, 0), Position(line_num, 20)),
                    message=f"Workflow '{getattr(wf, 'name', '?')}' has no 'protected_by' guard. Consider adding BUNNY Guardian protection.",
                    severity=DiagnosticSeverity.HINT,
                ))

        return diagnostics

    def _find_keyword_line(self, lines: list[str], keyword: str, name: str = "") -> int:
        """Find the line number of a keyword occurrence."""
        pattern = re.compile(rf"\b{re.escape(keyword)}\b.*\b{re.escape(name)}\b" if name else rf"\b{re.escape(keyword)}\b")
        for i, line in enumerate(lines):
            if pattern.search(line):
                return i
        return 0

    # ── Completion ───────────────────────────────────────────────

    def completion(self, uri: str, line: int, character: int) -> list[dict]:
        """Handle textDocument/completion."""
        text = self._documents.get(uri, "")
        lines = text.split("\n")

        if line >= len(lines):
            return []

        current_line = lines[line]
        prefix = current_line[:character].strip()

        items: list[CompletionItem] = []

        # Context-aware completions
        context = self._get_completion_context(lines, line, character)

        if context == "top_level":
            items.append(CompletionItem("workflow", CompletionItemKind.KEYWORD, "New workflow", insert_text='workflow ${1:name} {\n    version: "${2:2.0}"\n    $0\n}', insert_text_format=2))
        elif context == "workflow_body":
            items.extend(self._workflow_body_completions())
        elif context == "step_body":
            items.extend(self._step_body_completions())
        elif context == "agent_value":
            items.extend(self._agent_completions())
        else:
            # General keyword and snippet completions
            items.extend(self._keyword_completions())
            items.extend(self._snippet_completions())

        return [item.to_dict() for item in items]

    def _get_completion_context(self, lines: list[str], line: int, character: int) -> str:
        """Determine the completion context based on cursor position."""
        brace_depth = 0
        in_workflow = False
        in_step = False
        current_line_text = lines[line][:character].strip() if line < len(lines) else ""

        # Check if cursor is on an agent: line
        if re.match(r"^\s*agent\s*:\s*", current_line_text):
            return "agent_value"

        # Walk backwards to determine nesting context
        for i in range(line, -1, -1):
            text = lines[i] if i < line else lines[i][:character]
            brace_depth += text.count("}") - text.count("{")

            if re.match(r"\s*step\s+\w+\s*\{", text) and brace_depth <= 0:
                return "step_body"
            if re.match(r"\s*workflow\s+\w+\s*\{", text) and brace_depth <= 0:
                return "workflow_body"

        if brace_depth >= 0:
            return "top_level"

        return "unknown"

    def _workflow_body_completions(self) -> list[CompletionItem]:
        """Completions valid inside a workflow body."""
        items = []
        for s in SNIPPETS:
            items.append(CompletionItem(
                label=s["label"],
                kind=CompletionItemKind.SNIPPET,
                detail=s["detail"],
                documentation=s.get("documentation", ""),
                insert_text=s["insert_text"],
                insert_text_format=2,
            ))
        body_keywords = ["step", "parallel", "guard", "budget", "circuit_breaker",
                         "quality_gate", "if", "match", "try", "for", "finally",
                         "version", "owner", "protected_by", "criticality"]
        for kw in body_keywords:
            doc = KEYWORD_DOCS.get(kw, {})
            items.append(CompletionItem(
                label=kw,
                kind=CompletionItemKind.KEYWORD,
                detail=doc.get("detail", kw),
                documentation=doc.get("documentation", ""),
            ))
        return items

    def _step_body_completions(self) -> list[CompletionItem]:
        """Completions valid inside a step body."""
        items = []
        step_props = ["agent", "model", "task", "timeout", "validate_output",
                      "priority", "notify", "alert", "action", "data", "context"]
        for prop in step_props:
            doc = KEYWORD_DOCS.get(prop, {})
            items.append(CompletionItem(
                label=prop,
                kind=CompletionItemKind.PROPERTY,
                detail=doc.get("detail", prop),
                documentation=doc.get("documentation", ""),
            ))
        return items

    def _agent_completions(self) -> list[CompletionItem]:
        """Completions for agent values."""
        items = [
            CompletionItem("guardian_claude", CompletionItemKind.VALUE, "Guardian Claude agent"),
            CompletionItem("cascade", CompletionItemKind.KEYWORD, "Cascade routing",
                           insert_text="cascade [\n    try: ${1:primary},\n    fallback: ${2:secondary},\n    last_resort: ${3:guardian_claude}\n]",
                           insert_text_format=2),
            CompletionItem("balance", CompletionItemKind.KEYWORD, "Load-balanced pool",
                           insert_text="balance {\n    strategy: ${1:least_loaded}\n    pool: [${2:agents}]\n    max_concurrent: ${3:5}\n}",
                           insert_text_format=2),
            CompletionItem("route", CompletionItemKind.KEYWORD, "Conditional routing",
                           insert_text="route {\n    if ${1:condition} then use: ${2:agent}\n    else use: ${3:fallback}\n}",
                           insert_text_format=2),
            CompletionItem("triton_ternary", CompletionItemKind.FUNCTION, "Triton ternary model",
                           insert_text='triton_ternary("${1:model-name}")',
                           insert_text_format=2),
            CompletionItem("best_for", CompletionItemKind.FUNCTION, "Best-fit selection",
                           insert_text="best_for(complexity: ${1:0.8}, max_cost: ${2:0.05}, quality: ${3:0.9})",
                           insert_text_format=2),
            CompletionItem("cheapest_above", CompletionItemKind.FUNCTION, "Cost-optimized",
                           insert_text="cheapest_above(quality_threshold: ${1:0.8})",
                           insert_text_format=2),
        ]

        # Add Triton models from registry
        for model in self._triton_models:
            name = model.get("name", "")
            desc = model.get("description", "Triton ternary model")
            items.append(CompletionItem(
                label=f'triton_ternary("{name}")',
                kind=CompletionItemKind.VALUE,
                detail=desc,
                documentation=f"**{name}**\n\n{desc}",
                insert_text=f'triton_ternary("{name}")',
            ))

        return items

    def _keyword_completions(self) -> list[CompletionItem]:
        """All keyword completions."""
        items = []
        for kw, doc in KEYWORD_DOCS.items():
            items.append(CompletionItem(
                label=kw,
                kind=CompletionItemKind.KEYWORD,
                detail=doc.get("detail", ""),
                documentation=doc.get("documentation", ""),
            ))
        return items

    def _snippet_completions(self) -> list[CompletionItem]:
        """All snippet completions."""
        items = []
        for s in SNIPPETS:
            items.append(CompletionItem(
                label=s["label"],
                kind=CompletionItemKind.SNIPPET,
                detail=s["detail"],
                documentation=s.get("documentation", ""),
                insert_text=s["insert_text"],
                insert_text_format=2,
            ))
        return items

    # ── Hover ────────────────────────────────────────────────────

    def hover(self, uri: str, line: int, character: int) -> dict | None:
        """Handle textDocument/hover."""
        text = self._documents.get(uri, "")
        lines = text.split("\n")

        if line >= len(lines):
            return None

        word = self._get_word_at(lines[line], character)
        if not word:
            return None

        # Check keyword docs
        doc = KEYWORD_DOCS.get(word)
        if doc:
            return {
                "contents": {
                    "kind": "markdown",
                    "value": f"**{word}** — {doc['detail']}\n\n{doc['documentation']}",
                },
                "range": self._word_range(lines[line], line, character, word),
            }

        # Check Triton models
        for model in self._triton_models:
            if model.get("name", "") in word:
                return {
                    "contents": {
                        "kind": "markdown",
                        "value": f"**Triton Model: {model['name']}**\n\n{model.get('description', '')}\n\n"
                                 f"- Compression: {model.get('compression', 'N/A')}\n"
                                 f"- Latency: {model.get('latency', 'N/A')}\n"
                                 f"- Accuracy: {model.get('accuracy', 'N/A')}",
                    },
                }

        return None

    def _get_word_at(self, line: str, character: int) -> str:
        """Extract the word at the given character position."""
        if character >= len(line):
            return ""

        start = character
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
            start -= 1

        end = character
        while end < len(line) and (line[end].isalnum() or line[end] == "_"):
            end += 1

        return line[start:end]

    def _word_range(self, line: str, line_num: int, character: int, word: str) -> dict:
        """Get the range of a word at a position."""
        idx = line.find(word)
        if idx == -1:
            idx = max(0, character - len(word))
        return Range(Position(line_num, idx), Position(line_num, idx + len(word))).to_dict()

    # ── Document Symbols ─────────────────────────────────────────

    def document_symbols(self, uri: str) -> list[dict]:
        """Handle textDocument/documentSymbol."""
        if uri in self._symbols_cache:
            return [s.to_dict() for s in self._symbols_cache[uri]]

        text = self._documents.get(uri, "")
        try:
            parser = Parser(text)
            workflows = parser.parse()
            symbols = self._build_symbols(text, workflows)
            self._symbols_cache[uri] = symbols
            return [s.to_dict() for s in symbols]
        except Exception:
            return []

    def _build_symbols(self, text: str, workflows: list) -> list[DocumentSymbol]:
        """Build document symbols from parsed workflows."""
        lines = text.split("\n")
        symbols: list[DocumentSymbol] = []

        for wf in workflows:
            name = getattr(wf, "name", "unknown")
            wf_line = self._find_keyword_line(lines, "workflow", name)
            wf_end = self._find_block_end(lines, wf_line)

            wf_range = Range(Position(wf_line, 0), Position(wf_end, 0))
            wf_sel = Range(Position(wf_line, 0), Position(wf_line, len(lines[wf_line]) if wf_line < len(lines) else 0))

            wf_symbol = DocumentSymbol(
                name=name,
                kind=SymbolKind.CLASS,
                range=wf_range,
                selection_range=wf_sel,
            )

            # Add child symbols for steps, gates, etc.
            body = getattr(wf, "body", [])
            for node in body:
                node_type = type(node).__name__
                if node_type == "StepNode":
                    step_name = getattr(node, "name", "step")
                    step_line = self._find_keyword_line(lines, "step", step_name)
                    step_range = Range(Position(step_line, 0), Position(step_line, 0))
                    wf_symbol.children.append(DocumentSymbol(
                        name=step_name,
                        kind=SymbolKind.METHOD,
                        range=step_range,
                        selection_range=step_range,
                    ))
                elif node_type == "ParallelNode":
                    par_line = self._find_keyword_line(lines, "parallel")
                    par_range = Range(Position(par_line, 0), Position(par_line, 0))
                    par_sym = DocumentSymbol(
                        name="parallel",
                        kind=SymbolKind.NAMESPACE,
                        range=par_range,
                        selection_range=par_range,
                    )
                    for step in getattr(node, "steps", []):
                        sn = getattr(step, "name", "step")
                        sl = self._find_keyword_line(lines, "step", sn)
                        sr = Range(Position(sl, 0), Position(sl, 0))
                        par_sym.children.append(DocumentSymbol(
                            name=sn, kind=SymbolKind.METHOD, range=sr, selection_range=sr,
                        ))
                    wf_symbol.children.append(par_sym)

            # Guard, budget, quality_gate
            if getattr(wf, "guard", None):
                gl = self._find_keyword_line(lines, "guard")
                gr = Range(Position(gl, 0), Position(gl, 0))
                wf_symbol.children.append(DocumentSymbol("guard", SymbolKind.EVENT, gr, gr))
            if getattr(wf, "budget", None):
                bl = self._find_keyword_line(lines, "budget")
                br = Range(Position(bl, 0), Position(bl, 0))
                wf_symbol.children.append(DocumentSymbol("budget", SymbolKind.PROPERTY, br, br))
            if getattr(wf, "quality_gate", None):
                ql = self._find_keyword_line(lines, "quality_gate")
                qr = Range(Position(ql, 0), Position(ql, 0))
                wf_symbol.children.append(DocumentSymbol("quality_gate", SymbolKind.EVENT, qr, qr))

            symbols.append(wf_symbol)

        return symbols

    def _find_block_end(self, lines: list[str], start_line: int) -> int:
        """Find the closing brace of a block starting at start_line."""
        depth = 0
        for i in range(start_line, len(lines)):
            depth += lines[i].count("{") - lines[i].count("}")
            if depth <= 0 and i > start_line:
                return i
        return len(lines) - 1

    # ── Semantic Tokens ──────────────────────────────────────────

    def semantic_tokens(self, uri: str) -> dict:
        """Handle textDocument/semanticTokens/full.

        Returns delta-encoded semantic tokens for syntax highlighting.
        """
        text = self._documents.get(uri, "")
        try:
            lexer = Lexer(text)
            tokens = lexer.tokenize()
        except LexerError:
            return {"data": []}

        data: list[int] = []
        prev_line = 0
        prev_col = 0

        for token in tokens:
            token_type_idx = _TOKEN_TYPE_MAP.get(token.type)
            if token_type_idx is None:
                continue

            line = max(0, token.line - 1)  # Convert 1-indexed to 0-indexed
            col = max(0, token.column)
            length = len(str(token.value)) if token.value else 1

            delta_line = line - prev_line
            delta_col = col - prev_col if delta_line == 0 else col

            data.extend([delta_line, delta_col, length, token_type_idx, 0])

            prev_line = line
            prev_col = col

        return {"data": data}

    # ── Server Capabilities ──────────────────────────────────────

    def capabilities(self) -> dict:
        """Return server capabilities for initialize response."""
        return {
            "textDocumentSync": {
                "openClose": True,
                "change": 1,  # Full sync
            },
            "completionProvider": {
                "triggerCharacters": [":", ".", " ", "{", "(", '"'],
                "resolveProvider": False,
            },
            "hoverProvider": True,
            "documentSymbolProvider": True,
            "semanticTokensProvider": {
                "full": True,
                "legend": {
                    "tokenTypes": SEMANTIC_TOKEN_TYPES,
                    "tokenModifiers": SEMANTIC_TOKEN_MODIFIERS,
                },
            },
        }

    # ── Triton Model Registry ────────────────────────────────────

    def register_triton_models(self, models: list[dict[str, str]]) -> None:
        """Register Triton ternary models for autocomplete.

        Each model dict should have: name, description, compression, latency, accuracy
        """
        self._triton_models = models


# ── JSON-RPC stdio transport ─────────────────────────────────────────

def run_stdio_server() -> None:
    """Run the language server over stdio JSON-RPC.

    Reads JSON-RPC messages from stdin, dispatches to the LSP server,
    and writes responses to stdout.
    """
    server = OrchestraLanguageServer()
    reader = sys.stdin.buffer
    writer = sys.stdout.buffer

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    logger.info("Orchestra Language Server starting (stdio)")

    while True:
        try:
            # Read Content-Length header
            header = b""
            while True:
                byte = reader.read(1)
                if not byte:
                    return  # EOF
                header += byte
                if header.endswith(b"\r\n\r\n"):
                    break

            # Parse Content-Length
            content_length = 0
            for line in header.decode("utf-8").split("\r\n"):
                if line.startswith("Content-Length:"):
                    content_length = int(line.split(":")[1].strip())
                    break

            if content_length == 0:
                continue

            # Read body
            body = reader.read(content_length)
            message = json.loads(body.decode("utf-8"))

            # Dispatch
            response = _dispatch(server, message)

            if response is not None:
                response_body = json.dumps(response).encode("utf-8")
                header = f"Content-Length: {len(response_body)}\r\n\r\n".encode("utf-8")
                writer.write(header)
                writer.write(response_body)
                writer.flush()

        except Exception:
            logger.exception("Error in message loop")


def _dispatch(server: OrchestraLanguageServer, message: dict) -> dict | None:
    """Dispatch a JSON-RPC message to the appropriate handler."""
    method = message.get("method", "")
    params = message.get("params", {})
    msg_id = message.get("id")

    result = None

    if method == "initialize":
        result = {
            "capabilities": server.capabilities(),
            "serverInfo": {"name": "orchestra-lsp", "version": "1.0.0"},
        }
    elif method == "initialized":
        return None  # Notification, no response
    elif method == "shutdown":
        result = None
    elif method == "exit":
        sys.exit(0)
    elif method == "textDocument/didOpen":
        td = params.get("textDocument", {})
        server.did_open(td.get("uri", ""), td.get("text", ""))
        return None  # Notification
    elif method == "textDocument/didChange":
        td = params.get("textDocument", {})
        changes = params.get("contentChanges", [])
        if changes:
            server.did_change(td.get("uri", ""), changes[0].get("text", ""))
        return None  # Notification
    elif method == "textDocument/didClose":
        td = params.get("textDocument", {})
        server.did_close(td.get("uri", ""))
        return None  # Notification
    elif method == "textDocument/completion":
        td = params.get("textDocument", {})
        pos = params.get("position", {})
        items = server.completion(td.get("uri", ""), pos.get("line", 0), pos.get("character", 0))
        result = {"isIncomplete": False, "items": items}
    elif method == "textDocument/hover":
        td = params.get("textDocument", {})
        pos = params.get("position", {})
        result = server.hover(td.get("uri", ""), pos.get("line", 0), pos.get("character", 0))
    elif method == "textDocument/documentSymbol":
        td = params.get("textDocument", {})
        result = server.document_symbols(td.get("uri", ""))
    elif method == "textDocument/semanticTokens/full":
        td = params.get("textDocument", {})
        result = server.semantic_tokens(td.get("uri", ""))
    else:
        if msg_id is not None:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        return None

    if msg_id is not None:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}
    return None


def main() -> None:
    """Entry point for the orchestra-lsp console script."""
    run_stdio_server()
