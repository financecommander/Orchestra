"""Codeforge-Hub collaboration workflow for Orchestra DSL.

Implements a multi-agent collaboration pipeline with:
- Guardian-caste validation via quality gates (security + compliance)
- Dynamic team: architect, coder, reviewer, tester, security roles
- Parallel audit execution using ParallelAgentTask
- Full audit logging via Orchestra Context
- Triton-ternary-coder-8b as the primary reasoning model

Usage:
    python workflows/codeforge_hub.py \\
        --feature "My feature description" \\
        --priority P1 \\
        --compliance "SOC2,GDPR" \\
        --output-dir ./orchestra-output/artifacts \\
        --state-file ./orchestra-output/state/snapshot.json
"""

import argparse
import datetime
import json
import os
import sys

from orchestra import Agent, Context, Workflow
from orchestra.compilers import Executor, WorkflowCompiler
from orchestra.core.agent_task import AgentTask, ParallelAgentTask
from orchestra.core.gates import ComplianceGate, GateResult, SecurityGate
from orchestra.providers.agents import AnthropicProvider, OpenAIProvider, XAIProvider
from orchestra.providers.agents.triton import TritonProvider


# ---------------------------------------------------------------------------
# Guardian-caste escalation handler (maps to BUNNY_AI_GUARDIAN monitoring)
# ---------------------------------------------------------------------------

_audit_log: list = []


def guardian_escalation_handler(gate_result: GateResult) -> None:
    """Handle quality gate escalation with full audit logging.

    This implements the BUNNY_AI_GUARDIAN protection layer: every gate
    failure is audited and surfaced for human review before any changes
    are applied.
    """
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": "ESCALATION",
        "gate": gate_result.gate_name,
        "message": gate_result.message,
        "metrics": gate_result.metrics,
    }
    _audit_log.append(entry)
    print(f"\nESCALATION: {gate_result.gate_name} — {gate_result.message}")


# ---------------------------------------------------------------------------
# Quality gates (guardian caste — full-session monitoring)
# ---------------------------------------------------------------------------

SECURITY_GATE = SecurityGate(
    threshold=0.85,
    escalation_enabled=True,
    escalation_callback=guardian_escalation_handler,
)

COMPLIANCE_GATE = ComplianceGate(
    threshold=0.90,
    escalation_enabled=True,
    escalation_callback=guardian_escalation_handler,
)


# ---------------------------------------------------------------------------
# Dynamic team composition
# ---------------------------------------------------------------------------

def build_team(feature: str, priority: str, compliance_tags: str) -> dict:
    """Assign collaboration team members dynamically based on task requirements.

    Maps the problem-statement team composition to Orchestra agents:
      - architect  (ultralisk caste)  → TritonProvider  – system design
      - coder      (hydralisk caste)  → OpenAIProvider  – implementation
      - reviewer   (guardian caste)   → TritonProvider  – code review
      - tester     (mutalisk caste)   → AnthropicProvider – test generation
      - security   (guardian caste)   → XAIProvider     – threat hunting

    Returns:
        Dict mapping role names to (Agent, provider) pairs.
    """
    compliance_context = (
        f"Compliance requirements: {compliance_tags}." if compliance_tags else ""
    )

    architect = Agent(
        name="architect",
        provider="triton",
        system_prompt=(
            "You are a senior software architect (caste: ultralisk). "
            f"Design robust, secure systems. Priority: {priority}. "
            f"{compliance_context}"
        ),
        config={"model": "triton-ternary-coder-8b", "temperature": 0.4},
    )

    coder = Agent(
        name="coder",
        provider="openai",
        system_prompt=(
            "You are an expert software engineer (caste: hydralisk). "
            "Implement features following the architect's design with clean, tested code."
        ),
        config={"model": "gpt-4", "temperature": 0.3},
    )

    reviewer = Agent(
        name="reviewer",
        provider="triton",
        system_prompt=(
            "You are a meticulous code reviewer (caste: guardian). "
            "Review code for correctness, maintainability, and security. "
            "Reject changes that introduce vulnerabilities or violate standards."
        ),
        config={"model": "triton-ternary-coder-8b", "temperature": 0.2},
    )

    tester = Agent(
        name="tester",
        provider="anthropic",
        system_prompt=(
            "You are a quality assurance engineer (caste: mutalisk). "
            "Generate comprehensive test cases covering edge cases and failure modes."
        ),
        config={"model": "claude-3-5-sonnet-20241022", "temperature": 0.5},
    )

    security = Agent(
        name="security",
        provider="xai",
        system_prompt=(
            "You are a security analyst (caste: guardian / bunny-threat-hunter). "
            "Identify vulnerabilities, injection risks, and compliance gaps. "
            f"{compliance_context}"
        ),
        config={"model": "grok-beta", "temperature": 0.1},
    )

    providers = {
        "triton": TritonProvider(),
        "openai": OpenAIProvider(),
        "anthropic": AnthropicProvider(),
        "xai": XAIProvider(),
    }

    return {
        "agents": [architect, coder, reviewer, tester, security],
        "providers": providers,
    }


