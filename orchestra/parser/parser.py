"""Recursive-descent parser for Orchestra .orc files.

Converts a token stream (from ``Lexer``) into an AST of nodes
defined in ``ast_nodes``.
"""

from __future__ import annotations

from typing import Any, List, Optional

from orchestra.parser.lexer import Lexer, Token, TokenType
from orchestra.parser.ast_nodes import (
    AgentRef,
    AgentType,
    BalanceAgent,
    BestForAgent,
    BudgetNode,
    CascadeAgent,
    CatchClause,
    CheapestAboveAgent,
    CircuitBreakerNode,
    Expression,
    FinallyNode,
    ForEachNode,
    GuardNode,
    IfNode,
    MatchCase,
    MatchNode,
    OnPartialFailureNode,
    ParallelNode,
    PropertyAssignment,
    QualityGateNode,
    RetryConfig,
    RouteAgent,
    SelectAgent,
    StepNode,
    TimeoutNode,
    TritonAgent,
    TryNode,
    ValidateOutputNode,
    WorkflowNode,
)


class ParseError(Exception):
    """Raised when the parser encounters a syntax error."""

    def __init__(self, message: str, token: Optional[Token] = None):
        self.token = token
        loc = ""
        if token:
            loc = f" at line {token.line}, column {token.column}"
        super().__init__(f"Parse error{loc}: {message}")


