"""Agent task types with schema validation for Orchestra DSL."""

from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from orchestra.core.task import Task
from orchestra.core.context import Context


@dataclass
class AgentTask(Task):
    """Task with LLM agent execution and schema validation.

    Extends base Task with input/output schema validation capabilities.
    """

    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    validation_errors: List[str] = field(default_factory=list)

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """Validate input data against schema.

        Args:
            data: Input data to validate

        Returns:
            True if valid, False otherwise
        """
        if not self.input_schema:
            return True

        self.validation_errors.clear()
        return self._validate_against_schema(data, self.input_schema, "input")

    def validate_output(self, data: Dict[str, Any]) -> bool:
        """Validate output data against schema.

        Args:
            data: Output data to validate

        Returns:
            True if valid, False otherwise
        """
        if not self.output_schema:
            return True

        self.validation_errors.clear()
        return self._validate_against_schema(data, self.output_schema, "output")

    def _validate_against_schema(
        self, data: Dict[str, Any], schema: Dict[str, Any], schema_type: str
    ) -> bool:
        """Validate data against a JSON schema.

        Args:
            data: Data to validate
            schema: JSON schema
            schema_type: Type of schema (input/output) for error messages

        Returns:
            True if valid, False otherwise
        """
        # Basic schema validation implementation
        # In production, you'd use jsonschema library:
        # from jsonschema import validate, ValidationError
        # try:
        #     validate(instance=data, schema=schema)
        #     return True
        # except ValidationError as e:
        #     self.validation_errors.append(str(e))
        #     return False

        required_fields = schema.get("required", [])
        properties = schema.get("properties", {})

        # Check required fields
        for field_name in required_fields:
            if field_name not in data:
                self.validation_errors.append(
                    f"{schema_type} validation: Missing required field '{field_name}'"
                )
                return False

        # Check field types
        for field_name, field_schema in properties.items():
            if field_name in data:
                expected_type = field_schema.get("type")
                value = data[field_name]

                if expected_type == "string" and not isinstance(value, str):
                    self.validation_errors.append(
                        f"{schema_type} validation: Field '{field_name}' should be string"
                    )
                    return False
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    self.validation_errors.append(
                        f"{schema_type} validation: Field '{field_name}' should be number"
                    )
                    return False
                elif expected_type == "boolean" and not isinstance(value, bool):
                    self.validation_errors.append(
                        f"{schema_type} validation: Field '{field_name}' should be boolean"
                    )
                    return False
                elif expected_type == "object" and not isinstance(value, dict):
                    self.validation_errors.append(
                        f"{schema_type} validation: Field '{field_name}' should be object"
                    )
                    return False
                elif expected_type == "array" and not isinstance(value, list):
                    self.validation_errors.append(
                        f"{schema_type} validation: Field '{field_name}' should be array"
                    )
                    return False

        return True

    def __repr__(self) -> str:
        """String representation of the agent task."""
        return f"AgentTask(name='{self.name}', agent='{self.agent}', status='{self.status.value}')"


class ParallelAgentTask:
    """Execute multiple agent tasks in parallel.

    Manages concurrent execution of multiple AgentTask instances
    with result aggregation.
    """

    def __init__(
        self,
        name: str,
        tasks: List[AgentTask],
        max_workers: Optional[int] = None,
        aggregate_results: bool = True,
    ):
        """Initialize parallel agent task.

        Args:
            name: Name of the parallel task group
            tasks: List of AgentTask instances to execute
            max_workers: Maximum number of concurrent workers (default: min(4, len(tasks)))
            aggregate_results: Whether to aggregate results into single dict
        """
        self.name = name
        self.tasks = tasks
        self.max_workers = max_workers or min(4, len(tasks))
        self.aggregate_results = aggregate_results
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, str] = {}

    def execute(self, executor_func: callable, context: Context) -> Dict[str, Any]:
        """Execute tasks in parallel.

        Args:
            executor_func: Function to execute each task (takes task and context)
            context: Execution context

        Returns:
            Aggregated results from all tasks
        """
        self.results.clear()
        self.errors.clear()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(executor_func, task, context): task for task in self.tasks
            }

            # Collect results as they complete
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    self.results[task.name] = result
                except Exception as e:
                    self.errors[task.name] = str(e)

        # Aggregate results if requested
        if self.aggregate_results:
            return {
                "name": self.name,
                "status": "completed" if not self.errors else "completed_with_errors",
                "results": self.results,
                "errors": self.errors,
                "task_count": len(self.tasks),
                "success_count": len(self.results),
                "error_count": len(self.errors),
            }
        else:
            return self.results

    def __repr__(self) -> str:
        """String representation of the parallel task."""
        return f"ParallelAgentTask(name='{self.name}', tasks={len(self.tasks)})"