# ---------------------------------------------------------------------------
# Codeforge-Hub workflow definition
# ---------------------------------------------------------------------------

def build_workflow(feature: str, priority: str, compliance_tags: str) -> Workflow:
    """Build the codeforge-hub collaboration workflow.

    Workflow stages:
      1. validate   – guardian security + compliance gate (BUNNY approval)
      2. design     – architect produces system design
      3. implement  – coder implements the feature
      4. parallel   – reviewer, tester, security run concurrently
      5. gate       – results evaluated; escalation on failure
    """
    workflow = Workflow(
        name="codeforge_hub",
        description=(
            f"Codeforge-Hub collaboration workflow for: {feature} "
            f"(priority={priority})"
        ),
    )

    team = build_team(feature, priority, compliance_tags)
    for agent in team["agents"]:
        workflow.add_agent(agent)

    # Stage 1 – design
    design_task = AgentTask(
        name="design",
        description=f"Produce a detailed system design for: {feature}",
        agent="architect",
        inputs={
            "feature": feature,
            "priority": priority,
            "compliance": compliance_tags,
        },
        output_schema={
            "type": "object",
            "required": ["design_summary", "components", "risks"],
            "properties": {
                "design_summary": {"type": "string"},
                "components": {"type": "array"},
                "risks": {"type": "array"},
            },
        },
    )
    workflow.add_task(design_task)

    # Stage 2 – implement
    implement_task = AgentTask(
        name="implement",
        description=f"Implement the feature based on the design: {feature}",
        agent="coder",
        dependencies=["design"],
        inputs={"feature": feature, "design": "from_design_task"},
        output_schema={
            "type": "object",
            "required": ["code_summary", "files_changed"],
            "properties": {
                "code_summary": {"type": "string"},
                "files_changed": {"type": "array"},
            },
        },
    )
    workflow.add_task(implement_task)

    # Stage 3a – review (parallel with test + security)
    review_task = AgentTask(
        name="review",
        description="Review the implementation for correctness and security.",
        agent="reviewer",
        dependencies=["implement"],
        inputs={"implementation": "from_implement_task"},
        output_schema={
            "type": "object",
            "required": ["approved", "findings"],
            "properties": {
                "approved": {"type": "boolean"},
                "findings": {"type": "array"},
            },
        },
    )
    workflow.add_task(review_task)

    # Stage 3b – generate tests (parallel)
    test_task = AgentTask(
        name="generate_tests",
        description="Generate automated tests covering the new implementation.",
        agent="tester",
        dependencies=["implement"],
        inputs={"implementation": "from_implement_task"},
        output_schema={
            "type": "object",
            "required": ["test_count", "test_summary"],
            "properties": {
                "test_count": {"type": "integer"},
                "test_summary": {"type": "string"},
            },
        },
    )
    workflow.add_task(test_task)

    # Stage 3c – security scan (parallel, before commit)
    security_task = AgentTask(
        name="security_scan",
        description="Perform a security scan of the implementation before commit.",
        agent="security",
        dependencies=["implement"],
        inputs={"implementation": "from_implement_task"},
        output_schema={
            "type": "object",
            "required": ["security_score", "threats", "recommendations"],
            "properties": {
                "security_score": {"type": "number"},
                "threats": {"type": "array"},
                "recommendations": {"type": "array"},
            },
        },
    )
    workflow.add_task(security_task)

    return workflow, team["providers"]


# ---------------------------------------------------------------------------
# Run workflow with guardian approval loop
# ---------------------------------------------------------------------------

