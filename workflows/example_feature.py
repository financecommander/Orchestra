"""
Example Orchestra Workflow: Feature Development

This example demonstrates how to define agents, workflow stages,
quality gates, and execute an Orchestra workflow for a typical
feature development process.
"""

# ---------------------------------------------------------------------------
# Agent Definitions
# ---------------------------------------------------------------------------
# Agents represent specialized roles in the workflow. Each agent has a name,
# a model provider, and a description of its responsibilities.

agents = {
    "architect": {
        "model": "anthropic/claude-sonnet",
        "role": "Design technical architecture and define implementation plans.",
    },
    "developer": {
        "model": "anthropic/claude-sonnet",
        "role": "Implement code changes based on the architecture plan.",
    },
    "reviewer": {
        "model": "openai/gpt-4",
        "role": "Review code for correctness, style, and best practices.",
    },
    "tester": {
        "model": "anthropic/claude-sonnet",
        "role": "Write and run tests to verify the implementation.",
    },
}

# ---------------------------------------------------------------------------
# Workflow Stages
# ---------------------------------------------------------------------------
# Stages define the ordered sequence of work. Each stage specifies which agent
# handles it, what the expected input/output is, and any dependencies.

stages = [
    {
        "name": "design",
        "agent": "architect",
        "description": "Produce a technical design document for the feature.",
        "inputs": ["feature_request"],
        "outputs": ["design_document"],
    },
    {
        "name": "implement",
        "agent": "developer",
        "description": "Write the code that implements the design.",
        "inputs": ["design_document"],
        "outputs": ["source_code"],
        "depends_on": ["design"],
    },
    {
        "name": "review",
        "agent": "reviewer",
        "description": "Review the implementation for quality and correctness.",
        "inputs": ["source_code", "design_document"],
        "outputs": ["review_feedback"],
        "depends_on": ["implement"],
    },
    {
        "name": "test",
        "agent": "tester",
        "description": "Create and execute tests for the implementation.",
        "inputs": ["source_code", "design_document"],
        "outputs": ["test_results"],
        "depends_on": ["review"],
    },
]

# ---------------------------------------------------------------------------
# Quality Gates
# ---------------------------------------------------------------------------
# Quality gates are checkpoints that must pass before the workflow can proceed
# to the next stage or be considered complete.

quality_gates = [
    {
        "name": "design_approval",
        "after_stage": "design",
        "criteria": "Design document covers all requirements and edge cases.",
    },
    {
        "name": "code_review_pass",
        "after_stage": "review",
        "criteria": "No critical issues found; all comments resolved.",
    },
    {
        "name": "tests_pass",
        "after_stage": "test",
        "criteria": "All tests pass with >= 80% code coverage.",
    },
]

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
# In a real Orchestra environment, the workflow engine reads the definitions
# above and orchestrates the agents through each stage, enforcing quality
# gates between transitions.

if __name__ == "__main__":
    print("Orchestra Example Workflow")
    print("=" * 40)

    print("\nAgents:")
    for name, config in agents.items():
        print(f"  - {name}: {config['role']}")

    print("\nStages:")
    for stage in stages:
        deps = ", ".join(stage.get("depends_on", [])) or "none"
        print(f"  {stage['name']} (agent: {stage['agent']}, depends_on: {deps})")

    print("\nQuality Gates:")
    for gate in quality_gates:
        print(f"  - {gate['name']} (after: {gate['after_stage']})")
        print(f"    Criteria: {gate['criteria']}")

    print("\nWorkflow ready for execution.")
