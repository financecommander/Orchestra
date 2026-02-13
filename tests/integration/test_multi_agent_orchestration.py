"""Integration tests for multi-agent orchestration with mocked APIs."""

import pytest
from unittest.mock import patch, MagicMock
from orchestra import Agent, Workflow, Context
from orchestra.core.agent_task import AgentTask, ParallelAgentTask
from orchestra.core.gates import SecurityGate, ComplianceGate, PerformanceGate
from orchestra.compilers import WorkflowCompiler, Executor
from orchestra.providers.agents import AnthropicProvider, OpenAIProvider, XAIProvider


class TestMultiAgentOrchestration:
    """Integration tests for multi-agent orchestration."""

    def test_fintech_workflow_integration(self):
        """Test complete fintech workflow with mocked providers."""
        # Create workflow
        workflow = Workflow(
            name="fintech_test", description="Test fintech workflow"
        )

        # Add agents
        design_agent = Agent(
            name="designer",
            provider="anthropic",
            system_prompt="Design systems",
        )
        build_agent = Agent(
            name="builder", provider="openai", system_prompt="Build code"
        )
        audit_agent = Agent(
            name="auditor", provider="xai", system_prompt="Audit code"
        )

        workflow.add_agent(design_agent)
        workflow.add_agent(build_agent)
        workflow.add_agent(audit_agent)

        # Add tasks
        design_task = AgentTask(
            name="design",
            description="Design the system",
            agent="designer",
        )
        workflow.add_task(design_task)

        build_task = AgentTask(
            name="build",
            description="Build the system",
            agent="builder",
            dependencies=["design"],
        )
        workflow.add_task(build_task)

        audit_task = AgentTask(
            name="audit",
            description="Audit the system",
            agent="auditor",
            dependencies=["build"],
        )
        workflow.add_task(audit_task)

        # Compile workflow
        compiler = WorkflowCompiler()
        compiled_workflow = compiler.compile(workflow)

        # Mock providers
        mock_anthropic = MagicMock(spec=AnthropicProvider)
        mock_anthropic.execute.return_value = {
            "status": "completed",
            "response": "Design completed",
            "provider": "anthropic",
        }

        mock_openai = MagicMock(spec=OpenAIProvider)
        mock_openai.execute.return_value = {
            "status": "completed",
            "response": "Build completed",
            "provider": "openai",
        }

        mock_xai = MagicMock(spec=XAIProvider)
        mock_xai.execute.return_value = {
            "status": "completed",
            "response": "Audit completed",
            "provider": "xai",
        }

        provider_registry = {
            "anthropic": mock_anthropic,
            "openai": mock_openai,
            "xai": mock_xai,
        }

        # Execute workflow
        executor = Executor(provider_registry=provider_registry)
        context = Context()
        result = executor.execute(compiled_workflow, context)

        # Verify execution
        assert result.success is True
        assert len(result.task_results) == 3
        assert "design" in result.task_results
        assert "build" in result.task_results
        assert "audit" in result.task_results

        # Verify providers were called
        assert mock_anthropic.execute.called
        assert mock_openai.execute.called
        assert mock_xai.execute.called

    def test_parallel_audit_workflow(self):
        """Test parallel audit tasks with mocked providers."""
        workflow = Workflow(name="parallel_audit", description="Test parallel")

        # Single builder agent
        builder = Agent(name="builder", provider="openai")
        workflow.add_agent(builder)

        # Multiple audit agents
        security_auditor = Agent(name="sec_auditor", provider="xai")
        compliance_auditor = Agent(name="comp_auditor", provider="xai")
        workflow.add_agent(security_auditor)
        workflow.add_agent(compliance_auditor)

        # Build task
        build_task = AgentTask(name="build", description="Build", agent="builder")
        workflow.add_task(build_task)

        # Parallel audit tasks
        security_task = AgentTask(
            name="security_audit",
            description="Security audit",
            agent="sec_auditor",
            dependencies=["build"],
        )
        compliance_task = AgentTask(
            name="compliance_audit",
            description="Compliance audit",
            agent="comp_auditor",
            dependencies=["build"],
        )
        workflow.add_task(security_task)
        workflow.add_task(compliance_task)

        # Compile
        compiler = WorkflowCompiler()
        compiled_workflow = compiler.compile(workflow)
        execution_plan = compiler.get_execution_plan(compiled_workflow)

        # Verify parallel execution plan
        assert len(execution_plan) == 2
        assert execution_plan[0] == ["build"]
        assert set(execution_plan[1]) == {"security_audit", "compliance_audit"}

        # Mock providers
        mock_openai = MagicMock()
        mock_openai.execute.return_value = {
            "status": "completed",
            "response": "Built",
        }

        mock_xai = MagicMock()
        mock_xai.execute.return_value = {
            "status": "completed",
            "response": "Audited",
        }

        # Execute
        executor = Executor(
            provider_registry={"openai": mock_openai, "xai": mock_xai}
        )
        result = executor.execute(compiled_workflow, Context())

        assert result.success is True
        assert len(result.task_results) == 3

    def test_quality_gates_integration(self):
        """Test quality gates with workflow execution."""
        # Create gates
        security_gate = SecurityGate(threshold=0.8, escalation_enabled=False)
        compliance_gate = ComplianceGate(threshold=0.9, escalation_enabled=False)
        performance_gate = PerformanceGate(
            threshold=500.0, escalation_enabled=False
        )

        # Simulate audit results
        audit_results = {
            "security_score": 0.85,
            "compliance_score": 0.95,
            "latency": 350.0,
        }

        # Check gates
        security_result = security_gate.check(audit_results)
        compliance_result = compliance_gate.check(audit_results)
        performance_result = performance_gate.check(audit_results)

        assert security_result.passed is True
        assert compliance_result.passed is True
        assert performance_result.passed is True

    def test_quality_gates_with_failures(self):
        """Test quality gates with failures and escalation."""
        escalations = []

        def capture_escalation(result):
            escalations.append(result)

        # Create gates with escalation
        security_gate = SecurityGate(
            threshold=0.9, escalation_callback=capture_escalation
        )
        compliance_gate = ComplianceGate(
            threshold=0.95, escalation_callback=capture_escalation
        )

        # Failing audit results
        failing_results = {
            "security_score": 0.7,
            "compliance_score": 0.8,
        }

        security_result = security_gate.check(failing_results)
        compliance_result = compliance_gate.check(failing_results)

        # Both should fail
        assert security_result.passed is False
        assert compliance_result.passed is False

        # Both should trigger escalation
        assert len(escalations) == 2
        assert escalations[0].gate_name == "SecurityGate"
        assert escalations[1].gate_name == "ComplianceGate"

    def test_schema_validation_in_workflow(self):
        """Test schema validation integrated into workflow."""
        workflow = Workflow(name="validation_test", description="Test validation")

        agent = Agent(name="processor", provider="openai")
        workflow.add_agent(agent)

        # Task with strict schema
        task = AgentTask(
            name="process",
            description="Process data",
            agent="processor",
            input_schema={
                "type": "object",
                "required": ["data"],
                "properties": {"data": {"type": "array"}},
            },
            output_schema={
                "type": "object",
                "required": ["result"],
                "properties": {"result": {"type": "number"}},
            },
        )

        # Valid input
        assert task.validate_input({"data": [1, 2, 3]}) is True

        # Invalid input
        assert task.validate_input({"wrong_field": "value"}) is False
        assert len(task.validation_errors) > 0

        # Valid output
        assert task.validate_output({"result": 42}) is True

        # Invalid output
        assert task.validate_output({"result": "not a number"}) is False

    def test_parallel_agent_task_execution(self):
        """Test parallel agent task execution with context."""
        # Create multiple tasks
        tasks = [
            AgentTask(
                name=f"audit_{i}",
                description=f"Audit component {i}",
                agent="auditor",
            )
            for i in range(5)
        ]

        parallel = ParallelAgentTask(
            name="parallel_audits", tasks=tasks, max_workers=3
        )

        context = Context()
        context.set("project", "test_project")

        # Mock executor
        def mock_executor(task, ctx):
            return {
                "status": "completed",
                "task": task.name,
                "project": ctx.get("project"),
            }

        result = parallel.execute(mock_executor, context)

        assert result["task_count"] == 5
        assert result["success_count"] == 5
        assert result["error_count"] == 0

        # Verify all tasks executed
        for i in range(5):
            task_name = f"audit_{i}"
            assert task_name in result["results"]
            assert result["results"][task_name]["project"] == "test_project"

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_provider_with_environment_variables(self):
        """Test that providers load API keys from environment."""
        provider = AnthropicProvider()
        assert provider.api_key == "test-key"

    def test_complete_pipeline_with_gates_and_validation(self):
        """Test complete pipeline with gates and validation."""
        # Setup workflow
        workflow = Workflow(name="complete", description="Complete pipeline")

        design_agent = Agent(name="designer", provider="anthropic")
        build_agent = Agent(name="builder", provider="openai")
        audit_agent = Agent(name="auditor", provider="xai")

        workflow.add_agent(design_agent)
        workflow.add_agent(build_agent)
        workflow.add_agent(audit_agent)

        # Tasks with schemas
        design_task = AgentTask(
            name="design",
            description="Design",
            agent="designer",
            output_schema={
                "type": "object",
                "required": ["architecture"],
                "properties": {"architecture": {"type": "string"}},
            },
        )

        build_task = AgentTask(
            name="build",
            description="Build",
            agent="builder",
            dependencies=["design"],
            output_schema={
                "type": "object",
                "required": ["code"],
                "properties": {"code": {"type": "string"}},
            },
        )

        audit_task = AgentTask(
            name="audit",
            description="Audit",
            agent="auditor",
            dependencies=["build"],
            output_schema={
                "type": "object",
                "required": ["security_score"],
                "properties": {"security_score": {"type": "number"}},
            },
        )

        workflow.add_task(design_task)
        workflow.add_task(build_task)
        workflow.add_task(audit_task)

        # Compile and verify
        compiler = WorkflowCompiler()
        compiled = compiler.compile(workflow)

        assert compiled.validate() is True

        # Mock execution
        mock_providers = {
            "anthropic": MagicMock(),
            "openai": MagicMock(),
            "xai": MagicMock(),
        }

        for provider in mock_providers.values():
            provider.execute.return_value = {
                "status": "completed",
                "response": "Done",
            }

        executor = Executor(provider_registry=mock_providers)
        result = executor.execute(compiled, Context())

        assert result.success is True

        # Apply quality gates
        security_gate = SecurityGate(threshold=0.8, escalation_enabled=False)

        # Simulate audit result
        gate_result = security_gate.check({"security_score": 0.9})
        assert gate_result.passed is True
