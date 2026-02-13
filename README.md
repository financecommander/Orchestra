# Orchestra

Python DSL for multi-agent orchestration

## Overview

Orchestra is a Python Domain-Specific Language (DSL) designed for orchestrating multi-agent systems. It provides a clean, declarative way to define workflows, agents, and tasks that work together to accomplish complex goals.

## Features

- **Declarative Workflow Definition**: Define complex multi-agent workflows using Python
- **Task Dependencies**: Manage task execution order with dependency tracking
- **Agent Abstraction**: Support for various AI providers (LLMs, custom implementations)
- **Context Management**: Share state and data across tasks and agents
- **Parallel Execution**: Automatic identification of tasks that can run in parallel
- **Type Safety**: Comprehensive type hints and validation

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

### Basic Workflow Example

```python
from orchestra import Agent, Task, Workflow, Context
from orchestra.compilers import WorkflowCompiler, Executor

# Create a workflow
workflow = Workflow(
    name="data_analysis",
    description="Analyze data with multiple agents"
)

# Define agents
data_agent = Agent(name="data_collector", provider="llm")
analysis_agent = Agent(name="analyzer", provider="llm")

# Add agents to workflow
workflow.add_agent(data_agent)
workflow.add_agent(analysis_agent)

# Define tasks
collect_task = Task(
    name="collect_data",
    description="Collect data from sources",
    agent="data_collector"
)

analyze_task = Task(
    name="analyze_data",
    description="Analyze collected data",
    agent="analyzer",
    dependencies=["collect_data"]
)

# Add tasks to workflow
workflow.add_task(collect_task)
workflow.add_task(analyze_task)

# Compile and execute
compiler = WorkflowCompiler()
compiled_workflow = compiler.compile(workflow)

executor = Executor()
result = executor.execute(compiled_workflow)

print(f"Workflow completed: {result.success}")
```

### Parallel Task Execution

```python
# Tasks without dependencies run in parallel
task1 = Task(name="task1", description="Independent task 1")
task2 = Task(name="task2", description="Independent task 2")
task3 = Task(name="task3", description="Independent task 3")

workflow.add_task(task1)
workflow.add_task(task2)
workflow.add_task(task3)

# Add a final task that depends on all parallel tasks
final_task = Task(
    name="combine",
    description="Combine results",
    dependencies=["task1", "task2", "task3"]
)
workflow.add_task(final_task)
```

### Using Context

```python
# Create a context with shared data
context = Context()
context.set("config", {"model": "gpt-4", "temperature": 0.7})
context.set("data_source", "database")

# Execute with context
result = executor.execute(workflow, context)

# Access task results from context
task1_result = context.get("task.task1.result")
```

## Architecture

Orchestra consists of several key components:

- **Core**: Base classes for Agent, Task, Workflow, and Context
- **Compilers**: Workflow compilation and validation
- **Providers**: Extensible provider system for different execution backends
- **Executors**: Task and workflow execution engine

## Testing

Run the test suite:

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# All tests with coverage
pytest tests/ --cov=orchestra --cov-report=term
```

## Development

Format code:

```bash
black .
```

Lint code:

```bash
ruff check .
```

Type checking:

```bash
mypy orchestra/
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

