"""
Constitutional Tender: BSA/AML Compliance Checks

Demonstrates Orchestra DSL for Bank Secrecy Act and Anti-Money Laundering
compliance automation with multi-agent orchestration.
"""

import os
from orchestra.core.workflow import Workflow
from orchestra.core.task import Task
from orchestra.providers.agents.anthropic import AnthropicProvider
from orchestra.providers.agents.openai import OpenAIProvider
from orchestra.core.gates import SecurityGate, ComplianceGate

# Initialize providers
claude = AnthropicProvider(api_key=os.getenv('ANTHROPIC_API_KEY'))
copilot = OpenAIProvider(api_key=os.getenv('OPENAI_API_KEY'))

# Create workflow
workflow = Workflow(
    name="Constitutional Tender: BSA/AML Compliance",
    description="Automated BSA/AML compliance checks with regulatory reporting"
)

# Stage 1: Compliance Framework Design (Claude)
framework_task = Task(
    name="Design BSA/AML Compliance Framework",
    agent=claude,
    prompt="""Design a BSA/AML compliance framework for a fintech platform:

Requirements:
- Currency Transaction Report (CTR) generation for transactions over $10,000
- Suspicious Activity Report (SAR) detection and filing
- Customer Due Diligence (CDD) integration
- Enhanced Due Diligence (EDD) triggers
- OFAC sanctions screening
- FinCEN reporting requirements
- Record retention policies (5-year minimum)

Deliverables:
- Compliance rule engine specification
- Alert threshold definitions
- Reporting templates (CTR, SAR)
- Audit trail requirements
- Escalation procedures
"""
)

# Stage 2: Detection Rules (Claude)
rules_task = Task(
    name="Define AML Detection Rules",
    agent=claude,
    dependencies=[framework_task],
    prompt="""Define AML detection rules based on the compliance framework:

Rules to define:
- Structuring detection (smurfing patterns)
- Unusual transaction velocity
- Geographic risk indicators
- Peer group analysis anomalies
- Layering pattern detection
- Round-dollar transaction patterns
- Rapid movement of funds
- Dormant account activity spikes

For each rule provide:
- Detection logic and thresholds
- Risk score contribution
- Alert priority level
- Required SAR criteria
"""
)

# Stage 3: Implementation (Copilot)
build_task = Task(
    name="Implement BSA/AML Compliance Engine",
    agent=copilot,
    dependencies=[rules_task],
    prompt="""Implement the BSA/AML compliance engine based on the framework and rules:

Generate:
- Transaction monitoring service with rule engine
- Alert management system with priority queuing
- CTR/SAR report generation endpoints
- OFAC screening integration
- Compliance dashboard API endpoints
- Database models for alerts, reports, and audit logs
- Unit tests with pytest
"""
)

# Add tasks and gates to workflow
workflow.add_tasks([framework_task, rules_task, build_task])
workflow.add_gates([
    SecurityGate(threshold=95),
    ComplianceGate(threshold=98)
])

# Execute
if __name__ == "__main__":
    print("🏛️  Starting Constitutional Tender: BSA/AML Compliance Workflow\n")

    result = workflow.execute()

    print("\n✅ Workflow Complete!")
    print(f"Framework design: {len(result['framework_task'])} chars")
    print(f"Detection rules: {len(result['rules_task'])} chars")
    print(f"Code generated: {len(result['build_task'])} chars")
