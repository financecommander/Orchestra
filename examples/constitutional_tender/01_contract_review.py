"""Constitutional Tender Workflow 1: Contract Review & Validation.

Orchestrates a multi-agent pipeline that reviews a procurement tender document
for constitutional compliance, financial soundness, and legal validity using
Grok as the primary AI provider.
"""

from orchestra import Agent, Workflow, Context
from orchestra.core.agent_task import AgentTask
from orchestra.core.gates import SecurityGate, ComplianceGate
from orchestra.compilers import WorkflowCompiler, Executor
from orchestra.providers.agents import XAIProvider


def escalation_handler(gate_result):
    """Handle escalation when a quality gate fails."""
    print(f"\n⚠️  ESCALATION: {gate_result.gate_name} – {gate_result.message}")


def main():
    """Run the Contract Review & Validation workflow."""
    print("=" * 70)
    print("Constitutional Tender Workflow 1: Contract Review & Validation")
    print("=" * 70)

    workflow = Workflow(
        name="contract_review",
        description="Review procurement tender for constitutional and legal compliance",
    )

    # Document extraction agent
    extractor = Agent(
        name="document_extractor",
        provider="xai",
        system_prompt=(
            "You are a legal document specialist. Extract structured information "
            "from procurement tender documents including parties, obligations, "
            "timelines, and financial terms."
        ),
        config={"model": "grok-3-mini", "temperature": 0.1},
    )

    # Constitutional compliance agent
    compliance_reviewer = Agent(
        name="compliance_reviewer",
        provider="xai",
        system_prompt=(
            "You are a constitutional law expert specialising in public procurement. "
            "Verify that tender documents comply with constitutional principles: "
            "fair competition, transparency, value-for-money, and anti-corruption."
        ),
        config={"model": "grok-3-mini", "temperature": 0.2},
    )

    # Financial validation agent
    financial_validator = Agent(
        name="financial_validator",
        provider="xai",
        system_prompt=(
            "You are a financial analyst. Validate the financial terms of a tender: "
            "pricing, payment schedules, penalties, and budget alignment."
        ),
        config={"model": "grok-3-mini", "temperature": 0.2},
    )

    # Risk assessment agent
    risk_assessor = Agent(
        name="risk_assessor",
        provider="xai",
        system_prompt=(
            "You are a risk management specialist. Identify and score contractual, "
            "financial, and operational risks in procurement tenders."
        ),
        config={"model": "grok-3-mini", "temperature": 0.3},
    )

    for agent in [extractor, compliance_reviewer, financial_validator, risk_assessor]:
        workflow.add_agent(agent)

    # Tasks
    extract_task = AgentTask(
        name="extract_document",
        description="Extract structured data from the tender document",
        agent="document_extractor",
        inputs={"document": "tender_contract.pdf"},
        output_schema={
            "type": "object",
            "required": ["parties", "obligations", "financial_terms"],
            "properties": {
                "parties": {"type": "array"},
                "obligations": {"type": "array"},
                "financial_terms": {"type": "object"},
            },
        },
    )

    # Compliance and financial checks run in parallel after extraction
    compliance_task = AgentTask(
        name="check_compliance",
        description="Verify constitutional and regulatory compliance",
        agent="compliance_reviewer",
        dependencies=["extract_document"],
        output_schema={
            "type": "object",
            "required": ["compliance_score", "issues"],
            "properties": {
                "compliance_score": {"type": "number"},
                "issues": {"type": "array"},
            },
        },
    )

    financial_task = AgentTask(
        name="validate_financials",
        description="Validate financial terms and pricing",
        agent="financial_validator",
        dependencies=["extract_document"],
        output_schema={
            "type": "object",
            "required": ["financial_score", "anomalies"],
            "properties": {
                "financial_score": {"type": "number"},
                "anomalies": {"type": "array"},
            },
        },
    )

    risk_task = AgentTask(
        name="assess_risks",
        description="Identify and score contractual risks",
        agent="risk_assessor",
        dependencies=["check_compliance", "validate_financials"],
        output_schema={
            "type": "object",
            "required": ["risk_score", "risks"],
            "properties": {
                "risk_score": {"type": "number"},
                "risks": {"type": "array"},
            },
        },
    )

    for task in [extract_task, compliance_task, financial_task, risk_task]:
        workflow.add_task(task)

    # Quality gates
    compliance_gate = ComplianceGate(
        threshold=0.90,
        escalation_enabled=True,
        escalation_callback=escalation_handler,
    )
    security_gate = SecurityGate(
        threshold=0.80,
        escalation_enabled=True,
        escalation_callback=escalation_handler,
    )

    # Compile
    compiler = WorkflowCompiler()
    compiled = compiler.compile(workflow)
    plan = compiler.get_execution_plan(compiled)

    print(f"\n📋 Execution Plan ({len(plan)} stages):")
    for i, stage in enumerate(plan):
        label = "(Parallel)" if len(stage) > 1 else ""
        print(f"   Stage {i + 1} {label}: {stage}")

    # Context
    context = Context()
    context.set("tender_id", "CT-2026-001")
    context.set("issuing_authority", "Department of Finance")

    # Provider
    provider_registry = {"xai": XAIProvider()}

    # Execute
    print("\n🚀 Executing workflow...")
    executor = Executor(provider_registry=provider_registry)
    result = executor.execute(compiled, context)

    print(f"\n✓ Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"✓ Completed Tasks: {len(result.task_results)}/{len(workflow.tasks)}")

    # Gate checks (simulated scores)
    print("\n🔍 Quality Gate Results:")
    c_result = compliance_gate.check({"compliance_score": 0.93})
    print(f"   {'✅' if c_result.passed else '❌'} {c_result.message}")
    s_result = security_gate.check({"security_score": 0.87})
    print(f"   {'✅' if s_result.passed else '❌'} {s_result.message}")

    print("\n" + "=" * 70)
    print("✨ Contract Review workflow complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
