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

## Architecture Overview: Shapeshifter Orchestration Model

The system is designed as a **three-layer architecture** that separates orchestration logic, workflow definition, and computational execution.

The architecture supports **adaptive multi-agent workflows**, **distributed execution**, and **compression-aware model routing**.

The three architectural layers are:

```
Adaptive Layer        → Shapeshifter
Control Plane         → super-duper-spork + Orchestra + AI-PORTAL
Execution Plane       → Triton + BUNNY + distributed workers
```

Each layer has distinct responsibilities.

---

### 1. Architectural Layers

#### Adaptive Layer: Shapeshifter

The **Shapeshifter layer** determines how work should be executed.

It is not a single repository. It is a **system-wide orchestration model** implemented across multiple components.

Primary responsibilities:

* task classification
* workflow shape selection
* compression profile selection
* escalation policies
* validation routing
* adaptive swarm topology

Repositories involved:

| Repository          | Role                                   |
| ------------------- | -------------------------------------- |
| `ProbFlow`          | uncertainty scoring and routing policy |
| `super-duper-spork` | task lifecycle and routing execution   |
| `Orchestra`         | workflow templates                     |
| `AI-PORTAL`         | telemetry feedback                     |

---

#### Control Plane

The control plane manages task orchestration and system coordination.

Repositories:

| Repository          | Responsibility                                   |
| ------------------- | ------------------------------------------------ |
| `super-duper-spork` | task lifecycle, scheduling, merge orchestration  |
| `Orchestra`         | workflow DSL                                     |
| `AI-PORTAL`         | session UI, telemetry dashboards, model registry |

Control plane functions:

* task intake
* workflow compilation
* scheduling and dispatch
* validation orchestration
* merge arbitration
* telemetry collection

---

#### Execution Plane

The execution plane performs the actual work.

Repositories:

| Repository | Responsibility                       |
| ---------- | ------------------------------------ |
| `Triton`   | model runtime and compression engine |
| `BUNNY`    | distributed worker runtime           |

Execution environments include:

```
Codespaces workers
container workers
edge workers
local development workers
```

These workers execute tasks dispatched by the control plane.

---

### 2. Key Components

#### Orchestra — Workflow DSL

Repository: `Orchestra`

Orchestra defines the **structure of work**.

Responsibilities:

* task graphs
* dependency relationships
* parallel execution branches
* conditional workflow paths
* validation gates
* workflow templates

Example workflow:

```
planner
 ↓
parallel_workers
 ↓
reviewer
 ↓
merge
```

Orchestra determines **how tasks are structured**.

---

#### super-duper-spork — Control Plane Runtime

Repository: `super-duper-spork`

This is the **swarm control engine**.

Responsibilities:

* task lifecycle management
* worker registry
* queue management
* task dispatch
* merge arbitration
* failure handling
* retry policies
* tracing and observability

It executes the workflows defined by Orchestra.

---

#### Triton — Model Runtime and Compression Engine

Repository: `Triton`

Triton provides the **AI compute engine**.

Responsibilities:

* model compilation
* inference runtime
* compression pipelines
* mixed precision execution
* ternary kernels
* hardware-specific optimization
* model export

Example model profiles:

```
planner_safe
specialist_balanced
worker_fast
edge_extreme
```

Workers load Triton models to perform AI tasks.

---

#### BUNNY — Worker Runtime

Repository: `BUNNY`

BUNNY provides the **distributed worker execution environment**.

Responsibilities:

* secure task execution
* container / Codespaces worker runtime
* edge inference deployment
* execution isolation
* worker telemetry

Workers running BUNNY execute tasks from the control plane.

---

#### AI-PORTAL — System Interface and Telemetry

Repository: `AI-PORTAL`

AI-PORTAL provides the user interface and experiment control.

Responsibilities:

* authenticated user sessions
* Swarm mainframe UI
* Blueprint Editor (visual Orchestra workflow builder)
* model registry
* experiment tracking
* telemetry dashboards
* performance analytics

It visualizes system performance and feeds telemetry into the adaptive layer.

---

### 3. Execution Lifecycle

The system executes tasks through the following pipeline:

```
Task Input
 ↓
Task Classification
 ↓
Workflow Selection
 ↓
Task Graph Compilation
 ↓
Worker Dispatch
 ↓
Model Execution
 ↓
Validation
 ↓
Result Synthesis
```

Step-by-step process:

1. **Task Classification** — Shapeshifter determines task complexity, risk level, compression profile, and workflow shape.

2. **Workflow Compilation** — Orchestra builds the task graph:
   ```
   planner
    ↓
   parallel_workers
    ↓
   review
    ↓
   merge
   ```

3. **Task Dispatch** — `super-duper-spork` schedules tasks to workers.

4. **Execution** — Workers run Triton models (generate code, extract clauses, analyze financial data, etc.).

5. **Validation** — Validation gates: lint checks, test validation, static analysis, review models.

