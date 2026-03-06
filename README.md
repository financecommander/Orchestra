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

## What's New in v2.0

Orchestra v2.0 adds three major capabilities for production-grade multi-agent orchestration:

### Advanced Routing (6 strategies)
```python
from orchestra import AgentRouter, RoutingStrategy, CascadeRoute

router = AgentRouter()
agent = await router.route(
    strategy=RoutingStrategy.CASCADE,
    cascade=CascadeRoute(
        try_agent="ultra_reasoning",
        fallback="guardian_claude",
        last_resort="hydra_financial"
    )
)
```

Strategies: `best_for`, `cascade`, `round_robin`, `load_balance`, `cheapest_above`, `dynamic_select`

### Conditional Execution
```python
from orchestra import ConditionalExecutor, GuardClause

executor = ConditionalExecutor(context={"amount": 500000})
await executor.if_then_else(
    condition=amount > 1000000,
    then_block=premium_analysis,
    else_block=standard_analysis
)
```

Supports: if/then/else, guard clauses, pattern matching, parallel conditionals

### Error Handling
```python
from orchestra import ErrorHandler, RetryConfig, CircuitBreaker, CircuitBreakerConfig

# Retry with exponential backoff
result = await ErrorHandler.retry(my_func, RetryConfig(max_attempts=3))

# Circuit breaker protection
breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5))
result = await breaker.execute(risky_api_call)
```

Supports: retry strategies, circuit breaker, timeouts, graceful degradation, decorators

### Orchestra DSL v2.0 Syntax
```orchestra
workflow credit_analysis {
    guard { require: input.amount > 0 }

    if input.amount > 1000000 {
        try {
            agent: guardian_claude
            timeout: 30.0
        } retry {
            strategy: exponential_backoff
            max_attempts: 3
        } catch timeout_error {
            agent: hydra_financial
        }
    } else {
        agent: cascade [
            try: drone_cheap,
            fallback: hydra_financial
        ]
    }
}
```

See [v2.0 Overview](docs/V2_OVERVIEW.md) and [Advanced Features Spec](docs/ADVANCED_FEATURES.md) for full details.

See `examples/v2/` for 6 production workflow examples.

---

## Architecture

Orchestra consists of several key components:

- **Core**: Base classes for Agent, Task, Workflow, and Context
- **Compilers**: Workflow compilation and validation
- **Providers**: Extensible provider system for different execution backends
  - **Agent Providers**: Anthropic Claude, OpenAI, XAI Grok with retry logic
- **Advanced** *(v2.0)*: Routing, conditionals, and error handling
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

### v2.0 Workflow Examples

See `examples/v2/` for Orchestra DSL v2.0 workflow definitions:
- `credit_analysis.orc` - Constitutional Tender (routing + conditionals + errors)
- `tilt_enrichment.orc` - TILT (load balancing + dynamic routing)
- `dfip_analytics.orc` - DFIP (pattern matching + error recovery)
- `fraud_detection.orc` - Fraud detection (guards + validation + retries)
- `adaptive_analysis.orc` - Dynamic agent selection
- `batch_processing.orc` - Batch with resilience

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

## Production Deployment