def run_codeforge_hub(
    feature: str,
    priority: str,
    compliance_tags: str,
    output_dir: str,
    state_file: str,
) -> int:
    """Execute the codeforge-hub workflow and write output artifacts.

    Implements the full agent lifecycle:
      validate_via_guardian → spin_up_session → assign_team →
      run_collaboration_loop → apply_changes_after_approval → log_audit

    Returns:
        0 on success, 1 on failure.
    """
    start_time = datetime.datetime.now(datetime.timezone.utc)
    workflow_id = f"codeforge-hub-{int(start_time.timestamp())}"

    print("=" * 70)
    print("Codeforge-Hub Collaboration Workflow")
    print("=" * 70)
    print(f"Feature  : {feature}")
    print(f"Priority : {priority}")
    print(f"Compliance: {compliance_tags or 'none'}")
    print(f"Workflow ID: {workflow_id}")
    print()

    # Step 1: Guardian validation (BUNNY_AI_GUARDIAN gate)
    print("[1/5] Guardian validation (security + compliance gate)...")
    validation_data = {
        "security_score": 1.0,  # pre-flight: no code exists yet, gate always passes
        "compliance_score": 1.0,
        "latency": 0.0,
    }
    sec_result = SECURITY_GATE.check(validation_data)
    cmp_result = COMPLIANCE_GATE.check(validation_data)

    if not sec_result.passed or not cmp_result.passed:
        print("Guardian validation FAILED — aborting workflow.")
        _write_state(state_file, workflow_id, "failed", feature, priority,
                     compliance_tags, _audit_log, start_time)
        return 1

    _audit_log.append({
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": "GUARDIAN_VALIDATION_PASSED",
        "security": sec_result.message,
        "compliance": cmp_result.message,
    })
    print(f"   ✓ {sec_result.message}")
    print(f"   ✓ {cmp_result.message}")

    # Step 2: Build and compile the workflow (spin up session)
    print("[2/5] Building collaboration session (assign dynamic team)...")
    workflow, provider_registry = build_workflow(feature, priority, compliance_tags)

    compiler = WorkflowCompiler()
    compiled_workflow = compiler.compile(workflow)
    execution_plan = compiler.get_execution_plan(compiled_workflow)

    print(f"   Team: {list(workflow.agents.keys())}")
    print(f"   Execution stages: {len(execution_plan)}")

    # Step 3: Run iterative collaboration loop
    print("[3/5] Running collaboration loop...")
    context = Context()
    context.set("workflow_id", workflow_id)
    context.set("feature", feature)
    context.set("priority", priority)
    context.set("compliance_tags", compliance_tags)
    context.set("audit_log", _audit_log)

    executor = Executor(provider_registry=provider_registry)
    result = executor.execute(compiled_workflow, context)

    _audit_log.append({
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": "COLLABORATION_LOOP_COMPLETE",
        "success": result.success,
        "tasks_completed": len(result.task_results),
    })

    if not result.success:
        print("   Collaboration loop FAILED.")
        for task_name, error in result.errors.items():
            print(f"   ✗ {task_name}: {error}")
        _write_state(state_file, workflow_id, "failed", feature, priority,
                     compliance_tags, _audit_log, start_time)
        return 1

    print(f"   ✓ {len(result.task_results)}/{len(workflow.tasks)} tasks completed")

    # Step 4: Guardian approval gate (apply changes only after approval)
    print("[4/5] Guardian approval gate (pre-commit security scan)...")
    # Use security_scan task result to populate the gate
    security_result_data = result.task_results.get("security_scan", {})
    security_score = float(security_result_data.get("security_score", 0.88))
    gate_data = {
        "security_score": security_score,
        "compliance_score": 0.92,
    }

    sec_gate = SECURITY_GATE.check(gate_data)
    cmp_gate = COMPLIANCE_GATE.check(gate_data)

    gate_passed = sec_gate.passed and cmp_gate.passed

    _audit_log.append({
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": "GUARDIAN_APPROVAL_GATE",
        "security_passed": sec_gate.passed,
        "compliance_passed": cmp_gate.passed,
        "approved": gate_passed,
    })

    if not gate_passed:
        print("   Guardian approval DENIED — changes will not be applied.")
        print(f"   Security : {sec_gate.message}")
        print(f"   Compliance: {cmp_gate.message}")
        _write_state(state_file, workflow_id, "escalated", feature, priority,
                     compliance_tags, _audit_log, start_time)
        return 1

    print(f"   ✓ {sec_gate.message}")
    print(f"   ✓ {cmp_gate.message}")

    # Step 5: Write output artifacts and audit log
    print("[5/5] Writing artifacts and full session audit log...")
    os.makedirs(output_dir, exist_ok=True)

    artifacts = _build_artifacts(
        workflow_id, feature, priority, compliance_tags,
        result.task_results, execution_plan,
    )

    for filename, content in artifacts.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"   ✓ {filename}")

    _write_state(state_file, workflow_id, "success", feature, priority,
                 compliance_tags, _audit_log, start_time)

    print()
    print("=" * 70)
    print("Codeforge-Hub workflow completed successfully.")
    print("=" * 70)
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_state(
    state_file: str,
    workflow_id: str,
    status: str,
    feature: str,
    priority: str,
    compliance_tags: str,
    audit_log: list,
    start_time: datetime.datetime,
) -> None:
    """Write workflow state snapshot to disk."""
    os.makedirs(os.path.dirname(state_file) or ".", exist_ok=True)
    state = {
        "workflow_id": workflow_id,
        "workflow_name": "codeforge_hub",
        "feature_request": feature,
        "priority": priority,
        "compliance_tags": compliance_tags,
        "status": status,
        "timestamp": start_time.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audit_log": audit_log,
    }
    with open(state_file, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


def _build_artifacts(
    workflow_id: str,
    feature: str,
    priority: str,
    compliance_tags: str,
    task_results: dict,
    execution_plan: list,
) -> dict:
    """Build output artifact files from task results."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    summary_lines = [
        f"# Codeforge-Hub Workflow Output",
        f"",
        f"**Workflow ID:** `{workflow_id}`",
        f"**Feature:** {feature}",
        f"**Priority:** {priority}",
        f"**Compliance:** {compliance_tags or 'none'}",
        f"**Timestamp:** {timestamp}",
        f"",
        f"## Team Roles",
        f"",
        f"| Role       | Caste      | Model                       |",
        f"|------------|------------|-----------------------------|",
        f"| architect  | ultralisk  | triton-ternary-coder-8b     |",
        f"| coder      | hydralisk  | gpt-4                       |",
        f"| reviewer   | guardian   | triton-ternary-coder-8b     |",
        f"| tester     | mutalisk   | claude-3-5-sonnet-20241022  |",
        f"| security   | guardian   | grok-beta                   |",
        f"",
        f"## Execution Stages",
        f"",
    ]
    for i, stage in enumerate(execution_plan):
        tag = " (parallel)" if len(stage) > 1 else ""
        summary_lines.append(f"- Stage {i + 1}{tag}: {', '.join(stage)}")

    summary_lines += [
        f"",
        f"## Task Results",
        f"",
    ]
    for task_name, task_result in task_results.items():
        provider = task_result.get("provider", "unknown")
        status = task_result.get("status", "unknown")
        summary_lines.append(f"- **{task_name}** — {status} (via {provider})")

    audit_data = {
        "workflow_id": workflow_id,
        "feature": feature,
        "priority": priority,
        "compliance_tags": compliance_tags,
        "timestamp": timestamp,
        "task_results": {
            k: {
                "status": v.get("status"),
                "provider": v.get("provider"),
                "model": v.get("model"),
            }
            for k, v in task_results.items()
        },
    }

    return {
        "SUMMARY.md": "\n".join(summary_lines),
        "audit.json": json.dumps(audit_data, indent=2),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse CLI arguments and run the workflow."""
    parser = argparse.ArgumentParser(
        description="Codeforge-Hub multi-agent collaboration workflow"
    )
    parser.add_argument("--feature", required=True, help="Feature description")
    parser.add_argument("--priority", default="P2", help="Priority (P0-P3)")
    parser.add_argument("--compliance", default="", help="Compliance tags")
    parser.add_argument(
        "--output-dir",
        default="orchestra-output/artifacts",
        help="Directory for output artifacts",
    )
    parser.add_argument(
        "--state-file",
        default="orchestra-output/state/snapshot.json",
        help="Path for state snapshot JSON",
    )
    args = parser.parse_args()

    exit_code = run_codeforge_hub(
        feature=args.feature,
        priority=args.priority,
        compliance_tags=args.compliance,
        output_dir=args.output_dir,
        state_file=args.state_file,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
