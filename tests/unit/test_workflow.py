"""Tests for Workflow module."""

import pytest
from orchestra.core.workflow import Workflow
from orchestra.core.agent import Agent
from orchestra.core.task import Task


class TestWorkflow:
    """Test cases for Workflow class."""

    def test_workflow_creation(self):
        """Test basic workflow creation."""
        workflow = Workflow(name="test_workflow", description="Test workflow")
        assert workflow.name == "test_workflow"
        assert workflow.description == "Test workflow"
        assert len(workflow.agents) == 0
        assert len(workflow.tasks) == 0

    def test_workflow_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Workflow name cannot be empty"):
            Workflow(name="", description="test")

    def test_workflow_empty_description_raises_error(self):
        """Test that empty description raises ValueError."""
        with pytest.raises(ValueError, match="Workflow description cannot be empty"):
            Workflow(name="test", description="")

    def test_add_agent(self):
        """Test adding an agent to workflow."""
        workflow = Workflow(name="test", description="test")
        agent = Agent(name="agent1", provider="llm")

        workflow.add_agent(agent)
        assert "agent1" in workflow.agents
        assert workflow.agents["agent1"] == agent

    def test_add_duplicate_agent_raises_error(self):
        """Test that adding duplicate agent raises ValueError."""
        workflow = Workflow(name="test", description="test")
        agent = Agent(name="agent1", provider="llm")

        workflow.add_agent(agent)
        with pytest.raises(ValueError, match="Agent 'agent1' already exists"):
            workflow.add_agent(agent)

    def test_add_task(self):
        """Test adding a task to workflow."""
        workflow = Workflow(name="test", description="test")
        task = Task(name="task1", description="test task")

        workflow.add_task(task)
        assert "task1" in workflow.tasks
        assert workflow.tasks["task1"] == task

    def test_add_duplicate_task_raises_error(self):
        """Test that adding duplicate task raises ValueError."""
        workflow = Workflow(name="test", description="test")
        task = Task(name="task1", description="test task")

        workflow.add_task(task)
        with pytest.raises(ValueError, match="Task 'task1' already exists"):
            workflow.add_task(task)

    def test_add_task_with_invalid_agent_raises_error(self):
        """Test that task with invalid agent reference raises ValueError."""
        workflow = Workflow(name="test", description="test")
        task = Task(name="task1", description="test", agent="nonexistent")

        with pytest.raises(ValueError, match="Agent 'nonexistent' not found"):
            workflow.add_task(task)

    def test_add_task_with_valid_agent(self):
        """Test adding task with valid agent reference."""
        workflow = Workflow(name="test", description="test")
        agent = Agent(name="agent1", provider="llm")
        workflow.add_agent(agent)

        task = Task(name="task1", description="test", agent="agent1")
        workflow.add_task(task)

        assert "task1" in workflow.tasks

    def test_get_execution_order_no_dependencies(self):
        """Test execution order with no dependencies."""
        workflow = Workflow(name="test", description="test")

        task1 = Task(name="task1", description="test1")
        task2 = Task(name="task2", description="test2")
        workflow.add_task(task1)
        workflow.add_task(task2)

        order = workflow.get_execution_order()
        assert len(order) == 2
        assert "task1" in order
        assert "task2" in order

    def test_get_execution_order_with_dependencies(self):
        """Test execution order with dependencies."""
        workflow = Workflow(name="test", description="test")

        task1 = Task(name="task1", description="test1")
        workflow.add_task(task1)

        task2 = Task(name="task2", description="test2", dependencies=["task1"])
        workflow.add_task(task2)

        task3 = Task(name="task3", description="test3", dependencies=["task1", "task2"])
        workflow.add_task(task3)

        order = workflow.get_execution_order()
        assert order.index("task1") < order.index("task2")
        assert order.index("task2") < order.index("task3")

    def test_circular_dependency_raises_error(self):
        """Test that circular dependencies are detected."""
        workflow = Workflow(name="test", description="test")

        task1 = Task(name="task1", description="test1", dependencies=["task2"])
        task2 = Task(name="task2", description="test2", dependencies=["task1"])

        workflow.tasks["task1"] = task1
        workflow.tasks["task2"] = task2

        with pytest.raises(ValueError, match="Circular dependency detected"):
            workflow.get_execution_order()

    def test_validate_workflow(self):
        """Test workflow validation."""
        workflow = Workflow(name="test", description="test")

        agent = Agent(name="agent1", provider="llm")
        workflow.add_agent(agent)

        task = Task(name="task1", description="test", agent="agent1")
        workflow.add_task(task)

        assert workflow.validate() is True

    def test_method_chaining(self):
        """Test method chaining for workflow construction."""
        workflow = Workflow(name="test", description="test")

        agent = Agent(name="agent1", provider="llm")
        task = Task(name="task1", description="test", agent="agent1")

        result = workflow.add_agent(agent).add_task(task)
        assert result == workflow
        assert "agent1" in workflow.agents
        assert "task1" in workflow.tasks

    def test_workflow_repr(self):
        """Test workflow string representation."""
        workflow = Workflow(name="test", description="test")
        workflow.add_agent(Agent(name="agent1", provider="llm"))
        workflow.add_task(Task(name="task1", description="test"))

        repr_str = repr(workflow)
        assert "test" in repr_str
        assert "tasks=1" in repr_str
        assert "agents=1" in repr_str
