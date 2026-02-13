"""
Constitutional Tender: Plaid Bank Verification Integration

Demonstrates Orchestra DSL for fintech feature development with
compliance gates and multi-agent orchestration.
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
    name="Constitutional Tender: Plaid Integration",
    description="Secure bank verification using Plaid API with BSA/AML compliance"
)

# Stage 1: Architecture Design (Claude)
design_task = Task(
    name="Design Plaid Integration Architecture",
    agent=claude,
    prompt="""Design the architecture for Plaid bank verification integration:

Requirements:
- Plaid Link token flow
- Secure credential storage
- Account verification process
- BSA/AML compliance requirements
- Error handling and retry logic

Deliverables:
- API endpoint specifications
- Database schema for storing verification data
- Security considerations
- Compliance checklist
"""
)

# Stage 2: Implementation (Copilot)
build_task = Task(
    name="Implement Plaid Integration",
    agent=copilot,
    dependencies=[design_task],
    prompt="""Implement the Plaid integration based on the architecture design:

Generate:
- FastAPI endpoints for Plaid Link flow
- Pydantic models for request/response validation
- Database models with SQLAlchemy
- Error handling middleware
- Unit tests with pytest
"""
)

# Add tasks to workflow
workflow.add_tasks([design_task, build_task])

# Execute
if __name__ == "__main__":
    print("🏦 Starting Constitutional Tender: Plaid Integration Workflow\n")

    result = workflow.execute()

    print("\n✅ Workflow Complete!")
    print(f"Design output: {len(result['design_task'])} chars")
    print(f"Code generated: {len(result['build_task'])} chars")
