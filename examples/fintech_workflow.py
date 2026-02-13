"""Fintech workflow example demonstrating multi-agent orchestration.

This example shows a multi-stage fintech pipeline with:
- Design stage using Claude
- Build stage using OpenAI/Copilot
- Parallel dual audit (Security + Compliance) using Grok
- Quality gates with escalation
"""

from orchestra import Agent, Workflow, Context
from orchestra.core.agent_task import AgentTask
from orchestra.core.gates import SecurityGate, ComplianceGate, PerformanceGate
from orchestra.compilers import WorkflowCompiler, Executor
from orchestra.providers.agents import AnthropicProvider, OpenAIProvider, XAIProvider


def escalation_handler(gate_result):
    """Handle escalation when quality gates fail."""
    print(f"\n{'='*60}")
    print("⚠️  ESCALATION TRIGGERED")
    print(f"{'='*60}")
    print(f"Gate: {gate_result.gate_name}")
    print(f"Message: {gate_result.message}")
    print(f"Metrics: {gate_result.metrics}")
    print(f"{'='*60}\n")


def main():
    """Run the fintech workflow example."""
    print("=" * 70)
    print("Orchestra DSL - Fintech Multi-Agent Workflow")
    print("=" * 70)

    # Create workflow
    workflow = Workflow(
        name="fintech_pipeline",
        description="Multi-stage fintech development pipeline with quality gates",
    )

    # Stage 1: Design Agent (Claude)
    design_agent = Agent(
        name="design_architect",
        provider="anthropic",
        system_prompt="You are a senior fintech system architect. Design secure, compliant financial systems.",
        config={"model": "claude-3-5-sonnet-20241022", "temperature": 0.5},
    )
    workflow.add_agent(design_agent)

    # Stage 2: Build Agent (OpenAI/Copilot)
    build_agent = Agent(
        name="implementation_engineer",
        provider="openai",
        system_prompt="You are an expert software engineer. Implement secure financial systems following best practices.",
        config={"model": "gpt-4", "temperature": 0.3},
    )
    workflow.add_agent(build_agent)

    # Stage 3: Audit Agents (Grok for both security and compliance)
    security_auditor = Agent(
        name="security_auditor",
        provider="xai",
        system_prompt="You are a security expert. Audit code for vulnerabilities and security issues.",
        config={"model": "grok-beta", "temperature": 0.2},
    )
    workflow.add_agent(security_auditor)

    compliance_auditor = Agent(
        name="compliance_auditor",
        provider="xai",
        system_prompt="You are a financial compliance expert. Audit code for regulatory compliance.",
        config={"model": "grok-beta", "temperature": 0.2},
    )
    workflow.add_agent(compliance_auditor)

    # Define tasks with schema validation
    design_task = AgentTask(
        name="design_system",
        description="Design a payment processing system with fraud detection",
        agent="design_architect",
        inputs={
            "requirements": [
                "Process credit card payments",
                "Real-time fraud detection",
                "PCI DSS compliance",
                "Multi-currency support",
            ]
        },
        output_schema={
            "type": "object",
            "required": ["architecture", "components", "security_measures"],
            "properties": {
                "architecture": {"type": "string"},
                "components": {"type": "array"},
                "security_measures": {"type": "array"},
            },
        },
    )
    workflow.add_task(design_task)

    build_task = AgentTask(
        name="implement_system",
        description="Implement the designed payment system",
        agent="implementation_engineer",
        dependencies=["design_system"],
        inputs={"design": "from_design_task"},
        output_schema={
            "type": "object",
            "required": ["implementation", "test_coverage", "performance_metrics"],
            "properties": {
                "implementation": {"type": "string"},
                "test_coverage": {"type": "number"},
                "performance_metrics": {"type": "object"},
            },
        },
    )
    workflow.add_task(build_task)

    # Parallel audit tasks
    security_audit_task = AgentTask(
        name="security_audit",
        description="Perform security audit of the implementation",
        agent="security_auditor",
        dependencies=["implement_system"],
        inputs={"code": "from_implementation"},
        output_schema={
            "type": "object",
            "required": ["security_score", "vulnerabilities", "recommendations"],
            "properties": {
                "security_score": {"type": "number"},
                "vulnerabilities": {"type": "array"},
                "recommendations": {"type": "array"},
            },
        },
    )
    workflow.add_task(security_audit_task)

    compliance_audit_task = AgentTask(
        name="compliance_audit",
        description="Perform compliance audit of the implementation",
        agent="compliance_auditor",
        dependencies=["implement_system"],
        inputs={"code": "from_implementation"},
        output_schema={
            "type": "object",
            "required": [
                "compliance_score",
                "compliance_issues",
                "recommendations",
            ],
            "properties": {
                "compliance_score": {"type": "number"},
                "compliance_issues": {"type": "array"},
                "recommendations": {"type": "array"},
            },
        },
    )
    workflow.add_task(compliance_audit_task)

    # Quality gates
    security_gate = SecurityGate(
        threshold=0.85, escalation_enabled=True, escalation_callback=escalation_handler
    )

    compliance_gate = ComplianceGate(
        threshold=0.95, escalation_enabled=True, escalation_callback=escalation_handler
    )

    performance_gate = PerformanceGate(
        threshold=500.0,
        escalation_enabled=True,
        escalation_callback=escalation_handler,
    )

    print("\n📋 Workflow Configuration:")
    print(f"   Agents: {len(workflow.agents)}")
    print(f"   Tasks: {len(workflow.tasks)}")
    print("   Quality Gates: 3 (Security, Compliance, Performance)")

    # Compile workflow
    print("\n🔧 Compiling workflow...")
    compiler = WorkflowCompiler()
    compiled_workflow = compiler.compile(workflow)

    # Get execution plan
    execution_plan = compiler.get_execution_plan(compiled_workflow)
    print(f"\n📊 Execution Plan ({len(execution_plan)} stages):")
    for i, level in enumerate(execution_plan):
        if len(level) > 1:
            print(f"   Stage {i + 1} (Parallel): {level}")
        else:
            print(f"   Stage {i + 1}: {level}")

    # Create execution context
    context = Context()
    context.set("project", "PaymentProcessor")
    context.set("environment", "development")
    context.set("start_time", "2026-02-13T07:30:00Z")

    # Register providers
    provider_registry = {
        "anthropic": AnthropicProvider(),
        "openai": OpenAIProvider(),
        "xai": XAIProvider(),
    }

    # Execute workflow
    print("\n🚀 Executing workflow...")
    print("-" * 70)
    executor = Executor(provider_registry=provider_registry)
    result = executor.execute(compiled_workflow, context)

    # Display results
    print("\n" + "=" * 70)
    print("📈 Execution Results")
    print("=" * 70)
    print(f"✓ Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"✓ Completed Tasks: {len(result.task_results)}/{len(workflow.tasks)}")

    if result.success:
        print("\n📝 Task Results:")
        for task_name, task_result in result.task_results.items():
            status_emoji = "✅" if task_result.get("status") == "completed" else "❌"
            provider = task_result.get("provider", "unknown")
            print(f"   {status_emoji} {task_name} (via {provider})")

        # Simulate quality gate checks
        print("\n🔍 Quality Gate Checks:")

        # Security check (simulated)
        security_data = {"security_score": 0.92}
        security_result = security_gate.check(security_data)
        gate_emoji = "✅" if security_result.passed else "❌"
        print(f"   {gate_emoji} {security_result.message}")

        # Compliance check (simulated)
        compliance_data = {"compliance_score": 0.97}
        compliance_result = compliance_gate.check(compliance_data)
        gate_emoji = "✅" if compliance_result.passed else "❌"
        print(f"   {gate_emoji} {compliance_result.message}")

        # Performance check (simulated)
        performance_data = {"latency": 350.5}
        performance_result = performance_gate.check(performance_data)
        gate_emoji = "✅" if performance_result.passed else "❌"
        print(f"   {gate_emoji} {performance_result.message}")

        # Check for escalations
        all_passed = (
            security_result.passed and compliance_result.passed and performance_result.passed
        )
        if all_passed:
            print("\n🎉 All quality gates passed! Pipeline complete.")
        else:
            print("\n⚠️  Some quality gates failed. Review escalations above for details.")

    else:
        print("\n❌ Errors occurred:")
        for task_name, error in result.errors.items():
            print(f"   • {task_name}: {error}")

    # Show context after execution
    print("\n📊 Final Context State:")
    print(f"   Variables: {len(context.variables)}")
    print(f"   Execution ID: {context.execution_id}")

    print("\n" + "=" * 70)
    print("✨ Fintech workflow example completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