6. **Synthesis** — Results are merged and returned.

---

### 4. Telemetry Feedback Loop

System telemetry drives adaptive optimization.

Metrics collected:

* task latency
* model runtime efficiency
* memory usage
* validation success rates
* worker reliability
* merge success rates

Telemetry flow:

```
Triton runtime metrics
 ↓
AI-PORTAL dashboards
 ↓
ProbFlow routing models
 ↓
Shapeshifter policy updates
```

Routing policies improve automatically over time.

---

### 5. System Design Principles

#### Separation of Concerns

* Orchestra defines workflows
* super-duper-spork executes workflows
* Triton performs model computation
* BUNNY runs workers
* AI-PORTAL manages sessions and telemetry

#### Adaptive Orchestration

Shapeshifter dynamically adjusts:

* workflow structure
* compression profiles
* worker distribution
* validation intensity

#### Horizontal Scalability

Workers scale independently.

```
Control Plane
 ↓
Task Queue
 ↓
Worker Fleet
```

Adding workers increases system throughput without changing orchestration logic.

---

### 6. Repository Responsibility Matrix

| Layer     | Component        | Repository          | Role                            |
| --------- | ---------------- | ------------------- | ------------------------------- |
| Adaptive  | Routing & Policy | `ProbFlow`          | uncertainty scoring and routing |
| Control   | Workflow DSL     | `Orchestra`         | task graph definition           |
| Control   | Swarm Runtime    | `super-duper-spork` | scheduling and orchestration    |
| Execution | Model Runtime    | `Triton`            | AI inference and compression    |
| Execution | Worker Runtime   | `BUNNY`             | distributed execution           |
| Interface | UI & Telemetry   | `AI-PORTAL`         | monitoring and user interaction |

---

### 7. Summary

The architecture is intentionally modular:

```
Shapeshifter → decides how work should run
Orchestra → defines workflow topology
super-duper-spork → executes workflows
Triton → runs AI models
BUNNY → executes tasks
AI-PORTAL → monitors system behavior
```

This separation allows the system to scale while remaining maintainable. Improvements to one layer do not require changes to the others.

---

## GCP Infrastructure

The system runs on four GCP VMs in `us-east1-b`:

| VM                | External IP      | Internal IP  | Role                                      |
| ----------------- | ---------------- | ------------ | ----------------------------------------- |
| `calculus-web`    | 34.148.8.51      | 10.142.0.3   | Public web frontend                       |
| `fc-ai-portal`    | 34.139.78.75     | 10.142.0.2   | AI-PORTAL (frontend :3000, backend :8000) |
| `swarm-gpu`       | 35.227.111.161   | 10.142.0.6   | Triton inference + LLaMA models           |
| `swarm-mainframe` | 34.148.140.31    | 10.142.0.4   | Swarm control plane (super-duper-spork)   |

Traffic flow:

```
User → calculus-web → fc-ai-portal (authenticated UI)
                        ↓ /api/v2/*          → backend (FastAPI)
                        ↓ /swarm/*           → swarm-mainframe
                        ↓ /swarm/api/v1/blueprint/* → blueprint execution
swarm-mainframe → swarm-gpu (Triton inference via internal network)
```

---

## Compression Strategy

Compression is treated as a **routing primitive** rather than a static model property.

### Compression Profiles

| Profile              | Use Case                        | Compression Level                  |
| -------------------- | ------------------------------- | ---------------------------------- |
| **Planner Safe**     | architecture, complex reasoning | minimal quantization, mixed precision |
| **Specialist Balanced** | domain reasoning, mid-complexity | 4–5 bit quantization, mixed precision |
| **Worker Fast**      | bounded tasks, high throughput  | aggressive quantization, optional ternary |
| **Edge Extreme**     | edge nodes, constrained devices | ternary models, ultra-low memory   |

### Ternary Compression Policy

Use ternary for: swarm workers, microtasks, edge nodes.

Avoid ternary for: planners, reviewer models, complex reasoning.

| Layer                  | Compression Policy     |
| ---------------------- | ---------------------- |
| Embeddings             | preserve               |
| Attention projections  | moderate compression   |
| Feed-forward layers    | aggressive compression |
| Output head            | preserve               |

---

## Task Classification

Tasks are categorized before execution.

| Class    | Example Tasks                  | Workflow Shape         |
| -------- | ------------------------------ | ---------------------- |
| Compress | formatting, tests, lint fixes  | fast path              |
| Balance  | bug fixes, repo review         | planner + workers      |
| Preserve | architecture changes           | hierarchical swarm     |

Classification inputs: scope, risk, context size, expected reasoning depth.

---

## Validation Architecture

Validation uses a multi-stage ladder.

| Level | Type                 | Examples                                      |
| ----- | -------------------- | --------------------------------------------- |
| 1     | Deterministic Checks | syntax, lint, type checking, schema validation |
| 2     | Semantic Checks      | unit tests, static analysis, policy rules      |
| 3     | Reviewer Models      | code reviewer, security reviewer, compliance   |
| 4     | Human Review         | high-risk outputs, regulatory workflows        |

