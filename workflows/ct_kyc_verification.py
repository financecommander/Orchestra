"""
Constitutional Tender: KYC Verification with Persona API

Demonstrates Orchestra DSL for identity verification workflows
using Persona API with multi-agent orchestration.
"""

import os
from orchestra.core.workflow import Workflow
from orchestra.core.task import Task
from orchestra.providers.agents.anthropic import AnthropicProvider
from orchestra.providers.agents.openai import OpenAIProvider

# Initialize providers
claude = AnthropicProvider(api_key=os.getenv('ANTHROPIC_API_KEY'))
copilot = OpenAIProvider(api_key=os.getenv('OPENAI_API_KEY'))

# Create workflow
workflow = Workflow(
    name="Constitutional Tender: KYC Verification",
    description="Identity verification using Persona API with regulatory compliance"
)

# Stage 1: KYC Requirements Analysis (Claude)
requirements_task = Task(
    name="Analyze KYC Requirements",
    agent=claude,
    prompt="""Analyze KYC verification requirements for a fintech platform:

Requirements:
- Persona API integration for identity verification
- Document verification (government ID, proof of address)
- Biometric verification (selfie matching)
- PEP (Politically Exposed Persons) screening
- Sanctions list checking
- Risk scoring methodology

Deliverables:
- KYC verification flow diagram
- Data collection requirements per risk tier
- Persona API endpoint mapping
- Regulatory requirements by jurisdiction (US, EU, UK)
"""
)

# Stage 2: Verification Logic Design (Claude)
design_task = Task(
    name="Design KYC Verification Logic",
    agent=claude,
    dependencies=[requirements_task],
    prompt="""Design the KYC verification logic based on the requirements analysis:

Design:
- Risk-tiered verification levels (Basic, Enhanced, Full)
- Decision engine rules for auto-approval vs manual review
- Document validation pipeline
- Identity matching confidence thresholds
- Retry and escalation policies
- Data retention and privacy policies (GDPR, CCPA)
"""
)

# Stage 3: Implementation (Copilot)
build_task = Task(
    name="Implement KYC Verification System",
    agent=copilot,
    dependencies=[design_task],
    prompt="""Implement the KYC verification system based on the design:

Generate:
- FastAPI endpoints for KYC submission and status tracking
- Persona API client wrapper with webhook handling
- Pydantic models for verification requests and responses
- Risk scoring engine
- Database models for verification records
- Unit tests with pytest
"""
)

# Add tasks to workflow
workflow.add_tasks([requirements_task, design_task, build_task])

# Execute
if __name__ == "__main__":
    print("🔐 Starting Constitutional Tender: KYC Verification Workflow\n")

    result = workflow.execute()

    print("\n✅ Workflow Complete!")
    print(f"Requirements analysis: {len(result['requirements_task'])} chars")
    print(f"Design output: {len(result['design_task'])} chars")
    print(f"Code generated: {len(result['build_task'])} chars")
