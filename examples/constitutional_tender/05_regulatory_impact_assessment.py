"""Constitutional Tender Workflow 5: Regulatory Change Impact Assessment.

Evaluates the impact of new regulations or constitutional amendments on
existing public tender contracts and recommends required contract modifications.
"""

from orchestra import Agent, Workflow, Context
from orchestra.core.agent_task import AgentTask
from orchestra.core.gates import ComplianceGate, SecurityGate
from orchestra.compilers import WorkflowCompiler, Executor
from orchestra.providers.agents import XAIProvider


def escalation_handler(gate_result):
    """Handle gate escalations."""
    print(f"\n⚠️  ESCALATION: {gate_result.gate_name} – {gate_result.message}")


def main():
    """Run the Regulatory Change Impact Assessment workflow."""
    print("=" * 70)
    print("Constitutional Tender Workflow 5: Regulatory Change Impact Assessment")
    print("=" * 70)

    workflow = Workflow(
        name="regulatory_impact_assessment",
        description="Assess impact of new regulations on existing tender contracts",
    )

    # Regulatory analysis agent
    reg_agent = Agent(
        name="regulatory_analyst",
        provider="xai",
        system_prompt=(
            "You are a regulatory affairs expert. Analyse new legislation, "
            "constitutional amendments, and regulatory updates to identify "
            "obligations that affect existing public procurement contracts."
        ),
        config={"model": "grok-3-mini", "temperature": 0.2},
    )

    # Contract mapping agent
    mapping_agent = Agent(
        name="contract_mapper",
        provider="xai",
        system_prompt=(
            "You are a contract management specialist. Map regulatory requirements "
            "to specific clauses in existing tender contracts, identifying gaps "
            "and non-compliant provisions."
        ),
        config={"model": "grok-3-mini", "temperature": 0.2},
    )

    # Cost impact agent
    cost_agent = Agent(
        name="cost_impact_analyst",
        provider="xai",
        system_prompt=(
            "You are a financial modeller. Estimate the cost impact of regulatory "
            "changes on active contracts, including remediation costs, penalties "
            "for non-compliance, and renegotiation expenses."
        ),
        config={"model": "grok-3-mini", "temperature": 0.2},
    )

    # Amendment drafting agent
    amendment_agent = Agent(
        name="amendment_drafter",
        provider="xai",
        system_prompt=(
            "You are a legal drafter specialising in public contracts. Draft "
            "contract amendment clauses that bring existing tender agreements "
            "into compliance with new regulatory requirements."
        ),
        config={"model": "grok-3-mini", "temperature": 0.3},
    )

    for agent in [reg_agent, mapping_agent, cost_agent, amendment_agent]:
        workflow.add_agent(agent)

    # Tasks
    reg_analysis = AgentTask(
        name="analyse_regulation",
        description="Parse and extract obligations from the new regulation",
        agent="regulatory_analyst",
        inputs={
            "regulation": "Procurement Amendment Act 2026",
            "effective_date": "2026-04-01",
        },
        output_schema={
            "type": "object",
            "required": ["obligations", "effective_date", "grace_period_days"],
            "properties": {
                "obligations": {"type": "array"},
                "effective_date": {"type": "string"},
                "grace_period_days": {"type": "number"},
            },
        },
    )

    # Contract mapping and cost impact run in parallel
    contract_mapping = AgentTask(
        name="map_contracts",
        description="Identify affected contract clauses for each active tender",
        agent="contract_mapper",
        dependencies=["analyse_regulation"],
        inputs={"active_contracts": ["CT-2025-045", "CT-2025-067", "CT-2026-001"]},
        output_schema={
            "type": "object",
            "required": ["affected_contracts", "non_compliant_clauses"],
            "properties": {
                "affected_contracts": {"type": "array"},
                "non_compliant_clauses": {"type": "object"},
            },
        },
    )

    cost_impact = AgentTask(
        name="estimate_cost_impact",
        description="Model financial impact of regulatory compliance changes",
        agent="cost_impact_analyst",
        dependencies=["analyse_regulation"],
        output_schema={
            "type": "object",
            "required": ["total_cost_estimate", "breakdown"],
            "properties": {
                "total_cost_estimate": {"type": "number"},
                "breakdown": {"type": "object"},
            },
        },
    )

    amendment_task = AgentTask(
        name="draft_amendments",
        description="Draft contract amendments to achieve regulatory compliance",
        agent="amendment_drafter",
        dependencies=["map_contracts", "estimate_cost_impact"],
        output_schema={
            "type": "object",
            "required": ["amendments", "priority_contracts"],
            "properties": {
                "amendments": {"type": "object"},
                "priority_contracts": {"type": "array"},
            },
        },
    )

    for task in [reg_analysis, contract_mapping, cost_impact, amendment_task]:
        workflow.add_task(task)

    # Quality gates
    compliance_gate = ComplianceGate(
        threshold=0.92,
        escalation_enabled=True,
        escalation_callback=escalation_handler,
    )
    security_gate = SecurityGate(
        threshold=0.85,
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
    context.set("assessment_id", "RIA-2026-005")
    context.set("department", "Office of the Solicitor General")

    provider_registry = {"xai": XAIProvider()}

    print("\n🚀 Executing workflow...")
    executor = Executor(provider_registry=provider_registry)
    result = executor.execute(compiled, context)

    print(f"\n✓ Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"✓ Completed Tasks: {len(result.task_results)}/{len(workflow.tasks)}")

    print("\n🔍 Quality Gate Results:")
    c_result = compliance_gate.check({"compliance_score": 0.95})
    print(f"   {'✅' if c_result.passed else '❌'} {c_result.message}")
    s_result = security_gate.check({"security_score": 0.89})
    print(f"   {'✅' if s_result.passed else '❌'} {s_result.message}")

    print("\n" + "=" * 70)
    print("✨ Regulatory Change Impact Assessment workflow complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
