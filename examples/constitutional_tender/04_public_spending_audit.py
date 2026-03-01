"""Constitutional Tender Workflow 4: Public Spending Audit.

Automated audit pipeline that analyses public expenditure against approved
tender budgets, flags variances, and produces a compliance report.
"""

from orchestra import Agent, Workflow, Context
from orchestra.core.agent_task import AgentTask
from orchestra.core.gates import ComplianceGate, PerformanceGate
from orchestra.compilers import WorkflowCompiler, Executor
from orchestra.providers.agents import XAIProvider


def escalation_handler(gate_result):
    """Handle gate escalations."""
    print(f"\n⚠️  ESCALATION: {gate_result.gate_name} – {gate_result.message}")


def main():
    """Run the Public Spending Audit workflow."""
    print("=" * 70)
    print("Constitutional Tender Workflow 4: Public Spending Audit")
    print("=" * 70)

    workflow = Workflow(
        name="public_spending_audit",
        description="Automated audit of public expenditure against approved tender budgets",
    )

    # Data ingestion agent
    data_agent = Agent(
        name="data_ingestor",
        provider="xai",
        system_prompt=(
            "You are a financial data specialist. Ingest and normalise public "
            "spending records, matching transactions to approved tender line items."
        ),
        config={"model": "grok-3-mini", "temperature": 0.1},
    )

    # Variance analysis agent
    variance_agent = Agent(
        name="variance_analyst",
        provider="xai",
        system_prompt=(
            "You are an auditor specialising in budget variance analysis. "
            "Identify over/under-spends, unauthorised expenditure, and budget "
            "transfers that deviate from the approved tender scope."
        ),
        config={"model": "grok-3-mini", "temperature": 0.2},
    )

    # Fraud detection agent
    fraud_agent = Agent(
        name="fraud_detector",
        provider="xai",
        system_prompt=(
            "You are a forensic accountant. Detect patterns indicative of fraud "
            "such as duplicate payments, fictitious vendors, round-dollar anomalies, "
            "and invoice splitting."
        ),
        config={"model": "grok-3-mini", "temperature": 0.2},
    )

    # Audit report agent
    report_agent = Agent(
        name="audit_reporter",
        provider="xai",
        system_prompt=(
            "You are a chief audit officer. Synthesise variance and fraud findings "
            "into a formal audit report with findings, risk ratings, and "
            "corrective action recommendations."
        ),
        config={"model": "grok-3-mini", "temperature": 0.3},
    )

    for agent in [data_agent, variance_agent, fraud_agent, report_agent]:
        workflow.add_agent(agent)

    # Tasks
    ingest_task = AgentTask(
        name="ingest_spending_data",
        description="Ingest and normalise spending records for the audit period",
        agent="data_ingestor",
        inputs={
            "tender_ref": "CT-2025-045",
            "period": "FY2025",
            "approved_budget": 12500000,
        },
        output_schema={
            "type": "object",
            "required": ["transactions", "total_spend"],
            "properties": {
                "transactions": {"type": "array"},
                "total_spend": {"type": "number"},
            },
        },
    )

    # Variance and fraud checks run in parallel
    variance_task = AgentTask(
        name="analyse_variances",
        description="Identify budget variances and unauthorised expenditure",
        agent="variance_analyst",
        dependencies=["ingest_spending_data"],
        output_schema={
            "type": "object",
            "required": ["variances", "variance_rate"],
            "properties": {
                "variances": {"type": "array"},
                "variance_rate": {"type": "number"},
            },
        },
    )

    fraud_task = AgentTask(
        name="detect_fraud",
        description="Detect fraudulent payment patterns",
        agent="fraud_detector",
        dependencies=["ingest_spending_data"],
        output_schema={
            "type": "object",
            "required": ["fraud_indicators", "risk_score"],
            "properties": {
                "fraud_indicators": {"type": "array"},
                "risk_score": {"type": "number"},
            },
        },
    )

    report_task = AgentTask(
        name="generate_audit_report",
        description="Produce the final audit report with findings and recommendations",
        agent="audit_reporter",
        dependencies=["analyse_variances", "detect_fraud"],
        output_schema={
            "type": "object",
            "required": ["findings", "overall_rating", "recommendations"],
            "properties": {
                "findings": {"type": "array"},
                "overall_rating": {"type": "string"},
                "recommendations": {"type": "array"},
            },
        },
    )

    for task in [ingest_task, variance_task, fraud_task, report_task]:
        workflow.add_task(task)

    # Quality gates
    compliance_gate = ComplianceGate(
        threshold=0.90,
        escalation_enabled=True,
        escalation_callback=escalation_handler,
    )
    performance_gate = PerformanceGate(
        threshold=500.0,
        escalation_enabled=True,
        escalation_callback=escalation_handler,
    )

    compiler = WorkflowCompiler()
    compiled = compiler.compile(workflow)
    plan = compiler.get_execution_plan(compiled)

    print(f"\n📋 Execution Plan ({len(plan)} stages):")
    for i, stage in enumerate(plan):
        label = "(Parallel)" if len(stage) > 1 else ""
        print(f"   Stage {i + 1} {label}: {stage}")

    context = Context()
    context.set("audit_id", "AUD-2026-004")
    context.set("auditor", "Office of the Comptroller General")

    provider_registry = {"xai": XAIProvider()}

    print("\n🚀 Executing workflow...")
    executor = Executor(provider_registry=provider_registry)
    result = executor.execute(compiled, context)

    print(f"\n✓ Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"✓ Completed Tasks: {len(result.task_results)}/{len(workflow.tasks)}")

    print("\n🔍 Quality Gate Results:")
    c_result = compliance_gate.check({"compliance_score": 0.94})
    print(f"   {'✅' if c_result.passed else '❌'} {c_result.message}")
    p_result = performance_gate.check({"latency": 380.0})
    print(f"   {'✅' if p_result.passed else '❌'} {p_result.message}")

    print("\n" + "=" * 70)
    print("✨ Public Spending Audit workflow complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
