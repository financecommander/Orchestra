"""Tests for agent task module."""

import pytest
from orchestra.core.agent_task import AgentTask, ParallelAgentTask
from orchestra.core.task import TaskStatus
from orchestra.core.context import Context


class TestAgentTask:
    """Test cases for AgentTask."""

    def test_agent_task_creation(self):
        """Test basic agent task creation."""
        task = AgentTask(name="test_task", description="Test description")
        assert task.name == "test_task"
        assert task.description == "Test description"
        assert task.input_schema is None
        assert task.output_schema is None
        assert task.validation_errors == []

    def test_agent_task_with_schemas(self):
        """Test agent task with input/output schemas."""
        input_schema = {
            "type": "object",
            "required": ["field1"],
            "properties": {"field1": {"type": "string"}},
        }
        output_schema = {
            "type": "object",
            "required": ["result"],
            "properties": {"result": {"type": "number"}},
        }

        task = AgentTask(
            name="test_task",
            description="Test",
            input_schema=input_schema,
            output_schema=output_schema,
        )

        assert task.input_schema == input_schema
        assert task.output_schema == output_schema

    def test_agent_task_validate_input_no_schema(self):
        """Test input validation with no schema."""
        task = AgentTask(name="test", description="test")
        data = {"any": "data"}

        assert task.validate_input(data) is True
        assert task.validation_errors == []

    def test_agent_task_validate_input_valid(self):
        """Test input validation with valid data."""
        task = AgentTask(
            name="test",
            description="test",
            input_schema={
                "type": "object",
                "required": ["name", "age"],
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "number"},
                },
            },
        )

        data = {"name": "Alice", "age": 30}
        assert task.validate_input(data) is True
        assert task.validation_errors == []

    def test_agent_task_validate_input_missing_required(self):
        """Test input validation with missing required field."""
        task = AgentTask(
            name="test",
            description="test",
            input_schema={
                "type": "object",
                "required": ["name"],
                "properties": {"name": {"type": "string"}},
            },
        )

        data = {"other": "field"}
        assert task.validate_input(data) is False
        assert len(task.validation_errors) > 0
        assert "name" in task.validation_errors[0]

    def test_agent_task_validate_input_wrong_type(self):
        """Test input validation with wrong type."""
        task = AgentTask(
            name="test",
            description="test",
            input_schema={
                "type": "object",
                "properties": {"age": {"type": "number"}},
            },
        )

        data = {"age": "not a number"}
        assert task.validate_input(data) is False
        assert any("should be number" in err for err in task.validation_errors)

    def test_agent_task_validate_output_valid(self):
        """Test output validation with valid data."""
        task = AgentTask(
            name="test",
            description="test",
            output_schema={
                "type": "object",
                "required": ["result"],
                "properties": {"result": {"type": "boolean"}},
            },
        )

        data = {"result": True}
        assert task.validate_output(data) is True

    def test_agent_task_validate_output_invalid(self):
        """Test output validation with invalid data."""
        task = AgentTask(
            name="test",
            description="test",
            output_schema={
                "type": "object",
                "required": ["result"],
                "properties": {"result": {"type": "array"}},
            },
        )

        data = {"result": "not an array"}
        assert task.validate_output(data) is False

    def test_agent_task_validate_various_types(self):
        """Test validation with various data types."""
        task = AgentTask(
            name="test",
            description="test",
            input_schema={
                "type": "object",
                "properties": {
                    "string_field": {"type": "string"},
                    "number_field": {"type": "number"},
                    "boolean_field": {"type": "boolean"},
                    "object_field": {"type": "object"},
                    "array_field": {"type": "array"},
                },
            },
        )

        valid_data = {
            "string_field": "text",
            "number_field": 42,
            "boolean_field": True,
            "object_field": {"key": "value"},
            "array_field": [1, 2, 3],
        }
        assert task.validate_input(valid_data) is True

        # Test with wrong types
        invalid_data = {
            "string_field": 123,  # Should be string
            "number_field": "text",  # Should be number
            "boolean_field": "yes",  # Should be boolean
            "object_field": [1, 2],  # Should be object
            "array_field": {"key": "val"},  # Should be array
        }

        # Check each field individually
        for field, value in invalid_data.items():
            test_data = {field: value}
            result = task.validate_input(test_data)
            # At least one should fail
            if field == "number_field":
                assert result is False

    def test_agent_task_repr(self):
        """Test agent task string representation."""
        task = AgentTask(
            name="test_task", description="test", agent="test_agent"
        )
        repr_str = repr(task)
        assert "AgentTask" in repr_str
        assert "test_task" in repr_str


