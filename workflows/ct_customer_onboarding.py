"""
Constitutional Tender: Customer Onboarding Flow

Demonstrates Orchestra DSL for end-to-end customer onboarding
with KYC, compliance, and account provisioning.
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
    name="Constitutional Tender: Customer Onboarding",
    description="End-to-end customer onboarding with KYC, compliance, and account provisioning"
)

# Stage 1: Onboarding Flow Design (Claude)
flow_task = Task(
    name="Design Customer Onboarding Flow",
    agent=claude,
    prompt="""Design an end-to-end customer onboarding flow for a fintech platform:

Requirements:
- Multi-step application process
- Progressive data collection (minimize friction)
- KYC verification integration (Persona API)
- BSA/AML compliance screening
- Bank account linking (Plaid)
- Account provisioning and activation
- Welcome communications

Flow considerations:
- Mobile-first responsive design
- Save and resume capability
- Clear progress indicators
- Error recovery at each step
- Conditional steps based on risk tier
- Accessibility compliance (WCAG 2.1)
"""
)

# Stage 2: Integration Architecture (Claude)
integration_task = Task(
    name="Design Integration Architecture",
    agent=claude,
    dependencies=[flow_task],
    prompt="""Design the integration architecture for the onboarding flow:

Integrations to design:
- Persona API for identity verification
- Plaid API for bank account linking
- BSA/AML compliance engine
- Email/SMS notification service
- Account provisioning system
- CRM data synchronization

For each integration:
- API contract and data mapping
- Error handling and fallback behavior
- Retry policies and circuit breakers
- Webhook handling for async operations
- State machine for onboarding status tracking
"""
)

# Stage 3: Implementation (Copilot)
build_task = Task(
    name="Implement Customer Onboarding System",
    agent=copilot,
    dependencies=[integration_task],
    prompt="""Implement the customer onboarding system based on the design:

Generate:
- FastAPI endpoints for each onboarding step
- State machine for application status management
- Pydantic models for application data validation
- Integration clients (Persona, Plaid, notification service)
- Webhook handlers for async verification results
- Database models for applications and onboarding state
- Unit tests with pytest
"""
)

# Stage 4: Testing Strategy (Claude)
testing_task = Task(
    name="Design Onboarding Test Strategy",
    agent=claude,
    dependencies=[build_task],
    prompt="""Design a comprehensive testing strategy for the onboarding flow:

Test categories:
- Unit tests for each onboarding step
- Integration tests for third-party API interactions
- End-to-end flow tests (happy path and edge cases)
- Load testing scenarios for peak onboarding periods
- Security testing (input validation, data protection)
- Accessibility testing checklist

Include:
- Test data generation strategy
- Mock/stub definitions for external services
- Acceptance criteria per onboarding step
- Regression test suite definition
"""
)

# Add tasks and gates to workflow
workflow.add_tasks([flow_task, integration_task, build_task, testing_task])
workflow.add_gates([
    SecurityGate(threshold=95),
    ComplianceGate(threshold=98)
])

# Execute
if __name__ == "__main__":
    print("👤 Starting Constitutional Tender: Customer Onboarding Workflow\n")

    result = workflow.execute()

    print("\n✅ Workflow Complete!")
    print(f"Flow design: {len(result['flow_task'])} chars")
    print(f"Integration architecture: {len(result['integration_task'])} chars")
    print(f"Code generated: {len(result['build_task'])} chars")
    print(f"Test strategy: {len(result['testing_task'])} chars")
