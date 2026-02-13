# Orchestra

Python DSL for multi-agent orchestration

## Overview

Orchestra is a Python Domain-Specific Language (DSL) designed for orchestrating multi-agent systems. It provides a clean, declarative way to define workflows, agents, and tasks that work together to accomplish complex goals.

## Features

- **Declarative Workflow Definition**: Define complex multi-agent workflows using Python
- **Task Dependencies**: Manage task execution order with dependency tracking
- **Agent Abstraction**: Support for various AI providers (LLMs, custom implementations)
- **Multi-Agent Providers**: Built-in support for Anthropic Claude, OpenAI, and XAI Grok
- **Quality Gates**: Security, compliance, and performance validation with escalation
- **Schema Validation**: Input/output schema validation for agent tasks
- **Context Management**: Share state and data across tasks and agents
- **Parallel Execution**: Automatic identification of tasks that can run in parallel
- **Retry Logic**: Exponential backoff retry for API failures
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
  - **Agent Providers**: Anthropic Claude, OpenAI, XAI Grok with retry logic
- **Quality Gates**: Security, compliance, and performance validation
- **Agent Tasks**: Enhanced tasks with schema validation and parallel execution
- **Executors**: Task and workflow execution engine

## Multi-Agent Orchestration

### Using AI Provider Agents

Orchestra supports multiple AI providers with built-in retry logic and environment variable configuration:

```python
from orchestra import Agent, Workflow
from orchestra.providers.agents import AnthropicProvider, OpenAIProvider, XAIProvider
from orchestra.core.agent_task import AgentTask
from orchestra.compilers import Executor

# Create agents with different providers
claude_agent = Agent(
    name="architect",
    provider="anthropic",
    system_prompt="You are a system architect",
    config={"model": "claude-3-5-sonnet-20241022"}
)

gpt_agent = Agent(
    name="developer",
    provider="openai",
    system_prompt="You are a senior developer",
    config={"model": "gpt-4"}
)

grok_agent = Agent(
    name="auditor",
    provider="xai",
    system_prompt="You are a security auditor",
    config={"model": "grok-beta"}
)

# Set up environment variables for API keys
# export ANTHROPIC_API_KEY="your-key"
# export OPENAI_API_KEY="your-key"
# export XAI_API_KEY="your-key"

# Register providers
provider_registry = {
    "anthropic": AnthropicProvider(),
    "openai": OpenAIProvider(),
    "xai": XAIProvider()
}

executor = Executor(provider_registry=provider_registry)
```

### Quality Gates

Validate workflow outputs with quality gates:

```python
from orchestra.core.gates import SecurityGate, ComplianceGate, PerformanceGate

# Define quality gates
security_gate = SecurityGate(
    threshold=0.85,
    escalation_enabled=True,
    escalation_callback=lambda result: print(f"Security issue: {result.message}")
)

compliance_gate = ComplianceGate(threshold=0.95)
performance_gate = PerformanceGate(threshold=500.0)  # 500ms max latency

# Check results
audit_data = {
    "security_score": 0.92,
    "compliance_score": 0.97,
    "latency": 350.5
}

security_result = security_gate.check(audit_data)
if security_result.passed:
    print("Security check passed!")
```

### Schema Validation

Validate task inputs and outputs:

```python
from orchestra.core.agent_task import AgentTask

# Task with schema validation
task = AgentTask(
    name="process_payment",
    description="Process payment transaction",
    agent="payment_processor",
    input_schema={
        "type": "object",
        "required": ["amount", "currency"],
        "properties": {
            "amount": {"type": "number"},
            "currency": {"type": "string"}
        }
    },
    output_schema={
        "type": "object",
        "required": ["transaction_id", "status"],
        "properties": {
            "transaction_id": {"type": "string"},
            "status": {"type": "string"}
        }
    }
)

# Validate input
valid_input = {"amount": 100.50, "currency": "USD"}
if task.validate_input(valid_input):
    print("Input is valid")
```

### Parallel Agent Execution

Run multiple agents concurrently:

```python
from orchestra.core.agent_task import ParallelAgentTask

# Create parallel tasks
audit_tasks = [
    AgentTask(name="security_audit", description="Security check", agent="security"),
    AgentTask(name="compliance_audit", description="Compliance check", agent="compliance"),
    AgentTask(name="performance_audit", description="Performance check", agent="performance")
]

parallel = ParallelAgentTask(
    name="parallel_audits",
    tasks=audit_tasks,
    max_workers=3
)

# Execute in parallel
def task_executor(task, context):
    # Your execution logic
    return {"status": "completed"}

result = parallel.execute(task_executor, context)
print(f"Completed {result['success_count']}/{result['task_count']} tasks")
```

### Complete Example

See `examples/fintech_workflow.py` for a complete multi-stage pipeline with:
- Design stage using Claude
- Build stage using OpenAI
- Parallel dual audit using Grok
- Quality gates with escalation

```bash
python examples/fintech_workflow.py
```

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

