"""Tests for WorkflowCompiler module."""

import pytest
from orchestra.core.workflow import Workflow
from orchestra.core.agent import Agent
from orchestra.core.task import Task
from orchestra.compilers.workflow_compiler import WorkflowCompiler


class TestWorkflowCompiler:
    """Test cases for WorkflowCompiler class."""

    def test_compiler_creation(self):
        """Test basic compiler creation."""
        compiler = WorkflowCompiler()
        assert len(compiler.compiled_workflows) == 0

    def test_compile_simple_workflow(self):
        """Test compiling a simple workflow."""
        compiler = WorkflowCompiler()

        workflow = Workflow(name="test", description="test")
        agent = Agent(name="agent1", provider="llm")
        task = Task(name="task1", description="test", agent="agent1")

        workflow.add_agent(agent).add_task(task)

        compiled = compiler.compile(workflow)
        assert compiled == workflow
        assert "test" in compiler.compiled_workflows

    def test_compile_invalid_workflow_raises_error(self):
        """Test that compiling invalid workflow raises ValueError."""
        compiler = WorkflowCompiler()

        workflow = Workflow(name="test", description="test")
        task = Task(name="task1", description="test", agent="nonexistent")
        workflow.tasks["task1"] = task  # Bypass validation

        with pytest.raises(ValueError):
            compiler.compile(workflow)

    def test_get_execution_plan_sequential(self):
        """Test execution plan for sequential tasks."""
        compiler = WorkflowCompiler()

        workflow = Workflow(name="test", description="test")

        task1 = Task(name="task1", description="test1")
        workflow.add_task(task1)

        task2 = Task(name="task2", description="test2", dependencies=["task1"])
        workflow.add_task(task2)

        task3 = Task(name="task3", description="test3", dependencies=["task2"])
        workflow.add_task(task3)

        plan = compiler.get_execution_plan(workflow)

        # Should have 3 levels (sequential execution)
        assert len(plan) == 3
        assert plan[0] == ["task1"]
        assert plan[1] == ["task2"]
        assert plan[2] == ["task3"]

    def test_get_execution_plan_parallel(self):
        """Test execution plan for parallel tasks."""
        compiler = WorkflowCompiler()

        workflow = Workflow(name="test", description="test")

        task1 = Task(name="task1", description="test1")
        task2 = Task(name="task2", description="test2")
        task3 = Task(name="task3", description="test3")

        workflow.add_task(task1)
        workflow.add_task(task2)
        workflow.add_task(task3)

        plan = compiler.get_execution_plan(workflow)

        # All tasks can run in parallel (1 level)
        assert len(plan) == 1
        assert len(plan[0]) == 3
        assert set(plan[0]) == {"task1", "task2", "task3"}

    def test_get_execution_plan_mixed(self):
        """Test execution plan for mixed sequential/parallel tasks."""
        compiler = WorkflowCompiler()

        workflow = Workflow(name="test", description="test")

        # Level 1: task1
        task1 = Task(name="task1", description="test1")
        workflow.add_task(task1)

        # Level 2: task2 and task3 (both depend on task1)
        task2 = Task(name="task2", description="test2", dependencies=["task1"])
        task3 = Task(name="task3", description="test3", dependencies=["task1"])
        workflow.add_task(task2)
        workflow.add_task(task3)

        # Level 3: task4 (depends on both task2 and task3)
        task4 = Task(name="task4", description="test4", dependencies=["task2", "task3"])
        workflow.add_task(task4)

        plan = compiler.get_execution_plan(workflow)

        assert len(plan) == 3
        assert plan[0] == ["task1"]
        assert set(plan[1]) == {"task2", "task3"}
        assert plan[2] == ["task4"]

    def test_optimize_workflow(self):
        """Test workflow optimization."""
        compiler = WorkflowCompiler()

        workflow = Workflow(name="test", description="test")
        optimized = compiler.optimize(workflow)

        # Currently optimization is a placeholder
        assert optimized == workflow

    def test_compiler_repr(self):
        """Test compiler string representation."""
        compiler = WorkflowCompiler()

        workflow = Workflow(name="test", description="test")
        compiler.compile(workflow)

        repr_str = repr(compiler)
        assert "WorkflowCompiler" in repr_str
        assert "compiled=1" in repr_str