class Parser:
    """Recursive-descent parser for .orc files.

    Usage::

        parser = Parser(source_text)
        workflows = parser.parse()  # list of WorkflowNode
    """

    def __init__(self, source: str):
        self.lexer = Lexer(source)
        self.tokens: List[Token] = []
        self.pos = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> List[WorkflowNode]:
        """Parse the full source and return a list of top-level workflows."""
        self.tokens = self.lexer.tokenize()
        self.pos = 0
        workflows: List[WorkflowNode] = []

        self._skip_newlines()
        while not self._at_end():
            self._skip_newlines()
            if self._at_end():
                break
            if self._check(TokenType.WORKFLOW):
                workflows.append(self._parse_workflow())
            else:
                # Skip unknown top-level tokens (e.g. markdown headers in .orc files)
                self._advance()
            self._skip_newlines()

        return workflows

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    def _current(self) -> Token:
        if self.pos >= len(self.tokens):
            return self.tokens[-1]  # EOF
        return self.tokens[self.pos]

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]

    def _at_end(self) -> bool:
        return self._current().type == TokenType.EOF

    def _check(self, *types: TokenType) -> bool:
        return self._current().type in types

    def _match(self, *types: TokenType) -> Optional[Token]:
        if self._current().type in types:
            return self._advance()
        return None

    def _expect(self, ttype: TokenType, msg: str = "") -> Token:
        tok = self._current()
        if tok.type != ttype:
            expected = msg or ttype.name
            raise ParseError(
                f"Expected {expected}, got {tok.type.name} ({tok.value!r})", tok
            )
        return self._advance()

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def _skip_newlines(self):
        while self._check(TokenType.NEWLINE):
            self._advance()

    def _skip_to_next_meaningful(self):
        """Skip newlines and commas (commas are optional separators)."""
        while self._check(TokenType.NEWLINE, TokenType.COMMA):
            self._advance()

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    def _parse_workflow(self) -> WorkflowNode:
        self._expect(TokenType.WORKFLOW)
        name_tok = self._expect(TokenType.IDENTIFIER, "workflow name")
        self._skip_newlines()
        self._expect(TokenType.LBRACE)

        node = WorkflowNode(name=name_tok.value, line=name_tok.line)
        self._parse_workflow_body(node)

        self._skip_newlines()
        self._expect(TokenType.RBRACE)
        return node

    def _parse_workflow_body(self, wf: WorkflowNode):
        """Parse the contents between workflow { … }."""
        while True:
            self._skip_newlines()
            if self._check(TokenType.RBRACE, TokenType.EOF):
                break
            self._parse_workflow_item(wf)

    def _parse_workflow_item(self, wf: WorkflowNode):
        """Parse a single item inside a workflow body."""
        tok = self._current()

        if tok.type == TokenType.VERSION:
            wf.version = self._parse_simple_property()
        elif tok.type == TokenType.OWNER:
            wf.owner = self._parse_simple_property()
        elif tok.type == TokenType.PROTECTED_BY:
            wf.protected_by = self._parse_simple_property()
        elif tok.type == TokenType.CRITICALITY:
            wf.criticality = self._parse_simple_property()
        elif tok.type == TokenType.GUARD:
            wf.guard = self._parse_guard()
        elif tok.type == TokenType.BUDGET:
            wf.budget = self._parse_budget()
        elif tok.type == TokenType.CIRCUIT_BREAKER:
            wf.circuit_breaker = self._parse_circuit_breaker()
        elif tok.type == TokenType.AGENT:
            wf.agent = self._parse_agent_declaration()
        elif tok.type == TokenType.STEP:
            wf.body.append(self._parse_step())
        elif tok.type == TokenType.PARALLEL:
            wf.body.append(self._parse_parallel())
        elif tok.type == TokenType.IF:
            wf.body.append(self._parse_if())
        elif tok.type == TokenType.MATCH:
            wf.body.append(self._parse_match())
        elif tok.type == TokenType.TRY:
            wf.body.append(self._parse_try())
        elif tok.type == TokenType.QUALITY_GATE:
            wf.quality_gate = self._parse_quality_gate()
        elif tok.type == TokenType.FINALLY:
            wf.finally_block = self._parse_finally()
        elif tok.type == TokenType.ON_PARTIAL_FAILURE:
            wf.body.append(self._parse_on_partial_failure())
        elif tok.type == TokenType.FOR:
            wf.body.append(self._parse_for_each())
        else:
            # Unknown — skip token
            self._advance()

    # ------------------------------------------------------------------
    # Simple key: value property
    # ------------------------------------------------------------------

    def _parse_simple_property(self) -> str:
        """Parse ``keyword: value`` and return the value as a string."""
        self._advance()  # consume keyword
        self._skip_newlines()
        self._expect(TokenType.COLON)
        self._skip_newlines()
        return self._parse_value_as_string()

    def _parse_value_as_string(self) -> str:
        tok = self._current()
        if tok.type == TokenType.STRING:
            self._advance()
            return tok.value
        if tok.type == TokenType.NUMBER:
            self._advance()
            return tok.value
        if tok.type == TokenType.BOOL_TRUE:
            self._advance()
            return "true"
        if tok.type == TokenType.BOOL_FALSE:
            self._advance()
            return "false"
        if tok.type == TokenType.NULL:
            self._advance()
            return "null"
        # Identifier (possibly dotted)
        if tok.type == TokenType.IDENTIFIER or tok.type in KEYWORD_SET:
            return self._parse_dotted_identifier()
        raise ParseError(f"Expected value, got {tok.type.name}", tok)

    def _parse_dotted_identifier(self) -> str:
        """Parse ``a.b.c`` → 'a.b.c'."""
        parts = [self._advance().value]
        while self._check(TokenType.DOT):
            self._advance()
            parts.append(self._advance().value)
        return ".".join(parts)

    def _parse_value(self) -> Any:
        """Parse a value and return it as the appropriate Python type."""
        tok = self._current()
        if tok.type == TokenType.STRING:
            self._advance()
            return tok.value
        if tok.type == TokenType.NUMBER:
            self._advance()
            return float(tok.value) if "." in tok.value else int(tok.value)
        if tok.type == TokenType.BOOL_TRUE:
            self._advance()
            return True
        if tok.type == TokenType.BOOL_FALSE:
            self._advance()
            return False
        if tok.type == TokenType.NULL:
            self._advance()
            return None
        if tok.type == TokenType.LBRACKET:
            return self._parse_list()
        if tok.type == TokenType.LBRACE:
            return self._parse_dict_or_block_value()
        if tok.type == TokenType.IDENTIFIER or tok.type in KEYWORD_SET:
            return self._parse_dotted_identifier()
        raise ParseError(f"Expected value, got {tok.type.name}", tok)

    def _parse_list(self) -> List[Any]:
        """Parse ``[v1, v2, …]``."""
        self._expect(TokenType.LBRACKET)
        items: List[Any] = []
        self._skip_to_next_meaningful()
        while not self._check(TokenType.RBRACKET, TokenType.EOF):
            items.append(self._parse_value())
            self._skip_to_next_meaningful()
        self._expect(TokenType.RBRACKET)
        return items

    def _parse_dict_or_block_value(self) -> dict:
        """Parse ``{ key: value, … }`` into a dict."""
        self._expect(TokenType.LBRACE)
        d: dict = {}
        self._skip_to_next_meaningful()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            # key
            key_tok = self._current()
            if key_tok.type in (TokenType.IDENTIFIER, *KEYWORD_SET):
                key = self._advance().value
            elif key_tok.type == TokenType.STRING:
                key = self._advance().value
            else:
                # bare identifier without colon → list-like dict entry
                key = self._advance().value
                d[key] = True
                self._skip_to_next_meaningful()
                continue

            # optional colon
            if self._check(TokenType.COLON):
                self._advance()
                self._skip_newlines()
                val = self._parse_value()
                d[key] = val
            else:
                d[key] = True
            self._skip_to_next_meaningful()
        self._expect(TokenType.RBRACE)
        return d

    # ------------------------------------------------------------------
    # Agent declarations
    # ------------------------------------------------------------------

    def _parse_agent_declaration(self) -> AgentType:
        """Parse ``agent: <agent_spec>``."""
        self._advance()  # consume 'agent'
        self._skip_newlines()
        self._expect(TokenType.COLON)
        self._skip_newlines()
        return self._parse_agent_spec()

    def _parse_agent_spec(self) -> AgentType:
        """Parse the right-hand side of ``agent:``."""
        tok = self._current()

        if tok.type == TokenType.CASCADE:
            return self._parse_cascade_agent()
        if tok.type == TokenType.BALANCE:
            return self._parse_balance_agent()
        if tok.type == TokenType.ROUTE:
            return self._parse_route_agent()
        if tok.type == TokenType.SELECT:
            return self._parse_select_agent()
        if tok.type == TokenType.TRITON_TERNARY:
            return self._parse_triton_agent()
        if tok.type == TokenType.BEST_FOR:
            return self._parse_best_for_agent()
        if tok.type == TokenType.CHEAPEST_ABOVE:
            return self._parse_cheapest_above_agent()
        # Simple named agent
        name = self._parse_dotted_identifier()
        return AgentRef(name=name)

    def _parse_cascade_agent(self) -> CascadeAgent:
        self._advance()  # 'cascade'
        self._skip_newlines()
        self._expect(TokenType.LBRACKET)
        agent = CascadeAgent(try_agent="")
        self._skip_to_next_meaningful()
        while not self._check(TokenType.RBRACKET, TokenType.EOF):
            key_tok = self._current()
            key = self._advance().value
            self._skip_newlines()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            val = self._parse_value_as_string()
            if key == "try":
                agent.try_agent = val
            elif key == "fallback":
                agent.fallback = val
            elif key == "last_resort":
                agent.last_resort = val
            self._skip_to_next_meaningful()
        self._expect(TokenType.RBRACKET)
        return agent

    def _parse_balance_agent(self) -> BalanceAgent:
        self._advance()  # 'balance'
        self._skip_newlines()
        self._expect(TokenType.LBRACE)
        agent = BalanceAgent(strategy="round_robin")
        self._skip_to_next_meaningful()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            key = self._advance().value
            self._skip_newlines()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            if key == "strategy":
                agent.strategy = self._parse_value_as_string()
            elif key == "pool":
                agent.pool = self._parse_list()
            elif key == "max_concurrent":
                agent.max_concurrent = int(self._parse_value_as_string())
            else:
                self._parse_value()  # skip unknown
            self._skip_to_next_meaningful()
        self._expect(TokenType.RBRACE)
        return agent

    def _parse_route_agent(self) -> RouteAgent:
        self._advance()  # 'route'
        self._skip_newlines()
        self._expect(TokenType.LBRACE)
        agent = RouteAgent()
        self._skip_to_next_meaningful()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._current()
            if tok.type == TokenType.IF:
                self._advance()
                expr = self._parse_inline_expression()
                self._skip_newlines()
                self._expect(TokenType.THEN, "'then'")
                self._skip_newlines()
                target = self._parse_value_as_string()
                agent.rules.append(PropertyAssignment(key=expr, value=target, line=tok.line))
            elif tok.type == TokenType.ELSE:
                self._advance()
                self._skip_newlines()
                agent.default = self._parse_value_as_string()
            else:
                self._advance()
            self._skip_to_next_meaningful()
        self._expect(TokenType.RBRACE)
        return agent

    def _parse_select_agent(self) -> SelectAgent:
        self._advance()  # 'select'
        self._skip_newlines()
        self._expect(TokenType.LBRACE)
        agent = SelectAgent()
        self._skip_to_next_meaningful()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            key = self._advance().value
            self._skip_newlines()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            if key == "metric":
                agent.metric = self._parse_value_as_string()
            elif key == "timeframe":
                agent.timeframe = self._parse_value_as_string()
            elif key == "optimize_for":
                agent.optimize_for = self._parse_list()
            elif key == "weights":
                agent.weights = [float(x) for x in self._parse_list()]
            elif key == "candidates":
                agent.candidates = self._parse_list()
            elif key == "fallback":
                agent.fallback = self._parse_value_as_string()
            else:
                self._parse_value()
            self._skip_to_next_meaningful()
        self._expect(TokenType.RBRACE)
        return agent

    def _parse_triton_agent(self) -> TritonAgent:
        self._advance()  # 'triton_ternary'
        self._expect(TokenType.LPAREN)
        name_tok = self._expect(TokenType.STRING, "model name")
        self._expect(TokenType.RPAREN)
        return TritonAgent(model_name=name_tok.value)

    def _parse_best_for_agent(self) -> BestForAgent:
        self._advance()  # 'best_for'
        self._expect(TokenType.LPAREN)
        agent = BestForAgent()
        self._skip_to_next_meaningful()
        while not self._check(TokenType.RPAREN, TokenType.EOF):
            key = self._advance().value
            self._skip_newlines()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            val = self._parse_value()
            agent.properties[key] = val
            self._skip_to_next_meaningful()
        self._expect(TokenType.RPAREN)
        return agent

    def _parse_cheapest_above_agent(self) -> CheapestAboveAgent:
        self._advance()  # 'cheapest_above'
        self._expect(TokenType.LPAREN)
        agent = CheapestAboveAgent()
        self._skip_to_next_meaningful()
        while not self._check(TokenType.RPAREN, TokenType.EOF):
            key = self._advance().value
            self._skip_newlines()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            val = self._parse_value()
            if key == "quality_threshold":
                agent.quality_threshold = float(val)
            self._skip_to_next_meaningful()
        self._expect(TokenType.RPAREN)
        return agent

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def _parse_step(self) -> StepNode:
        line = self._current().line
        self._advance()  # 'step'
        self._skip_newlines()
        name_tok = self._expect(TokenType.IDENTIFIER, "step name")
        self._skip_newlines()
        self._expect(TokenType.LBRACE)

        step = StepNode(name=name_tok.value, line=line)
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            self._parse_step_item(step)
            self._skip_newlines()
        self._expect(TokenType.RBRACE)
        return step

    def _parse_step_item(self, step: StepNode):
        tok = self._current()

        if tok.type == TokenType.AGENT:
            step.agent = self._parse_agent_declaration()
        elif tok.type == TokenType.MODEL:
            step.model = self._parse_simple_property()
        elif tok.type == TokenType.TASK:
            step.task = self._parse_simple_property()
        elif tok.type == TokenType.TIMEOUT:
            step.timeout = self._parse_timeout()
        elif tok.type == TokenType.VALIDATE_OUTPUT:
            step.validate_output = self._parse_validate_output()
        elif tok.type == TokenType.TRY:
            step.body.append(self._parse_try())
        elif tok.type in (TokenType.NOTIFY, TokenType.PRIORITY, TokenType.ACTION,
                           TokenType.CONTEXT, TokenType.ALERT):
            key = self._advance().value
            self._skip_newlines()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            val = self._parse_value()
            step.properties.append(PropertyAssignment(key=key, value=val, line=tok.line))
        elif tok.type == TokenType.FOR:
            step.body.append(self._parse_for_each())
        elif tok.type == TokenType.DATA:
            key = self._advance().value
            self._skip_newlines()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            val = self._parse_value()
            step.properties.append(PropertyAssignment(key=key, value=val, line=tok.line))
        else:
            # Generic property or unknown — skip
            key = self._advance().value
            if self._check(TokenType.COLON):
                self._advance()
                self._skip_newlines()
                val = self._parse_value()
                step.properties.append(PropertyAssignment(key=key, value=val, line=tok.line))

    # ------------------------------------------------------------------
    # Parallel
    # ------------------------------------------------------------------

    def _parse_parallel(self) -> ParallelNode:
        line = self._current().line
        self._advance()  # 'parallel'
        self._skip_newlines()
        self._expect(TokenType.LBRACE)

        node = ParallelNode(line=line)
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._current()
            if tok.type == TokenType.STEP:
                node.steps.append(self._parse_step())
            else:
                self._advance()
            self._skip_newlines()
        self._expect(TokenType.RBRACE)

        # Check for trailing on_partial_failure
        self._skip_newlines()
        if self._check(TokenType.ON_PARTIAL_FAILURE):
            node.on_partial_failure = self._parse_on_partial_failure()

        return node

    # ------------------------------------------------------------------
    # If / else if / else
    # ------------------------------------------------------------------

    def _parse_if(self) -> IfNode:
        line = self._current().line
        self._advance()  # 'if'
        condition = self._parse_expression()
        self._skip_newlines()
        self._expect(TokenType.LBRACE)

        node = IfNode(condition=condition, line=line)
        node.body = self._parse_body_items()
        self._expect(TokenType.RBRACE)

        # else if / else
        self._skip_newlines()
        while self._check(TokenType.ELSE):
            self._advance()  # 'else'
            self._skip_newlines()
            if self._check(TokenType.IF):
                # else if
                elif_node = self._parse_if()
                node.elif_branches.append(elif_node)
                break  # the recursive parse_if handles further chains
            else:
                # else
                self._expect(TokenType.LBRACE)
                node.else_body = self._parse_body_items()
                self._expect(TokenType.RBRACE)
                break

        return node

    # ------------------------------------------------------------------
    # Match / case
    # ------------------------------------------------------------------

    def _parse_match(self) -> MatchNode:
        line = self._current().line
        self._advance()  # 'match'
        expr = self._parse_inline_expression()
        self._skip_newlines()
        self._expect(TokenType.LBRACE)

        node = MatchNode(expression=expr, line=line)
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._current()
            if tok.type == TokenType.CASE:
                self._advance()
                val_tok = self._current()
                val = self._parse_value_as_string()
                self._skip_newlines()
                self._expect(TokenType.ARROW)
                self._skip_newlines()
                self._expect(TokenType.LBRACE)
                body = self._parse_body_items()
                self._expect(TokenType.RBRACE)
                node.cases.append(MatchCase(value=val, body=body, line=val_tok.line))
            elif tok.type == TokenType.DEFAULT:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.ARROW)
                self._skip_newlines()
                self._expect(TokenType.LBRACE)
                body = self._parse_body_items()
                self._expect(TokenType.RBRACE)
                node.default = MatchCase(value="default", body=body, line=tok.line)
            else:
                self._advance()
            self._skip_newlines()
        self._expect(TokenType.RBRACE)
        return node

    # ------------------------------------------------------------------
    # For each
    # ------------------------------------------------------------------

    def _parse_for_each(self) -> ForEachNode:
        line = self._current().line
        self._advance()  # 'for'
        self._skip_newlines()
        self._expect(TokenType.EACH, "'each'")
        self._skip_newlines()
        var_tok = self._expect(TokenType.IDENTIFIER, "iterator variable")
        self._skip_newlines()
        self._expect(TokenType.IN, "'in'")
        self._skip_newlines()
        collection = self._parse_dotted_identifier()
        self._skip_newlines()
        self._expect(TokenType.LBRACE)
        body = self._parse_body_items()
        self._expect(TokenType.RBRACE)
        return ForEachNode(variable=var_tok.value, collection=collection, body=body, line=line)

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    def _parse_guard(self) -> GuardNode:
        line = self._current().line
        self._advance()  # 'guard'
        self._skip_newlines()
        self._expect(TokenType.LBRACE)

        node = GuardNode(line=line)
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._current()
            if tok.type == TokenType.REQUIRE:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.requirements.append(self._parse_expression())
            elif tok.type == TokenType.ON_VIOLATION:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.on_violation = self._parse_value_as_string()
                # Handle function-call style: reject("...")
                if self._check(TokenType.LPAREN):
                    self._advance()
                    if self._check(TokenType.STRING):
                        node.on_violation = self._advance().value
                    self._skip_to_next_meaningful()
                    if self._check(TokenType.RPAREN):
                        self._advance()
            else:
                self._advance()
            self._skip_newlines()
        self._expect(TokenType.RBRACE)
        return node

    # ------------------------------------------------------------------
    # Budget
    # ------------------------------------------------------------------

    def _parse_budget(self) -> BudgetNode:
        line = self._current().line
        self._advance()  # 'budget'
        self._skip_newlines()
        self._expect(TokenType.LBRACE)

        node = BudgetNode(line=line)
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            key = self._advance().value
            self._skip_newlines()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            val = self._parse_value()
            if key == "per_task":
                node.per_task = float(val)
            elif key == "hourly_limit":
                node.hourly_limit = float(val)
            elif key == "alert_at":
                node.alert_at = float(val)
            self._skip_to_next_meaningful()
        self._expect(TokenType.RBRACE)
        return node

    # ------------------------------------------------------------------
    # Circuit breaker
    # ------------------------------------------------------------------

    def _parse_circuit_breaker(self) -> CircuitBreakerNode:
        line = self._current().line
        self._advance()  # 'circuit_breaker'
        self._skip_newlines()
        self._expect(TokenType.LBRACE)

        node = CircuitBreakerNode(line=line)
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            key = self._advance().value
            self._skip_newlines()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            if key == "failure_threshold":
                node.failure_threshold = int(self._parse_value())
            elif key == "timeout":
                node.timeout = float(self._parse_value())
            elif key == "half_open_after":
                node.half_open_after = float(self._parse_value())
            elif key == "on_open":
                node.on_open = self._parse_value()
            else:
                self._parse_value()
            self._skip_to_next_meaningful()
        self._expect(TokenType.RBRACE)
        return node

    # ------------------------------------------------------------------
    # Quality gate
    # ------------------------------------------------------------------

    def _parse_quality_gate(self) -> QualityGateNode:
        line = self._current().line
        self._advance()  # 'quality_gate'
        self._skip_newlines()
        self._expect(TokenType.LBRACE)

        node = QualityGateNode(line=line)
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._current()
            if tok.type == TokenType.METRICS:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.metrics = self._parse_dict_or_block_value()
            elif tok.type == TokenType.ON_FAILURE:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.LBRACE)
                node.on_failure = self._parse_body_items()
                self._expect(TokenType.RBRACE)
            else:
                self._advance()
            self._skip_to_next_meaningful()
        self._expect(TokenType.RBRACE)
        return node

    # ------------------------------------------------------------------
    # Timeout
    # ------------------------------------------------------------------

    def _parse_timeout(self) -> TimeoutNode:
        self._advance()  # 'timeout'
        self._skip_newlines()

        # Simple form: timeout: 10.0
        if self._check(TokenType.COLON):
            self._advance()
            self._skip_newlines()
            val = float(self._parse_value())
            return TimeoutNode(hard=val)

        # Block form: timeout { soft: … hard: … }
        self._expect(TokenType.LBRACE)
        node = TimeoutNode()
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._current()
            key = tok.value
            if tok.type == TokenType.SOFT:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.soft = float(self._parse_value())
            elif tok.type == TokenType.HARD:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.hard = float(self._parse_value())
            elif tok.type == TokenType.ON_SOFT_TIMEOUT:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.on_soft_timeout = self._parse_value()
            elif tok.type == TokenType.ON_HARD_TIMEOUT:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.on_hard_timeout = self._parse_value()
            elif tok.type == TokenType.ON_TIMEOUT:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.on_timeout = self._parse_value()
            else:
                self._advance()
                if self._check(TokenType.COLON):
                    self._advance()
                    self._skip_newlines()
                    self._parse_value()
            self._skip_to_next_meaningful()
        self._expect(TokenType.RBRACE)
        return node

    # ------------------------------------------------------------------
    # Validate output
    # ------------------------------------------------------------------

    def _parse_validate_output(self) -> ValidateOutputNode:
        self._advance()  # 'validate_output'
        self._skip_newlines()
        self._expect(TokenType.LBRACE)

        node = ValidateOutputNode()
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._current()
            if tok.type == TokenType.ASSERT:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.assertions.append(self._parse_expression())
            elif tok.type == TokenType.ON_VALIDATION_FAILURE:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.on_validation_failure = self._parse_value()
            else:
                self._advance()
            self._skip_newlines()
        self._expect(TokenType.RBRACE)
        return node

    # ------------------------------------------------------------------
    # On partial failure
    # ------------------------------------------------------------------

    def _parse_on_partial_failure(self) -> OnPartialFailureNode:
        self._advance()  # 'on_partial_failure'
        self._skip_newlines()
        self._expect(TokenType.LBRACE)

        node = OnPartialFailureNode()
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._current()
            key = tok.value
            if tok.type == TokenType.STRATEGY:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.strategy = self._parse_value_as_string()
            elif tok.type == TokenType.MIN_SUCCESS_RATE:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.min_success_rate = float(self._parse_value())
            elif tok.type == TokenType.ON_BELOW_THRESHOLD:
                self._advance()
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                node.on_below_threshold = self._parse_value()
            else:
                self._advance()
                if self._check(TokenType.COLON):
                    self._advance()
                    self._skip_newlines()
                    self._parse_value()
            self._skip_to_next_meaningful()
        self._expect(TokenType.RBRACE)
        return node

    # ------------------------------------------------------------------
    # Try / retry / catch
    # ------------------------------------------------------------------

    def _parse_try(self) -> TryNode:
        line = self._current().line
        self._advance()  # 'try'
        self._skip_newlines()
        self._expect(TokenType.LBRACE)
        body = self._parse_body_items()
        self._expect(TokenType.RBRACE)

        node = TryNode(body=body, line=line)

        # Optional retry block
        self._skip_newlines()
        if self._check(TokenType.RETRY):
            node.retry = self._parse_retry_config()

        # Optional catch blocks
        self._skip_newlines()
        while self._check(TokenType.CATCH):
            node.catches.append(self._parse_catch())
            self._skip_newlines()

        # on_error variant
        if self._check(TokenType.ON_ERROR):
            self._advance()
            self._skip_newlines()
            self._expect(TokenType.LBRACE)
            catch_body = self._parse_body_items()
            self._expect(TokenType.RBRACE)
            node.catches.append(CatchClause(error_type="any_error", body=catch_body, line=line))

        return node

    def _parse_retry_config(self) -> RetryConfig:
        line = self._current().line
        self._advance()  # 'retry'
        self._skip_newlines()

        # retry(max: N) shorthand
        if self._check(TokenType.LPAREN):
            self._advance()
            cfg = RetryConfig(line=line)
            self._skip_to_next_meaningful()
            while not self._check(TokenType.RPAREN, TokenType.EOF):
                key = self._advance().value
                self._skip_newlines()
                self._expect(TokenType.COLON)
                self._skip_newlines()
                val = self._parse_value()
                if key == "max":
                    cfg.max_attempts = int(val)
                self._skip_to_next_meaningful()
            self._expect(TokenType.RPAREN)
            return cfg

        self._expect(TokenType.LBRACE)
        cfg = RetryConfig(line=line)
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            key = self._advance().value
            self._skip_newlines()
            self._expect(TokenType.COLON)
            self._skip_newlines()
            if key == "strategy":
                cfg.strategy = self._parse_value_as_string()
            elif key == "max_attempts":
                cfg.max_attempts = int(self._parse_value())
            elif key == "initial_delay":
                cfg.initial_delay = float(self._parse_value())
            elif key == "max_delay":
                cfg.max_delay = float(self._parse_value())
            else:
                self._parse_value()
            self._skip_to_next_meaningful()
        self._expect(TokenType.RBRACE)
        return cfg

    def _parse_catch(self) -> CatchClause:
        line = self._current().line
        self._advance()  # 'catch'
        self._skip_newlines()
        error_type = self._advance().value  # e.g. timeout_error, any_error
        self._skip_newlines()
        self._expect(TokenType.LBRACE)
        body = self._parse_body_items()
        self._expect(TokenType.RBRACE)
        return CatchClause(error_type=error_type, body=body, line=line)

    # ------------------------------------------------------------------
    # Finally
    # ------------------------------------------------------------------

    def _parse_finally(self) -> FinallyNode:
        line = self._current().line
        self._advance()  # 'finally'
        self._skip_newlines()
        self._expect(TokenType.LBRACE)
        body = self._parse_body_items()
        self._expect(TokenType.RBRACE)
        return FinallyNode(body=body, line=line)

    # ------------------------------------------------------------------
    # Expression parsing (simple comparisons for guards/conditions)
    # ------------------------------------------------------------------

    def _parse_expression(self) -> Expression:
        """Parse a simple expression like ``input.amount > 1000`` or
        ``result.score in ["A", "B"]``.

        Returns an Expression with raw text and parsed structure.
        """
        parts: list[str] = []
        left = self._parse_expr_atom()
        parts.append(left)

        # Check for operator
        op = None
        if self._check(TokenType.GT, TokenType.LT, TokenType.GTE, TokenType.LTE,
                        TokenType.EQ, TokenType.NEQ):
            op_tok = self._advance()
            op = op_tok.value
            parts.append(op)
            right = self._parse_expr_atom()
            parts.append(right)
            return Expression(raw=" ".join(parts), left=left, operator=op, right=right)

        # 'in' operator
        if self._check(TokenType.IN):
            self._advance()
            parts.append("in")
            right = self._parse_expr_atom()
            parts.append(right)
            return Expression(raw=" ".join(parts), left=left, operator="in", right=right)

        return Expression(raw=" ".join(parts), left=left)

    def _parse_expr_atom(self) -> str:
        """Parse a single expression atom (identifier, number, string, list)."""
        tok = self._current()
        if tok.type == TokenType.STRING:
            self._advance()
            return f'"{tok.value}"'
        if tok.type == TokenType.NUMBER:
            self._advance()
            return tok.value
        if tok.type == TokenType.NULL:
            self._advance()
            return "null"
        if tok.type == TokenType.BOOL_TRUE:
            self._advance()
            return "true"
        if tok.type == TokenType.BOOL_FALSE:
            self._advance()
            return "false"
        if tok.type == TokenType.LBRACKET:
            items = self._parse_list()
            return str(items)
        if tok.type == TokenType.IDENTIFIER or tok.type in KEYWORD_SET:
            return self._parse_dotted_identifier()
        # Function call patterns like len(…), reject(…)
        self._advance()
        return tok.value

    def _parse_inline_expression(self) -> str:
        """Parse tokens until we hit a keyword boundary (then, {, }, etc.).
        Returns raw text."""
        parts: list[str] = []
        stop_types = {
            TokenType.THEN, TokenType.LBRACE, TokenType.RBRACE,
            TokenType.ARROW, TokenType.NEWLINE, TokenType.EOF,
        }
        while self._current().type not in stop_types:
            tok = self._advance()
            parts.append(tok.value)
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Generic body parser (shared by if/else/match/try/catch/finally)
    # ------------------------------------------------------------------

    def _parse_body_items(self) -> List[Any]:
        """Parse items until we hit a closing brace."""
        items: List[Any] = []
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            tok = self._current()
            if tok.type == TokenType.STEP:
                items.append(self._parse_step())
            elif tok.type == TokenType.PARALLEL:
                items.append(self._parse_parallel())
            elif tok.type == TokenType.IF:
                items.append(self._parse_if())
            elif tok.type == TokenType.MATCH:
                items.append(self._parse_match())
            elif tok.type == TokenType.TRY:
                items.append(self._parse_try())
            elif tok.type == TokenType.FOR:
                items.append(self._parse_for_each())
            elif tok.type == TokenType.FINALLY:
                items.append(self._parse_finally())
            elif tok.type == TokenType.QUALITY_GATE:
                items.append(self._parse_quality_gate())
            elif tok.type == TokenType.ON_PARTIAL_FAILURE:
                items.append(self._parse_on_partial_failure())
            elif tok.type == TokenType.AGENT:
                # agent: … as a standalone property in body
                agent = self._parse_agent_declaration()
                items.append(PropertyAssignment(key="agent", value=agent, line=tok.line))
            elif tok.type == TokenType.MODEL:
                items.append(PropertyAssignment(
                    key="model", value=self._parse_simple_property(), line=tok.line
                ))
            elif tok.type == TokenType.TASK:
                items.append(PropertyAssignment(
                    key="task", value=self._parse_simple_property(), line=tok.line
                ))
            elif tok.type == TokenType.TIMEOUT:
                items.append(self._parse_timeout())
            elif tok.type == TokenType.VALIDATE_OUTPUT:
                items.append(self._parse_validate_output())
            elif tok.type in (TokenType.ALERT, TokenType.LOG, TokenType.NOTIFY,
                               TokenType.ACTION, TokenType.RETURN, TokenType.CONTINUE,
                               TokenType.ABORT_WORKFLOW, TokenType.MARK_FOR_RETRY,
                               TokenType.DEGRADE_TO, TokenType.FALLBACK, TokenType.CAPTURE,
                               TokenType.LEVEL, TokenType.MESSAGE, TokenType.CONTEXT,
                               TokenType.DATA, TokenType.PRIORITY):
                key = self._advance().value
                if self._check(TokenType.COLON):
                    self._advance()
                    self._skip_newlines()
                    val = self._parse_value()
                    items.append(PropertyAssignment(key=key, value=val, line=tok.line))
                else:
                    items.append(PropertyAssignment(key=key, value=True, line=tok.line))
            elif tok.type == TokenType.IDENTIFIER:
                key = self._advance().value
                if self._check(TokenType.COLON):
                    self._advance()
                    self._skip_newlines()
                    val = self._parse_value()
                    items.append(PropertyAssignment(key=key, value=val, line=tok.line))
                else:
                    items.append(PropertyAssignment(key=key, value=True, line=tok.line))
            else:
                self._advance()
            self._skip_newlines()
        return items