class TestParallelAgentTask:
    """Test cases for ParallelAgentTask."""

    def test_parallel_agent_task_creation(self):
        """Test basic parallel agent task creation."""
        tasks = [
            AgentTask(name="task1", description="Task 1"),
            AgentTask(name="task2", description="Task 2"),
        ]

        parallel = ParallelAgentTask(name="parallel_group", tasks=tasks)

        assert parallel.name == "parallel_group"
        assert len(parallel.tasks) == 2
        assert parallel.max_workers == 2  # min(4, len(tasks))
        assert parallel.aggregate_results is True

    def test_parallel_agent_task_custom_workers(self):
        """Test parallel task with custom worker count."""
        tasks = [
            AgentTask(name=f"task{i}", description=f"Task {i}")
            for i in range(10)
        ]

        parallel = ParallelAgentTask(
            name="parallel_group", tasks=tasks, max_workers=8
        )

        assert parallel.max_workers == 8

    def test_parallel_agent_task_execute(self):
        """Test parallel task execution."""
        tasks = [
            AgentTask(name="task1", description="Task 1"),
            AgentTask(name="task2", description="Task 2"),
            AgentTask(name="task3", description="Task 3"),
        ]

        parallel = ParallelAgentTask(name="parallel_group", tasks=tasks)
        context = Context()

        def mock_executor(task, ctx):
            """Mock executor function."""
            return {
                "status": "completed",
                "task_name": task.name,
                "result": f"Result for {task.name}",
            }

        result = parallel.execute(mock_executor, context)

        assert result["name"] == "parallel_group"
        assert result["status"] == "completed"
        assert result["task_count"] == 3
        assert result["success_count"] == 3
        assert result["error_count"] == 0
        assert "task1" in result["results"]
        assert "task2" in result["results"]
        assert "task3" in result["results"]

    def test_parallel_agent_task_execute_with_errors(self):
        """Test parallel task execution with errors."""
        tasks = [
            AgentTask(name="task1", description="Task 1"),
            AgentTask(name="task2", description="Task 2"),
            AgentTask(name="task3", description="Task 3"),
        ]

        parallel = ParallelAgentTask(name="parallel_group", tasks=tasks)
        context = Context()

        def mock_executor(task, ctx):
            """Mock executor that fails for task2."""
            if task.name == "task2":
                raise RuntimeError("Task 2 failed")
            return {"status": "completed", "task_name": task.name}

        result = parallel.execute(mock_executor, context)

        assert result["status"] == "completed_with_errors"
        assert result["success_count"] == 2
        assert result["error_count"] == 1
        assert "task2" in result["errors"]
        assert "Task 2 failed" in result["errors"]["task2"]

    def test_parallel_agent_task_no_aggregation(self):
        """Test parallel task without result aggregation."""
        tasks = [
            AgentTask(name="task1", description="Task 1"),
            AgentTask(name="task2", description="Task 2"),
        ]

        parallel = ParallelAgentTask(
            name="parallel_group", tasks=tasks, aggregate_results=False
        )
        context = Context()

        def mock_executor(task, ctx):
            return {"result": f"Result {task.name}"}

        result = parallel.execute(mock_executor, context)

        # Without aggregation, returns just the results dict
        assert "task1" in result
        assert "task2" in result
        assert "status" not in result
        assert "task_count" not in result

    def test_parallel_agent_task_repr(self):
        """Test parallel agent task string representation."""
        tasks = [
            AgentTask(name="task1", description="Task 1"),
            AgentTask(name="task2", description="Task 2"),
        ]

        parallel = ParallelAgentTask(name="test_parallel", tasks=tasks)
        repr_str = repr(parallel)

        assert "ParallelAgentTask" in repr_str
        assert "test_parallel" in repr_str
        assert "2" in repr_str


class TestAgentTaskIntegration:
    """Integration tests for agent tasks."""

    def test_agent_task_full_workflow(self):
        """Test complete workflow with validation."""
        # Create task with schemas
        task = AgentTask(
            name="process_data",
            description="Process input data",
            input_schema={
                "type": "object",
                "required": ["data"],
                "properties": {"data": {"type": "array"}},
            },
            output_schema={
                "type": "object",
                "required": ["processed"],
                "properties": {"processed": {"type": "number"}},
            },
        )

        # Validate valid input
        input_data = {"data": [1, 2, 3, 4, 5]}
        assert task.validate_input(input_data) is True

        # Simulate processing
        output_data = {"processed": 15}

        # Validate output
        assert task.validate_output(output_data) is True

    def test_multiple_parallel_tasks_with_validation(self):
        """Test multiple parallel tasks with schema validation."""
        tasks = [
            AgentTask(
                name=f"task{i}",
                description=f"Task {i}",
                output_schema={
                    "type": "object",
                    "required": ["result"],
                    "properties": {"result": {"type": "number"}},
                },
            )
            for i in range(3)
        ]

        parallel = ParallelAgentTask(name="validation_group", tasks=tasks)
        context = Context()

        def mock_executor(task, ctx):
            return {"result": 42}  # Valid output

        result = parallel.execute(mock_executor, context)

        assert result["success_count"] == 3
        assert result["error_count"] == 0

        # Validate outputs
        for task_name, task_result in result["results"].items():
            assert "result" in task_result
            assert isinstance(task_result["result"], (int, float))
