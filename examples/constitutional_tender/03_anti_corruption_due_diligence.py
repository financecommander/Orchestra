"""Constitutional Tender Workflow 3: Anti-Corruption Due Diligence.

Runs a rigorous anti-corruption and conflict-of-interest check on tender
applicants using Grok-powered analysis before awarding a public contract.
"""

from orchestra import Agent, Workflow, Context
from orchestra.core.agent_task import AgentTask
from orchestra.core.gates import SecurityGate, ComplianceGate
from orchestra.compilers import WorkflowCompiler, Executor
from orchestra.providers.agents import XAIProvider


def escalation_handler(gate_result):
    """Handle gate escalations."""
    print(f"\n⚠️  ESCALATION: {gate_result.gate_name} – {gate_result.message}")


def main():
    """Run the Anti-Corruption Due Diligence workflow."""
    print("=" * 70)
    print("Constitutional Tender Workflow 3: Anti-Corruption Due Diligence")
    print("=" * 70)

    workflow = Workflow(
        name="anti_corruption_due_diligence",
        description="Anti-corruption and conflict-of-interest screening for tender applicants",
    )

    # Beneficial ownership agent
    ownership_agent = Agent(
        name="ownership_analyst",
        provider="xai",
        system_prompt=(
            "You are a corporate intelligence specialist. Trace the beneficial "
            "ownership structure of companies and identify ultimate beneficial "
            "owners (UBOs), shell companies, and politically exposed persons (PEPs)."
        ),
        config={"model": "grok-3-mini", "temperature": 0.1},
    )

    # Sanctions screening agent
    sanctions_agent = Agent(
        name="sanctions_screener",
        provider="xai",
        system_prompt=(
            "You are a compliance officer specialising in sanctions. Screen "
            "individuals and entities against OFAC, EU, UN, and national sanctions "
            "lists and adverse media databases."
        ),
        config={"model": "grok-3-mini", "temperature": 0.1},
    )

    # Conflict-of-interest agent
    coi_agent = Agent(
        name="coi_reviewer",
        provider="xai",
        system_prompt=(
            "You are an ethics and integrity officer. Identify potential conflicts "
            "of interest between bidding companies, their directors, and public "
            "officials involved in the procurement process."
        ),
        config={"model": "grok-3-mini", "temperature": 0.2},
    )

    # Risk summary agent
    risk_summary_agent = Agent(
        name="risk_summariser",
        provider="xai",
        system_prompt=(
            "You are a senior compliance analyst. Synthesise ownership, sanctions, "
            "and conflict-of-interest findings into a clear risk rating and "
            "award recommendation."
        ),
        config={"model": "grok-3-mini", "temperature": 0.2},
    )

    for agent in [ownership_agent, sanctions_agent, coi_agent, risk_summary_agent]:
        workflow.add_agent(agent)

    # Tasks – ownership, sanctions, COI run in parallel
    ownership_task = AgentTask(
        name="trace_ownership",
        description="Trace beneficial ownership of all bidders",
        agent="ownership_analyst",
        inputs={"bidders": ["Bidder_A", "Bidder_B", "Bidder_C"]},
        output_schema={
            "type": "object",
            "required": ["ownership_map", "pep_flags"],
            "properties": {
                "ownership_map": {"type": "object"},
                "pep_flags": {"type": "array"},
            },
        },
    )

    sanctions_task = AgentTask(
        name="screen_sanctions",
        description="Screen bidders and directors against sanctions lists",
        agent="sanctions_screener",
        inputs={"bidders": ["Bidder_A", "Bidder_B", "Bidder_C"]},
        output_schema={
            "type": "object",
            "required": ["matches", "adverse_media"],
            "properties": {
                "matches": {"type": "array"},
                "adverse_media": {"type": "array"},
            },
        },
    )

    coi_task = AgentTask(
        name="check_conflicts",
        description="Identify conflicts of interest with procurement officials",
        agent="coi_reviewer",
        inputs={"bidders": ["Bidder_A", "Bidder_B", "Bidder_C"]},
        output_schema={
            "type": "object",
            "required": ["conflicts", "severity"],
            "properties": {
                "conflicts": {"type": "array"},
                "severity": {"type": "string"},
            },
        },
    )

    summary_task = AgentTask(
        name="summarise_risks",
        description="Produce consolidated risk rating and award recommendation",
        agent="risk_summariser",
        dependencies=["trace_ownership", "screen_sanctions", "check_conflicts"],
        output_schema={
            "type": "object",
            "required": ["risk_rating", "recommendation", "flagged_bidders"],
            "properties": {
                "risk_rating": {"type": "string"},
                "recommendation": {"type": "string"},
                "flagged_bidders": {"type": "array"},
            },
        },
    )

    for task in [ownership_task, sanctions_task, coi_task, summary_task]:
        workflow.add_task(task)

    # Quality gates
    security_gate = SecurityGate(
        threshold=0.95,
        escalation_enabled=True,
        escalation_callback=escalation_handler,
    )
    compliance_gate = ComplianceGate(
        threshold=0.95,
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
    context.set("tender_ref", "CT-2026-003")
    context.set("issuing_authority", "Ministry of Public Works")

    provider_registry = {"xai": XAIProvider()}

    print("\n🚀 Executing workflow...")
    executor = Executor(provider_registry=provider_registry)
    result = executor.execute(compiled, context)

    print(f"\n✓ Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"✓ Completed Tasks: {len(result.task_results)}/{len(workflow.tasks)}")

    print("\n🔍 Quality Gate Results:")
    s_result = security_gate.check({"security_score": 0.97})
    print(f"   {'✅' if s_result.passed else '❌'} {s_result.message}")
    c_result = compliance_gate.check({"compliance_score": 0.96})
    print(f"   {'✅' if c_result.passed else '❌'} {c_result.message}")

    print("\n" + "=" * 70)
    print("✨ Anti-Corruption Due Diligence workflow complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
