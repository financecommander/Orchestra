"""Tests for Executor module."""

from orchestra.core.workflow import Workflow
from orchestra.core.agent import Agent
from orchestra.core.task import Task, TaskStatus
from orchestra.core.context import Context
from orchestra.compilers.executor import Executor, ExecutionResult


class TestExecutionResult:
    """Test cases for ExecutionResult class."""

    def test_execution_result_creation(self):
        """Test execution result creation."""
        result = ExecutionResult("test_workflow", True)
        assert result.workflow_name == "test_workflow"
        assert result.success is True
        assert len(result.task_results) == 0
        assert len(result.errors) == 0

    def test_add_task_result(self):
        """Test adding task results."""
        result = ExecutionResult("test", True)
        result.add_task_result("task1", {"output": "value"})

        assert "task1" in result.task_results
        assert result.task_results["task1"]["output"] == "value"

    def test_add_error(self):
        """Test adding errors."""
        result = ExecutionResult("test", True)
        result.add_error("task1", "Error message")

        assert "task1" in result.errors
        assert result.errors["task1"] == "Error message"

    def test_execution_result_repr(self):
        """Test execution result string representation."""
        result = ExecutionResult("test", True)
        assert "test" in repr(result)
        assert "success" in repr(result)


class TestExecutor:
    """Test cases for Executor class."""

    def test_executor_creation(self):
        """Test basic executor creation."""
        executor = Executor()
        assert len(executor.provider_registry) == 0
        assert len(executor.execution_history) == 0

    def test_executor_with_providers(self):
        """Test executor creation with providers."""
        providers = {"llm": "mock_provider"}
        executor = Executor(provider_registry=providers)

        assert "llm" in executor.provider_registry

    def test_execute_simple_workflow(self):
        """Test executing a simple workflow."""
        executor = Executor()

        workflow = Workflow(name="test", description="test")
        task = Task(name="task1", description="Simple task")
        workflow.add_task(task)

        result = executor.execute(workflow)

        assert result.success is True
        assert "task1" in result.task_results
        assert workflow.tasks["task1"].status == TaskStatus.COMPLETED

    def test_execute_workflow_with_agent(self):
        """Test executing workflow with agent."""
        executor = Executor()

        workflow = Workflow(name="test", description="test")
        agent = Agent(name="agent1", provider="llm")
        workflow.add_agent(agent)

        task = Task(name="task1", description="Task with agent", agent="agent1")
        workflow.add_task(task)

        result = executor.execute(workflow)

        assert result.success is True
        assert "task1" in result.task_results
        assert workflow.tasks["task1"].status == TaskStatus.COMPLETED

    def test_execute_workflow_with_dependencies(self):
        """Test executing workflow with task dependencies."""
        executor = Executor()

        workflow = Workflow(name="test", description="test")

        task1 = Task(name="task1", description="First task")
        workflow.add_task(task1)

        task2 = Task(name="task2", description="Second task", dependencies=["task1"])
        workflow.add_task(task2)

        result = executor.execute(workflow)

        assert result.success is True
        assert "task1" in result.task_results
        assert "task2" in result.task_results
        assert workflow.tasks["task1"].status == TaskStatus.COMPLETED
        assert workflow.tasks["task2"].status == TaskStatus.COMPLETED

    def test_execute_workflow_with_context(self):
        """Test executing workflow with custom context."""
        executor = Executor()
        context = Context()
        context.set("initial_value", "test_value")

        workflow = Workflow(name="test", description="test")
        task = Task(name="task1", description="Task")
        workflow.add_task(task)

        result = executor.execute(workflow, context)

        assert result.success is True
        assert context.has("task.task1.result")

    def test_execute_workflow_updates_context(self):
        """Test that execution updates context with task results."""
        executor = Executor()
        context = Context()

        workflow = Workflow(name="test", description="test")
        task1 = Task(name="task1", description="First")
        task2 = Task(name="task2", description="Second", dependencies=["task1"])

        workflow.add_task(task1)
        workflow.add_task(task2)

        result = executor.execute(workflow, context)

        assert result.success is True
        assert context.has("task.task1.result")
        assert context.has("task.task2.result")

    def test_execution_history(self):
        """Test that executor maintains execution history."""
        executor = Executor()

        workflow = Workflow(name="test", description="test")
        task = Task(name="task1", description="Task")
        workflow.add_task(task)

        executor.execute(workflow)

        assert len(executor.execution_history) == 1
        assert executor.execution_history[0]["workflow"] == "test"

    def test_executor_repr(self):
        """Test executor string representation."""
        executor = Executor()

        workflow = Workflow(name="test", description="test")
        task = Task(name="task1", description="Task")
        workflow.add_task(task)

        executor.execute(workflow)

        repr_str = repr(executor)
        assert "Executor" in repr_str
        assert "executions=1" in repr_str