# Set of all keyword TokenTypes (for allowing keywords as identifiers in some contexts)
KEYWORD_SET: set[TokenType] = {
    TokenType.WORKFLOW, TokenType.STEP, TokenType.PARALLEL, TokenType.IF,
    TokenType.ELSE, TokenType.MATCH, TokenType.CASE, TokenType.DEFAULT,
    TokenType.GUARD, TokenType.BUDGET, TokenType.CIRCUIT_BREAKER,
    TokenType.QUALITY_GATE, TokenType.TRY, TokenType.RETRY, TokenType.CATCH,
    TokenType.FINALLY, TokenType.FOR, TokenType.EACH, TokenType.IN,
    TokenType.THEN, TokenType.ON_PARTIAL_FAILURE, TokenType.ON_FAILURE,
    TokenType.ON_ERROR, TokenType.ON_VIOLATION, TokenType.ON_OPEN,
    TokenType.ON_TIMEOUT, TokenType.ON_SOFT_TIMEOUT, TokenType.ON_HARD_TIMEOUT,
    TokenType.REQUIRE, TokenType.ASSERT, TokenType.VALIDATE_OUTPUT,
    TokenType.TIMEOUT, TokenType.AGENT, TokenType.MODEL, TokenType.TASK,
    TokenType.ACTION, TokenType.CASCADE, TokenType.BALANCE, TokenType.ROUTE,
    TokenType.SELECT, TokenType.TRITON_TERNARY, TokenType.BEST_FOR,
    TokenType.CHEAPEST_ABOVE, TokenType.VERSION, TokenType.OWNER,
    TokenType.PROTECTED_BY, TokenType.CRITICALITY, TokenType.PRIORITY,
    TokenType.NOTIFY, TokenType.ALERT, TokenType.LOG, TokenType.DATA,
    TokenType.STRATEGY, TokenType.POOL, TokenType.MAX_CONCURRENT,
    TokenType.FALLBACK, TokenType.LAST_RESORT, TokenType.DEGRADE_TO,
    TokenType.RETURN, TokenType.CONTINUE, TokenType.ABORT_WORKFLOW,
    TokenType.MARK_FOR_RETRY, TokenType.SOFT, TokenType.HARD,
    TokenType.METRICS, TokenType.CANDIDATES, TokenType.WEIGHTS,
    TokenType.OPTIMIZE_FOR, TokenType.TIMEFRAME, TokenType.METRIC,
    TokenType.MAX_ATTEMPTS, TokenType.INITIAL_DELAY, TokenType.MAX_DELAY,
    TokenType.PER_TASK, TokenType.HOURLY_LIMIT, TokenType.ALERT_AT,
    TokenType.FAILURE_THRESHOLD, TokenType.HALF_OPEN_AFTER,
    TokenType.MIN_SUCCESS_RATE, TokenType.CONTEXT, TokenType.CAPTURE,
    TokenType.LEVEL, TokenType.MESSAGE, TokenType.ON_BELOW_THRESHOLD,
    TokenType.ON_VALIDATION_FAILURE, TokenType.NULL,
}
