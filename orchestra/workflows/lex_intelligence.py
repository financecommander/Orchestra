# orchestra/workflows/lex_intelligence.py
from orchestra.core.workflow import Workflow
from orchestra.core.agent import Agent
from orchestra.core.task import AgentTask, ParallelAgentTask
from orchestra.core.context import Context
from orchestra.core.gates import SecurityGate, ComplianceGate, PerformanceGate, FinancialAccuracyGate

def build_lex_intelligence_workflow(user_query: str, context_data: dict = None) -> Workflow:
    ctx = Context(initial_data={
        "query": user_query,
        "domain": "general_finance_legal",  # can be overridden to "real_estate", "tokenization", etc.
        **(context_data or {})
    })

    workflow = Workflow("Lex Intelligence v2 – Orchestra Edition", context=ctx)

    # === AGENTS (mirrors your current 6-agent CrewAI setup) ===
    researcher = Agent("lead_researcher", "openai", model="gpt-4o-2026-02", temperature=0.3)
    contrarian = Agent("contrarian_analyst", "anthropic", model="claude-opus-4.6", temperature=0.4)
    regulator = Agent("regulatory_scanner", "gemini", model="gemini-2.5-pro", temperature=0.2)  # now native!
    quant = Agent("quantitative_modeler", "openai", model="gpt-4o-2026-02", temperature=0.1)
    synthesizer = Agent("convergence_synthesizer", "anthropic", model="claude-opus-4.6", temperature=0.2)
    editor = Agent("final_editor", "anthropic", model="claude-opus-4.6", temperature=0.1)

    # === TASKS ===
    research_task = AgentTask(
        name="research",
        agent=researcher,
        prompt="""You are Lead Researcher. Perform deep live research on the query. 
        Output structured findings with sources.""",
        output_schema={"findings": "list", "sources": "list"}
    )

    contrarian_task = AgentTask(
        name="contrarian",
        agent=contrarian,
        prompt="Challenge all assumptions from research. Find weaknesses and alternative views.",
        depends_on=research_task
    )

    regulatory_task = AgentTask(
        name="regulatory",
        agent=regulator,
        prompt="Scan all regulatory, compliance, zoning, securities, and constitutional tender implications.",
        depends_on=research_task
    )

    quant_task = AgentTask(
        name="quant",
        agent=quant,
        prompt="Build financial models, Monte Carlo, sensitivities, or valuation where applicable.",
        depends_on=[research_task, regulatory_task]
    )

    synth_task = AgentTask(
        name="synthesis",
        agent=synthesizer,
        prompt="Converge all inputs into a single coherent analysis with clear recommendations.",
        depends_on=[contrarian_task, regulatory_task, quant_task]
    )

    final_task = AgentTask(
        name="final_output",
        agent=editor,
        prompt="Polish into investor/lender-grade executive document with executive summary, risks, next steps.",
        depends_on=synth_task
    )

    # Parallel final polishing + Forge modeling (your new coding system)
    parallel_final = ParallelAgentTask(
        name="final_parallel",
        tasks=[final_task],
        # Forge will be added here in next step
    )

    workflow.add_tasks([research_task, contrarian_task, regulatory_task, quant_task, synth_task, parallel_final])

    # === YOUR FINANCE-GRADE QUALITY GATES ===
    workflow.add_gate(SecurityGate())
    workflow.add_gate(ComplianceGate())
    workflow.add_gate(PerformanceGate())
    workflow.add_gate(FinancialAccuracyGate(min_confidence=0.85))

    return workflow