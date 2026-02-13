"""Tests for Task module."""

import pytest
from orchestra.core.task import Task, TaskStatus


class TestTask:
    """Test cases for Task class."""
    
    def test_task_creation(self):
        """Test basic task creation."""
        task = Task(name="test_task", description="Test description")
        assert task.name == "test_task"
        assert task.description == "Test description"
        assert task.status == TaskStatus.PENDING
        assert task.dependencies == []
        assert task.inputs == {}
    
    def test_task_with_dependencies(self):
        """Test task creation with dependencies."""
        task = Task(
            name="dependent_task",
            description="Depends on other tasks",
            dependencies=["task1", "task2"]
        )
        assert len(task.dependencies) == 2
        assert "task1" in task.dependencies
        assert "task2" in task.dependencies
    
    def test_task_with_inputs(self):
        """Test task creation with inputs."""
        inputs = {"param1": "value1", "param2": 42}
        task = Task(
            name="input_task",
            description="Task with inputs",
            inputs=inputs
        )
        assert task.inputs == inputs
    
    def test_task_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Task name cannot be empty"):
            Task(name="", description="test")
    
    def test_task_empty_description_raises_error(self):
        """Test that empty description raises ValueError."""
        with pytest.raises(ValueError, match="Task description cannot be empty"):
            Task(name="test", description="")
    
    def test_task_status_transitions(self):
        """Test task status transitions."""
        task = Task(name="test", description="test")
        
        # Initial status
        assert task.status == TaskStatus.PENDING
        
        # Mark running
        task.mark_running()
        assert task.status == TaskStatus.RUNNING
        
        # Mark completed
        result = {"output": "success"}
        task.mark_completed(result)
        assert task.status == TaskStatus.COMPLETED
        assert task.result == result
    
    def test_task_mark_failed(self):
        """Test marking task as failed."""
        task = Task(name="test", description="test")
        task.mark_failed("Error message")
        
        assert task.status == TaskStatus.FAILED
        assert task.error == "Error message"
    
    def test_task_is_ready_no_dependencies(self):
        """Test task readiness with no dependencies."""
        task = Task(name="test", description="test")
        assert task.is_ready(set())
    
    def test_task_is_ready_with_dependencies(self):
        """Test task readiness with dependencies."""
        task = Task(
            name="test",
            description="test",
            dependencies=["task1", "task2"]
        )
        
        # Not ready when no dependencies completed
        assert not task.is_ready(set())
        
        # Not ready when only some dependencies completed
        assert not task.is_ready({"task1"})
        
        # Ready when all dependencies completed
        assert task.is_ready({"task1", "task2"})
        assert task.is_ready({"task1", "task2", "task3"})
    
    def test_task_repr(self):
        """Test task string representation."""
        task = Task(name="test", description="test")
        assert "test" in repr(task)
        assert "pending" in repr(task).lower()
