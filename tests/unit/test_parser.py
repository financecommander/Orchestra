"""Tests for the Orchestra .orc parser — lexer, parser, and compiler bridge."""

import pytest

from orchestra.parser.lexer import Lexer, LexerError, Token, TokenType
from orchestra.parser.parser import Parser, ParseError
from orchestra.parser.ast_nodes import (
    AgentRef,
    BalanceAgent,
    BudgetNode,
    CascadeAgent,
    CheapestAboveAgent,
    CircuitBreakerNode,
    Expression,
    ForEachNode,
    GuardNode,
    IfNode,
    MatchNode,
    OnPartialFailureNode,
    ParallelNode,
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
from orchestra.parser.compiler_bridge import OrcCompiler, CompilationError


# =====================================================================
# LEXER TESTS
# =====================================================================

class TestLexer:
    """Tests for Lexer tokenization."""

    def test_empty_source(self):
        tokens = Lexer("").tokenize()
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_keywords(self):
        tokens = Lexer("workflow step parallel if else").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert TokenType.WORKFLOW in types
        assert TokenType.STEP in types
        assert TokenType.PARALLEL in types
        assert TokenType.IF in types
        assert TokenType.ELSE in types

    def test_string_literal(self):
        tokens = Lexer('"hello world"').tokenize()
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello world"

    def test_number_integer(self):
        tokens = Lexer("42").tokenize()
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "42"

    def test_number_decimal(self):
        tokens = Lexer("3.14").tokenize()
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "3.14"

    def test_identifier(self):
        tokens = Lexer("my_agent_name").tokenize()
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "my_agent_name"

    def test_operators(self):
        tokens = Lexer("> >= < <= == != =>").tokenize()
        types = [t.type for t in tokens if t.type not in (TokenType.EOF, TokenType.NEWLINE)]
        assert TokenType.GT in types
        assert TokenType.GTE in types
        assert TokenType.LT in types
        assert TokenType.LTE in types
        assert TokenType.EQ in types
        assert TokenType.NEQ in types
        assert TokenType.ARROW in types

    def test_structural_tokens(self):
        tokens = Lexer("{ } [ ] ( ) : , .").tokenize()
        types = [t.type for t in tokens if t.type not in (TokenType.EOF, TokenType.NEWLINE)]
        assert TokenType.LBRACE in types
        assert TokenType.RBRACE in types
        assert TokenType.LBRACKET in types
        assert TokenType.RBRACKET in types
        assert TokenType.LPAREN in types
        assert TokenType.RPAREN in types
        assert TokenType.COLON in types
        assert TokenType.COMMA in types
        assert TokenType.DOT in types

    def test_comment_skipped(self):
        tokens = Lexer("step # this is a comment\nparallel").tokenize()
        types = [t.type for t in tokens if t.type not in (TokenType.EOF, TokenType.NEWLINE)]
        assert types == [TokenType.STEP, TokenType.PARALLEL]

    def test_line_tracking(self):
        tokens = Lexer("step\nparallel").tokenize()
        step = [t for t in tokens if t.type == TokenType.STEP][0]
        par = [t for t in tokens if t.type == TokenType.PARALLEL][0]
        assert step.line == 1
        assert par.line == 2

    def test_string_escape(self):
        tokens = Lexer(r'"hello \"world\""').tokenize()
        assert tokens[0].value == 'hello "world"'

    def test_unterminated_string_raises(self):
        with pytest.raises(LexerError):
            Lexer('"unterminated').tokenize()

    def test_unexpected_char_raises(self):
        with pytest.raises(LexerError):
            Lexer("workflow @invalid").tokenize()

    def test_boolean_tokens(self):
        tokens = Lexer("true false").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert TokenType.BOOL_TRUE in types
        assert TokenType.BOOL_FALSE in types

    def test_null_token(self):
        tokens = Lexer("null").tokenize()
        assert tokens[0].type == TokenType.NULL

    def test_dollar_interpolation(self):
        tokens = Lexer("${item.id}").tokenize()
        assert tokens[0].type == TokenType.IDENTIFIER
        assert "item.id" in tokens[0].value


# =====================================================================
# PARSER TESTS
# =====================================================================

class TestParser:
    """Tests for Parser → AST conversion."""

    def test_empty_source(self):
        workflows = Parser("").parse()
        assert workflows == []

    def test_minimal_workflow(self):
        src = """
workflow test_wf {
    version: "1.0"
    owner: "test"
}
"""
        wfs = Parser(src).parse()
        assert len(wfs) == 1
        assert wfs[0].name == "test_wf"
        assert wfs[0].version == "1.0"
        assert wfs[0].owner == "test"

    def test_workflow_with_step(self):
        src = """
workflow my_wf {
    version: "2.0"

    step analyze {
        agent: my_agent
        task: "Do analysis"
        timeout: 10.0
    }
}
"""
        wfs = Parser(src).parse()
        wf = wfs[0]
        assert len(wf.body) == 1
        step = wf.body[0]
        assert isinstance(step, StepNode)
        assert step.name == "analyze"
        assert isinstance(step.agent, AgentRef)
        assert step.agent.name == "my_agent"
        assert step.task == "Do analysis"
        assert step.timeout.hard == 10.0

    def test_parallel_block(self):
        src = """
workflow my_wf {
    version: "2.0"

    parallel {
        step a {
            agent: agent_a
            task: "Task A"
        }
        step b {
            agent: agent_b
            task: "Task B"
        }
    }
}
"""
        wfs = Parser(src).parse()
        assert len(wfs[0].body) == 1
        par = wfs[0].body[0]
        assert isinstance(par, ParallelNode)
        assert len(par.steps) == 2
        assert par.steps[0].name == "a"
        assert par.steps[1].name == "b"

    def test_if_else(self):
        src = """
workflow my_wf {
    version: "2.0"

    if input.score > 80 {
        step high {
            task: "High score"
        }
    } else {
        step low {
            task: "Low score"
        }
    }
}
"""
        wfs = Parser(src).parse()
        if_node = wfs[0].body[0]
        assert isinstance(if_node, IfNode)
        assert if_node.condition.operator == ">"
        assert len(if_node.body) == 1
        assert len(if_node.else_body) == 1

    def test_match_case(self):
        src = """
workflow my_wf {
    version: "2.0"

    match input.type {
        case "alpha" => {
            step handle_alpha {
                task: "Alpha handling"
            }
        }
        default => {
            step handle_default {
                task: "Default handling"
            }
        }
    }
}
"""
        wfs = Parser(src).parse()
        match = wfs[0].body[0]
        assert isinstance(match, MatchNode)
        assert len(match.cases) == 1
        assert match.cases[0].value == "alpha"
        assert match.default is not None

    def test_guard_block(self):
        src = """
workflow my_wf {
    version: "2.0"

    guard {
        require: input.id != null
        require: input.amount > 0
        on_violation: reject("Bad input")
    }
}
"""
        wfs = Parser(src).parse()
        assert wfs[0].guard is not None
        assert len(wfs[0].guard.requirements) == 2
        assert wfs[0].guard.requirements[0].operator == "!="

    def test_budget_block(self):
        src = """
workflow my_wf {
    version: "2.0"
    budget {
        per_task: 0.02
        hourly_limit: 500.0
        alert_at: 80.0
    }
}
"""
        wfs = Parser(src).parse()
        assert wfs[0].budget is not None
        assert wfs[0].budget.per_task == 0.02
        assert wfs[0].budget.hourly_limit == 500.0
        assert wfs[0].budget.alert_at == 80.0

    def test_circuit_breaker(self):
        src = """
workflow my_wf {
    version: "2.0"
    circuit_breaker {
        failure_threshold: 10
        timeout: 120.0
        half_open_after: 30.0
    }
}
"""
        wfs = Parser(src).parse()
        cb = wfs[0].circuit_breaker
        assert cb is not None
        assert cb.failure_threshold == 10
        assert cb.timeout == 120.0
        assert cb.half_open_after == 30.0

    def test_cascade_agent(self):
        src = """
workflow my_wf {
    version: "2.0"
    step s {
        agent: cascade [
            try: drone_fast,
            fallback: hydra,
            last_resort: claude
        ]
        task: "Test"
    }
}
"""
        wfs = Parser(src).parse()
        step = wfs[0].body[0]
        assert isinstance(step.agent, CascadeAgent)
        assert step.agent.try_agent == "drone_fast"
        assert step.agent.fallback == "hydra"
        assert step.agent.last_resort == "claude"

    def test_balance_agent(self):
        src = """
workflow my_wf {
    version: "2.0"
    agent: balance {
        strategy: round_robin
        pool: ["drone_1", "drone_2", "drone_3"]
        max_concurrent: 50
    }
}
"""
        wfs = Parser(src).parse()
        assert isinstance(wfs[0].agent, BalanceAgent)
        assert wfs[0].agent.strategy == "round_robin"
        assert len(wfs[0].agent.pool) == 3
        assert wfs[0].agent.max_concurrent == 50

    def test_triton_agent(self):
        src = """
workflow my_wf {
    version: "2.0"
    step s {
        agent: triton_ternary("credit-risk-v4")
        task: "Evaluate risk"
    }
}
"""
        wfs = Parser(src).parse()
        step = wfs[0].body[0]
        assert isinstance(step.agent, TritonAgent)
        assert step.agent.model_name == "credit-risk-v4"

    def test_cheapest_above_agent(self):
        src = """
workflow my_wf {
    version: "2.0"
    step s {
        agent: cheapest_above(quality_threshold: 0.85)
        task: "Score lead"
    }
}
"""
        wfs = Parser(src).parse()
        step = wfs[0].body[0]
        assert isinstance(step.agent, CheapestAboveAgent)
        assert step.agent.quality_threshold == 0.85

    def test_select_agent(self):
        src = """
workflow my_wf {
    version: "2.0"
    agent: select {
        metric: performance_history
        timeframe: last_24h
        optimize_for: [speed, cost, accuracy]
        weights: [0.2, 0.5, 0.3]
        candidates: ["drone_1", "hydra", "ultra"]
        fallback: guardian_claude
    }
}
"""
        wfs = Parser(src).parse()
        agent = wfs[0].agent
        assert isinstance(agent, SelectAgent)
        assert agent.metric == "performance_history"
        assert len(agent.candidates) == 3
        assert len(agent.weights) == 3

    def test_try_retry_catch(self):
        src = """
workflow my_wf {
    version: "2.0"
    step s {
        try {
            agent: ultra_reasoning
            task: "Deep analysis"
        } retry {
            strategy: exponential_backoff
            max_attempts: 3
            initial_delay: 2.0
        } catch timeout_error {
            agent: hydra
            alert: "Degraded"
        } catch any_error {
            agent: fallback
        }
    }
}
"""
        wfs = Parser(src).parse()
        step = wfs[0].body[0]
        assert len(step.body) == 1
        try_node = step.body[0]
        assert isinstance(try_node, TryNode)
        assert try_node.retry is not None
        assert try_node.retry.strategy == "exponential_backoff"
        assert try_node.retry.max_attempts == 3
        assert len(try_node.catches) == 2
        assert try_node.catches[0].error_type == "timeout_error"
        assert try_node.catches[1].error_type == "any_error"

    def test_quality_gate(self):
        src = """
workflow my_wf {
    version: "2.0"
    quality_gate {
        metrics: {
            accuracy: 0.95,
            completeness: 0.90
        }
        on_failure {
            step review {
                agent: claude
                task: "Manual review"
            }
        }
    }
}
"""
        wfs = Parser(src).parse()
        qg = wfs[0].quality_gate
        assert qg is not None
        assert qg.metrics["accuracy"] == 0.95
        assert qg.on_failure is not None
        assert len(qg.on_failure) == 1

    def test_finally_block(self):
        src = """
workflow my_wf {
    version: "2.0"
    step work {
        task: "Do work"
    }
    finally {
        step cleanup {
            action: log_metrics
        }
    }
}
"""
        wfs = Parser(src).parse()
        assert wfs[0].finally_block is not None
        assert len(wfs[0].finally_block.body) == 1

    def test_validate_output(self):
        src = """
workflow my_wf {
    version: "2.0"
    step s {
        agent: test_agent
        task: "Test"
        validate_output {
            assert: result.score >= 0
            assert: result.score <= 100
        }
    }
}
"""
        wfs = Parser(src).parse()
        step = wfs[0].body[0]
        assert step.validate_output is not None
        assert len(step.validate_output.assertions) == 2

    def test_timeout_block(self):
        src = """
workflow my_wf {
    version: "2.0"
    step s {
        task: "Test"
        timeout {
            soft: 15.0
            hard: 30.0
        }
    }
}
"""
        wfs = Parser(src).parse()
        step = wfs[0].body[0]
        assert step.timeout is not None
        assert step.timeout.soft == 15.0
        assert step.timeout.hard == 30.0

    def test_protected_by(self):
        src = """
workflow my_wf {
    version: "2.0"
    protected_by: bunny_guardian
}
"""
        wfs = Parser(src).parse()
        assert wfs[0].protected_by == "bunny_guardian"

    def test_multiple_workflows(self):
        src = """
workflow first {
    version: "1.0"
}
workflow second {
    version: "2.0"
}
"""
        wfs = Parser(src).parse()
        assert len(wfs) == 2
        assert wfs[0].name == "first"
        assert wfs[1].name == "second"

    def test_for_each(self):
        src = """
workflow my_wf {
    version: "2.0"
    for each item in input.batch {
        step process {
            task: "Process item"
        }
    }
}
"""
        wfs = Parser(src).parse()
        fe = wfs[0].body[0]
        assert isinstance(fe, ForEachNode)
        assert fe.variable == "item"
        assert fe.collection == "input.batch"

    def test_route_agent(self):
        src = """
workflow my_wf {
    version: "2.0"
    step s {
        agent: route {
            if input.score > 750 then hydra
            if input.score > 650 then ultra
            else guardian
        }
        task: "Route test"
    }
}
"""
        wfs = Parser(src).parse()
        step = wfs[0].body[0]
        assert isinstance(step.agent, RouteAgent)
        assert len(step.agent.rules) == 2
        assert step.agent.default == "guardian"

    def test_on_partial_failure(self):
        src = """
workflow my_wf {
    version: "2.0"
    parallel {
        step a { task: "A" }
        step b { task: "B" }
    }

    on_partial_failure {
        strategy: continue
        min_success_rate: 0.75
    }
}
"""
        wfs = Parser(src).parse()
        par = wfs[0].body[0]
        assert isinstance(par, ParallelNode)
        assert par.on_partial_failure is not None
        assert par.on_partial_failure.min_success_rate == 0.75


# =====================================================================
# COMPILER BRIDGE TESTS
# =====================================================================

class TestOrcCompiler:
    """Tests for OrcCompiler (AST → Workflow objects)."""

    def test_compile_simple_workflow(self):
        src = """
workflow test_wf {
    version: "2.0"
    owner: "test_owner"

    step analyze {
        agent: my_agent
        task: "Do analysis"
    }
}
"""
        compiler = OrcCompiler()
        workflows = compiler.compile_source(src)
        assert len(workflows) == 1
        wf = workflows[0]
        assert wf.name == "test_wf"
        assert wf.metadata["orc_version"] == "2.0"
        assert wf.metadata["owner"] == "test_owner"
        assert "analyze" in wf.tasks
        assert "my_agent" in wf.agents

    def test_compile_parallel_creates_independent_tasks(self):
        src = """
workflow par_wf {
    version: "2.0"

    parallel {
        step a {
            agent: agent1
            task: "Task A"
        }
        step b {
            agent: agent2
            task: "Task B"
        }
    }
}
"""
        compiler = OrcCompiler()
        workflows = compiler.compile_source(src)
        wf = workflows[0]
        assert "a" in wf.tasks
        assert "b" in wf.tasks
        # Parallel tasks should have the same dependencies (both depend on nothing)
        assert wf.tasks["a"].dependencies == wf.tasks["b"].dependencies

    def test_compile_sequential_steps_create_dependencies(self):
        src = """
workflow seq_wf {
    version: "2.0"

    step first {
        task: "First task"
    }
    step second {
        task: "Second task"
    }
}
"""
        compiler = OrcCompiler()
        workflows = compiler.compile_source(src)
        wf = workflows[0]
        assert wf.tasks["second"].dependencies == ["first"]

    def test_compile_guard_stored_in_metadata(self):
        src = """
workflow guarded {
    version: "2.0"
    guard {
        require: input.id != null
        on_violation: reject("Bad")
    }
}
"""
        compiler = OrcCompiler()
        workflows = compiler.compile_source(src)
        wf = workflows[0]
        assert "guard" in wf.metadata
        assert len(wf.metadata["guard"]["requirements"]) == 1

    def test_compile_budget_stored_in_metadata(self):
        src = """
workflow budgeted {
    version: "2.0"
    budget {
        per_task: 0.01
        hourly_limit: 100.0
    }
}
"""
        compiler = OrcCompiler()
        workflows = compiler.compile_source(src)
        wf = workflows[0]
        assert wf.metadata["budget"]["per_task"] == 0.01
        assert wf.metadata["budget"]["hourly_limit"] == 100.0

    def test_compile_triton_agent(self):
        src = """
workflow triton_wf {
    version: "2.0"
    step infer {
        agent: triton_ternary("risk-model-v3")
        task: "Run inference"
    }
}
"""
        compiler = OrcCompiler()
        workflows = compiler.compile_source(src)
        wf = workflows[0]
        agent_name = wf.tasks["infer"].agent
        assert agent_name in wf.agents
        agent = wf.agents[agent_name]
        assert agent.provider == "triton_ternary"
        assert agent.config["model_name"] == "risk-model-v3"

    def test_compile_cascade_agent(self):
        src = """
workflow cascade_wf {
    version: "2.0"
    step s {
        agent: cascade [
            try: fast_agent,
            fallback: medium_agent,
            last_resort: slow_agent
        ]
        task: "Resilient task"
    }
}
"""
        compiler = OrcCompiler()
        workflows = compiler.compile_source(src)
        wf = workflows[0]
        agent_name = wf.tasks["s"].agent
        agent = wf.agents[agent_name]
        assert agent.provider == "cascade"
        assert agent.config["try"] == "fast_agent"
        assert agent.config["fallback"] == "medium_agent"
        assert agent.config["last_resort"] == "slow_agent"

    def test_compile_if_creates_tasks_with_conditions(self):
        src = """
workflow cond_wf {
    version: "2.0"
    if input.amount > 1000 {
        step big {
            task: "Big amount"
        }
    } else {
        step small {
            task: "Small amount"
        }
    }
}
"""
        compiler = OrcCompiler()
        workflows = compiler.compile_source(src)
        wf = workflows[0]
        assert "big" in wf.tasks
        assert "small" in wf.tasks
        assert wf.tasks["big"].metadata["branch"] == "if"
        assert wf.tasks["small"].metadata["branch"] == "else"

    def test_compile_finally_depends_on_all(self):
        src = """
workflow fin_wf {
    version: "2.0"
    step work {
        task: "Work"
    }
    finally {
        step cleanup {
            task: "Cleanup"
        }
    }
}
"""
        compiler = OrcCompiler()
        workflows = compiler.compile_source(src)
        wf = workflows[0]
        assert "work" in wf.tasks["cleanup"].dependencies

    def test_validate_file_valid(self, tmp_path):
        orc_file = tmp_path / "test.orc"
        orc_file.write_text("""
workflow valid_wf {
    version: "2.0"
    step s { task: "Test" }
}
""")
        compiler = OrcCompiler()
        result = compiler.validate_file(str(orc_file))
        assert result["valid"] is True
        assert len(result["workflows"]) == 1

    def test_validate_file_not_found(self):
        compiler = OrcCompiler()
        result = compiler.validate_file("/nonexistent/path.orc")
        assert result["valid"] is False

    def test_execution_plan_output(self):
        src = """
workflow plan_wf {
    version: "2.0"
    step a { task: "A" }
    step b { task: "B" }
}
"""
        compiler = OrcCompiler()
        workflows = compiler.compile_source(src)
        plan = compiler.to_execution_plan(workflows)
        assert plan["version"] == "2.0"
        assert len(plan["workflows"]) == 1
        assert len(plan["workflows"][0]["tasks"]) == 2

    def test_compile_empty_source_warns(self):
        compiler = OrcCompiler()
        workflows = compiler.compile_source("")
        assert workflows == []
        assert len(compiler.warnings) > 0


# =====================================================================
# CLI TESTS
# =====================================================================

class TestCLI:
    """Tests for the CLI entry point."""

    def test_validate_command(self, tmp_path):
        from orchestra.parser.cli import main

        orc_file = tmp_path / "test.orc"
        orc_file.write_text("""
workflow cli_test {
    version: "2.0"
    step s { task: "Hello" }
}
""")
        result = main(["validate", str(orc_file)])
        assert result == 0

    def test_compile_command(self, tmp_path):
        from orchestra.parser.cli import main

        orc_file = tmp_path / "test.orc"
        orc_file.write_text("""
workflow cli_compile {
    version: "2.0"
    step s { task: "Hello" }
}
""")
        out_file = tmp_path / "plan.json"
        result = main(["compile", str(orc_file), "--output", str(out_file)])
        assert result == 0
        assert out_file.exists()

    def test_info_command(self, tmp_path):
        from orchestra.parser.cli import main

        orc_file = tmp_path / "test.orc"
        orc_file.write_text("""
workflow info_test {
    version: "2.0"
    owner: "tester"
    step s {
        agent: test_agent
        task: "Hello"
    }
}
""")
        result = main(["info", str(orc_file)])
        assert result == 0

    def test_validate_invalid_file(self):
        from orchestra.parser.cli import main

        result = main(["validate", "/nonexistent.orc"])
        assert result == 1

    def test_no_command_shows_help(self, capsys):
        from orchestra.parser.cli import main

        result = main([])
        assert result == 1