### Worker Self-Validation

Workers return validation metadata for early rejection of low-quality outputs:

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

### Failure Escalation

Escalation ladder: `Compress → Balance → Preserve`

Triggers: validation failure, low confidence, repeated retries.

---

## Goals

### Near-Term Goals (Q1–Q2 2026)

1. **Blueprint Editor GA** — Ship the visual Orchestra workflow builder inside AI-PORTAL as a production-grade tool for designing, validating, and executing `.orc` workflows through the Swarm Mainframe.

2. **Orchestra Language Server** — Deliver IDE-grade support for `.orc` files (diagnostics, completions, hover docs) via the LSP server already implemented in `orchestra/lsp/`.

3. **Triton Model Registry Integration** — Complete the live model discovery pipeline: `swarm-gpu` Triton inventory → Orchestra registry → Blueprint Editor model selector → AI-PORTAL dashboards.

4. **End-to-End Workflow Execution** — Close the loop from `.orc` authoring in the Blueprint Editor through `super-duper-spork` scheduling to Triton inference on `swarm-gpu`, with real-time status polling back to the UI.

5. **Validation Ladder v1** — Implement the four-level validation architecture (deterministic → semantic → reviewer → human) as a first-class Orchestra DSL construct with gate syntax.

6. **Compression-Aware Routing** — Route tasks to the correct Triton compression profile based on Shapeshifter's task classification output, verified by ProbFlow confidence scoring.

### Mid-Term Goals (Q3–Q4 2026)

7. **ProbFlow Routing Engine** — Deploy uncertainty-based routing that selects workflow shape, compression profile, and escalation policy per-task using live telemetry regression.

8. **BUNNY Worker Fleet** — Expand execution to distributed workers (Codespaces, containers, edge devices) registered in the `super-duper-spork` worker registry and dispatched via task queue.

9. **Telemetry-Driven Optimization** — Feed runtime metrics (latency, cost, validation pass rate, compression efficiency) from Triton and `super-duper-spork` into ProbFlow to auto-tune routing weights.

10. **Multi-Swarm Topologies** — Support multiple concurrent swarm sessions with different collaboration modes (round table, review chain, specialist, debate) orchestrated by a single Shapeshifter policy.

### Long-Term Goals (2027+)

11. **Self-Healing Workflows** — Workflows that detect failure patterns and restructure themselves (swap agents, adjust compression, re-route to fallback workers) without human intervention.

12. **Federated Execution** — Cross-cloud and cross-org task dispatch where BUNNY workers in different environments execute tasks under a unified control plane.

13. **Adaptive AI Infrastructure Platform** — Fully autonomous system where routing decisions are telemetry-driven, models are dynamically selected, workflows adapt to task complexity, and validation is automated by default.

---

## Roadmap

### Phase 1 — Validation Infrastructure *(in progress)*

Repositories: `super-duper-spork`, `Orchestra`

Deliverables:
* validation ladder (4-level gate system)
* worker self-check protocol
* task classification system
* Orchestra gate DSL syntax (`guard`, `quality_gate`, `circuit_breaker`)

### Phase 2 — Blueprint Editor & Tooling *(in progress)*

Repositories: `Orchestra`, `AI-PORTAL`, `super-duper-spork`

Deliverables:
* Blueprint Editor UI in AI-PORTAL Swarm Mainframe page
* Orchestra LSP server for `.orc` IDE support
* Triton model registry with live discovery
* Parse / generate / validate / execute pipeline

### Phase 3 — Compression Profiles

Repositories: `Triton`, `AI-PORTAL`

Deliverables:
* four named compression profiles (planner_safe, specialist_balanced, worker_fast, edge_extreme)
* benchmark dashboards in AI-PORTAL
* mixed precision policies
* layer sensitivity analysis

### Phase 4 — Adaptive Routing

Repositories: `super-duper-spork`, `ProbFlow`

Deliverables:
* compression-aware routing
* confidence scoring
* escalation policies
* dynamic agent selection

### Phase 5 — Distributed Worker Expansion

Repositories: `BUNNY`, `super-duper-spork`

Deliverables:
* worker registry
* remote task execution protocol
* Codespaces / container / edge worker support
* execution isolation and secure runtime

### Phase 6 — Telemetry Optimization

Repositories: `AI-PORTAL`, `Triton`, `ProbFlow`

Deliverables:
* runtime compression telemetry
* routing optimization feedback loop
* performance analytics dashboards
* auto-tuning routing weights

### Phase 7 — Multi-Swarm & Self-Healing

Repositories: all

Deliverables:
* concurrent swarm topologies
* self-restructuring workflows
* federated execution across environments
* autonomous infrastructure platform

---

## Engineering Principles

> Use the smallest reliable model and workflow capable of completing the task safely.

Compression, routing, and validation all support this objective.

---

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

