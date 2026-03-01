"""Constitutional Tender Workflow 2: Bid Evaluation & Scoring.

Multi-agent pipeline that evaluates competing bids for a public procurement
tender using objective scoring criteria and Grok-powered analysis.
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
    """Run the Bid Evaluation & Scoring workflow."""
    print("=" * 70)
    print("Constitutional Tender Workflow 2: Bid Evaluation & Scoring")
    print("=" * 70)

    workflow = Workflow(
        name="bid_evaluation",
        description="Objective multi-criteria evaluation of competing tender bids",
    )

    # Criteria definition agent
    criteria_agent = Agent(
        name="criteria_analyst",
        provider="xai",
        system_prompt=(
            "You are a procurement specialist. Define objective, measurable "
            "evaluation criteria for public tender bids including technical, "
            "financial, and qualitative dimensions."
        ),
        config={"model": "grok-3-mini", "temperature": 0.2},
    )

    # Technical evaluation agent
    tech_evaluator = Agent(
        name="technical_evaluator",
        provider="xai",
        system_prompt=(
            "You are a technical assessor. Score each bid on technical merit: "
            "solution quality, delivery plan, team qualifications, and innovation."
        ),
        config={"model": "grok-3-mini", "temperature": 0.2},
    )

    # Financial evaluation agent
    financial_evaluator = Agent(
        name="financial_evaluator",
        provider="xai",
        system_prompt=(
            "You are a financial evaluator. Score each bid on financial merit: "
            "price competitiveness, cost transparency, value-for-money, and "
            "financial stability of the bidder."
        ),
        config={"model": "grok-3-mini", "temperature": 0.1},
    )

    # Ranking agent
    ranking_agent = Agent(
        name="bid_ranker",
        provider="xai",
        system_prompt=(
            "You are an impartial procurement judge. Combine technical and "
            "financial scores to produce a final weighted ranking of bids, "
            "with justification for the recommended award."
        ),
        config={"model": "grok-3-mini", "temperature": 0.1},
    )

    for agent in [criteria_agent, tech_evaluator, financial_evaluator, ranking_agent]:
        workflow.add_agent(agent)

    # Tasks
    define_criteria = AgentTask(
        name="define_criteria",
        description="Define scoring criteria and weightings for bid evaluation",
        agent="criteria_analyst",
        inputs={
            "tender_type": "IT infrastructure",
            "budget": 5000000,
            "duration_months": 24,
        },
        output_schema={
            "type": "object",
            "required": ["criteria", "weightings"],
            "properties": {
                "criteria": {"type": "array"},
                "weightings": {"type": "object"},
            },
        },
    )

    # Technical and financial evaluation run in parallel
    tech_eval = AgentTask(
        name="technical_evaluation",
        description="Score all bids on technical criteria",
        agent="technical_evaluator",
        dependencies=["define_criteria"],
        inputs={"bids": ["Bidder_A", "Bidder_B", "Bidder_C"]},
        output_schema={
            "type": "object",
            "required": ["scores"],
            "properties": {"scores": {"type": "object"}},
        },
    )

    financial_eval = AgentTask(
        name="financial_evaluation",
        description="Score all bids on financial criteria",
        agent="financial_evaluator",
        dependencies=["define_criteria"],
        inputs={"bids": ["Bidder_A", "Bidder_B", "Bidder_C"]},
        output_schema={
            "type": "object",
            "required": ["scores"],
            "properties": {"scores": {"type": "object"}},
        },
    )

    rank_bids = AgentTask(
        name="rank_bids",
        description="Produce final weighted ranking and award recommendation",
        agent="bid_ranker",
        dependencies=["technical_evaluation", "financial_evaluation"],
        output_schema={
            "type": "object",
            "required": ["ranking", "recommended_award", "justification"],
            "properties": {
                "ranking": {"type": "array"},
                "recommended_award": {"type": "string"},
                "justification": {"type": "string"},
            },
        },
    )

    for task in [define_criteria, tech_eval, financial_eval, rank_bids]:
        workflow.add_task(task)

    # Quality gates
    compliance_gate = ComplianceGate(
        threshold=0.85,
        escalation_enabled=True,
        escalation_callback=escalation_handler,
    )
    performance_gate = PerformanceGate(
        threshold=300.0,
        escalation_enabled=True,
        escalation_callback=escalation_handler,
    )

    # Compile and execute
    compiler = WorkflowCompiler()
    compiled = compiler.compile(workflow)
    plan = compiler.get_execution_plan(compiled)

    print(f"\n📋 Execution Plan ({len(plan)} stages):")
    for i, stage in enumerate(plan):
        label = "(Parallel)" if len(stage) > 1 else ""
        print(f"   Stage {i + 1} {label}: {stage}")

    context = Context()
    context.set("tender_ref", "CT-2026-002")
    context.set("evaluation_date", "2026-03-01")

    provider_registry = {"xai": XAIProvider()}

    print("\n🚀 Executing workflow...")
    executor = Executor(provider_registry=provider_registry)
    result = executor.execute(compiled, context)

    print(f"\n✓ Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"✓ Completed Tasks: {len(result.task_results)}/{len(workflow.tasks)}")

    print("\n🔍 Quality Gate Results:")
    c_result = compliance_gate.check({"compliance_score": 0.91})
    print(f"   {'✅' if c_result.passed else '❌'} {c_result.message}")
    p_result = performance_gate.check({"latency": 210.0})
    print(f"   {'✅' if p_result.passed else '❌'} {p_result.message}")

    print("\n" + "=" * 70)
    print("✨ Bid Evaluation workflow complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
