"""Integration tests for Orchestra DSL."""

from orchestra.core.agent import Agent
from orchestra.core.task import Task
from orchestra.core.workflow import Workflow
from orchestra.core.context import Context
from orchestra.compilers.workflow_compiler import WorkflowCompiler
from orchestra.compilers.executor import Executor


class TestWorkflowIntegration:
    """Integration tests for workflow execution."""

    def test_simple_workflow_execution(self):
        """Test executing a simple workflow end-to-end."""
        # Create workflow
        workflow = Workflow(name="simple_workflow", description="A simple test workflow")

        # Add an agent
        agent = Agent(name="test_agent", provider="test")
        workflow.add_agent(agent)

        # Add tasks
        task1 = Task(name="task1", description="First task", agent="test_agent")
        task2 = Task(
            name="task2",
            description="Second task",
            agent="test_agent",
            dependencies=["task1"],
        )
        workflow.add_task(task1)
        workflow.add_task(task2)

        # Compile workflow
        compiler = WorkflowCompiler()
        compiled_workflow = compiler.compile(workflow)

        # Execute workflow
        executor = Executor()
        result = executor.execute(compiled_workflow)

        # Verify execution
        assert result.success is True
        assert "task1" in result.task_results
        assert "task2" in result.task_results

    def test_workflow_with_context(self):
        """Test workflow execution with shared context."""
        # Create workflow
        workflow = Workflow(name="context_workflow", description="Workflow with context")

        # Add tasks
        task1 = Task(name="task1", description="First task")
        task2 = Task(name="task2", description="Second task", dependencies=["task1"])
        workflow.add_task(task1)
        workflow.add_task(task2)

        # Create context with initial data
        context = Context()
        context.set("input_data", {"key": "value"})

        # Execute workflow
        executor = Executor()
        result = executor.execute(workflow, context)

        # Verify execution
        assert result.success is True
        assert context.has("task.task1.result")
        assert context.has("task.task2.result")

    def test_parallel_task_execution(self):
        """Test workflow with parallel tasks."""
        # Create workflow
        workflow = Workflow(name="parallel_workflow", description="Workflow with parallel tasks")

        # Add parallel tasks (no dependencies)
        task1 = Task(name="task1", description="Parallel task 1")
        task2 = Task(name="task2", description="Parallel task 2")
        task3 = Task(name="task3", description="Parallel task 3")
        workflow.add_task(task1)
        workflow.add_task(task2)
        workflow.add_task(task3)

        # Add a final task that depends on all parallel tasks
        task4 = Task(
            name="task4",
            description="Final task",
            dependencies=["task1", "task2", "task3"],
        )
        workflow.add_task(task4)

        # Compile and get execution plan
        compiler = WorkflowCompiler()
        compiled_workflow = compiler.compile(workflow)
        plan = compiler.get_execution_plan(compiled_workflow)

        # Verify parallel execution plan
        assert len(plan) == 2
        assert set(plan[0]) == {"task1", "task2", "task3"}
        assert plan[1] == ["task4"]

        # Execute workflow
        executor = Executor()
        result = executor.execute(compiled_workflow)

        # Verify all tasks completed
        assert result.success is True
        assert len(result.task_results) == 4