For production deployment with the Swarm orchestration system, see [super-duper-spork](https://github.com/financecommander/super-duper-spork) - the proprietary AI swarm platform that uses Orchestra as its DSL engine.

## Documentation

- [v2.0 Overview](docs/V2_OVERVIEW.md) - What's new in v2.0
- [Advanced Features Specification](docs/ADVANCED_FEATURES.md) - Full spec for routing, conditionals, error handling

---

## Shapeshifter Architecture Goals

### Adaptive AI Execution, Compression, and Validation System

This section outlines the **future build-out plan** for the Shapeshifter architecture across the existing repository ecosystem.

Shapeshifter introduces:

- adaptive model routing
- compression-aware execution
- layered validation
- distributed worker execution
- telemetry-driven optimization

The goal is to evolve the current centralized swarm architecture into a **task-adaptive AI infrastructure platform**.

#### System Overview

Shapeshifter enables the system to dynamically adjust:

- model size
- compression level
- workflow topology
- compute location
- validation intensity

based on task classification and operational telemetry.

Execution pipeline:

```

task input
↓
task classification
↓
compression profile selection
↓
workflow template selection
↓
execution
↓
validation
↓
escalation (if required)

```

#### Repository Architecture

Shapeshifter builds on the current repository structure.

| Repository | Role |
|---|---|
| `super-duper-spork` | control plane orchestration |
| `Orchestra` | workflow DSL |
| `Triton` | model compilation and compression |
| `AI-PORTAL` | evaluation and experiment management |
| `ProbFlow` | probabilistic routing and uncertainty |
| `BUNNY` | edge worker runtime |

#### Core Architectural Layers

##### Control Plane

Repository: `super-duper-spork`

Responsibilities:

- task intake and routing
- workflow orchestration
- escalation control
- validation ladder management
- telemetry aggregation

Future additions:

```

/routing
/task_classifier
/validation_ladder
/compression_router
/worker_registry

```

##### Workflow Definition

Repository: `Orchestra`

Responsibilities:

- workflow templates
- swarm execution topology
- recursive task decomposition
- validation pipeline definitions

Future additions:

```

/workflow_templates
/shapes
fast_path
reviewer_path
swarm_path
hierarchical_path

```

##### Model Runtime and Compression

Repository: `Triton`

Responsibilities:

- model compilation
- compression pipelines
- ternary runtime kernels
- mixed precision export
- hardware-target optimization

Future additions:

```

/compression_profiles
planner_safe
specialist_balanced
worker_fast
edge_extreme

/layer_sensitivity
/runtime_metrics
/export_targets

```

##### Model Lifecycle and Evaluation

Repository: `AI-PORTAL`

Responsibilities:

- model registry
- experiment tracking
- compression benchmarking
- dataset management
- telemetry dashboards

Future additions:

```

/models
/experiments
/compression_benchmarks
/task_family_metrics

```

##### Routing Intelligence

Repository: `ProbFlow`

Responsibilities:

- uncertainty scoring
- routing optimization
- compression profile selection
- escalation thresholds

Future additions:

```

/routing_models
/confidence_scoring
/expected_value_estimation

```

##### Edge Worker Runtime

Repository: `BUNNY`

Responsibilities:

- lightweight worker runtime
- constrained-device execution
- secure remote worker protocol
- compressed model execution

Future additions:

```

/worker_runtime
/task_executor
/telemetry_client

```

#### Compression Strategy

Compression must be treated as a **routing primitive** rather than a static model property.

The system uses compression profiles.

##### Profiles

###### Planner Safe

Purpose:

- architecture planning
- complex reasoning
- arbitration

Compression:

- minimal quantization
- mixed precision

###### Specialist Balanced

Purpose:

- domain reasoning
- medium complexity tasks

Compression:

- 4–5 bit quantization
- mixed precision

###### Worker Fast

Purpose:

- bounded execution tasks
- high-throughput workers

Compression:

- aggressive quantization
- optional ternary

###### Edge Extreme

Purpose:

- edge nodes
- constrained environments

Compression:

- ternary models
- ultra-low memory footprint

#### Ternary Compression Policy

Ternary compression is applied selectively.

Use cases:

- swarm workers
- microtasks
- edge nodes

Avoid ternary for:

- planners
- reviewer models
- complex reasoning tasks

Layer sensitivity rules:

| Layer | Compression Policy |
|---|---|
| Embeddings | preserve |
| Attention projections | moderate compression |
| Feed-forward layers | aggressive compression |
| Output head | preserve |

#### Task Classification

Tasks are categorized before execution.

| Class | Example Tasks |
|---|---|
| Compress | formatting, tests, lint fixes |
| Balance | bug fixes, repo review |
| Preserve | architecture changes |

Classification inputs:

- scope
- risk
- context size
- expected reasoning depth

#### Validation Architecture

Validation uses a multi-stage ladder.

##### Level 1 — Deterministic Checks

Examples:

- syntax validation
- lint checks
- type checking
- schema validation

##### Level 2 — Semantic Checks

Examples:

- unit tests
- static analysis
- policy rules

##### Level 3 — Reviewer Models

Examples:

- code reviewer
- security reviewer
- compliance reviewer

##### Level 4 — Human Review

Required for:

- high-risk outputs
- unresolved conflicts
- regulatory workflows

#### Worker Self-Validation

Workers return validation metadata.

Example:

```json
{
  "task_id": "123",
  "confidence": 0.84,
  "checks": {
    "lint_pass": true,
    "tests_passed": true
  }
}
```

This allows early rejection of low-quality outputs.

#### Telemetry System

Telemetry is required for adaptive routing.

Metrics tracked:

* success rate
* validation pass rate
* latency
* compression profile performance
* escalation frequency

Repositories responsible:

```
Triton → runtime metrics
AI-PORTAL → dashboards
super-duper-spork → routing telemetry
```

#### Failure Escalation

Escalation ladder:

```
Compress → Balance → Preserve
```

Triggers:

* validation failure
* low confidence
* repeated retries

#### Execution Examples

##### Small Task

```
classification → compress
model → worker_fast
validation → deterministic checks
```

##### Medium Task

```
classification → balance
workflow → planner + workers
validation → semantic checks + reviewer
```

##### Large Task

```
classification → preserve
workflow → hierarchical swarm
validation → reviewer chain + human approval
```

#### Implementation Roadmap

##### Phase 1 — Validation Infrastructure

Repositories:

```
super-duper-spork
Orchestra
```

Deliverables:

* validation ladder
* worker self-check protocol
* task classification system

##### Phase 2 — Compression Profiles

Repositories:

```
Triton
AI-PORTAL
```

Deliverables:

* compression profiles
* benchmark dashboards
* mixed precision policies

##### Phase 3 — Adaptive Routing

Repositories:

```
super-duper-spork
ProbFlow
```

Deliverables:

* compression-aware routing
* confidence scoring
* escalation policies

##### Phase 4 — Distributed Worker Expansion

Repositories:

```
BUNNY
super-duper-spork
```

Deliverables:

* worker registry
* remote task execution
* edge worker support

##### Phase 5 — Telemetry Optimization

Repositories:

```
AI-PORTAL
Triton
ProbFlow
```

Deliverables:

* compression telemetry
* routing optimization
* performance analytics

#### Engineering Principles

Shapeshifter follows a single rule:

> Use the smallest reliable model and workflow capable of completing the task safely.

Compression, routing, and validation all support this objective.

#### Expected Outcomes

Compared to traditional single-model systems:

* improved compute efficiency
* reduced validation burden
* higher scalability
* adaptive model deployment
* improved failure containment

#### Long-Term Vision

Shapeshifter evolves the existing architecture into:

```
Adaptive AI Infrastructure Platform
```

Where:

* routing decisions are telemetry-driven
* models are dynamically selected
* workflows adapt to task complexity
* validation is automated by default

---

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

