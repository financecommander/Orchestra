"""
Constitutional Tender: Real-Time Transaction Monitoring

Demonstrates Orchestra DSL for real-time transaction monitoring
with fraud detection and compliance alerting.
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
    name="Constitutional Tender: Transaction Monitoring",
    description="Real-time transaction monitoring with fraud detection and compliance alerting"
)

# Stage 1: Monitoring Architecture (Claude)
architecture_task = Task(
    name="Design Transaction Monitoring Architecture",
    agent=claude,
    prompt="""Design a real-time transaction monitoring system architecture:

Requirements:
- Sub-second transaction screening
- Event-driven architecture for scalability
- Multi-channel monitoring (ACH, wire, card, P2P)
- Real-time risk scoring per transaction
- Integration with BSA/AML compliance engine
- Fraud pattern detection

Architecture considerations:
- Stream processing (Kafka/event streams)
- In-memory rule evaluation
- Historical pattern analysis
- Machine learning model integration points
- Alert routing and prioritization
- System throughput and latency targets
"""
)

# Stage 2: Detection Models (Claude)
models_task = Task(
    name="Design Detection Models",
    agent=claude,
    dependencies=[architecture_task],
    prompt="""Design fraud and anomaly detection models for transaction monitoring:

Models to design:
- Velocity checks (count and amount thresholds by time window)
- Geographic anomaly detection (impossible travel, high-risk jurisdictions)
- Behavioral profiling (deviation from customer baseline)
- Network analysis (related party transaction patterns)
- Amount anomaly detection (statistical outlier identification)
- Channel-switching patterns
- Time-of-day risk adjustments

For each model provide:
- Input features and data sources
- Scoring methodology
- Threshold calibration approach
- False positive mitigation strategy
"""
)

# Stage 3: Implementation (Copilot)
build_task = Task(
    name="Implement Transaction Monitoring System",
    agent=copilot,
    dependencies=[models_task],
    prompt="""Implement the real-time transaction monitoring system:

Generate:
- Transaction ingestion API with validation
- Stream processing pipeline for real-time evaluation
- Rule engine with configurable thresholds
- Risk scoring aggregation service
- Alert generation and routing system
- Monitoring dashboard API endpoints
- Database models for transactions, alerts, and risk scores
- Unit tests with pytest
"""
)

# Add tasks and gates to workflow
workflow.add_tasks([architecture_task, models_task, build_task])
workflow.add_gates([
    SecurityGate(threshold=95),
    ComplianceGate(threshold=98)
])

# Execute
if __name__ == "__main__":
    print("📊 Starting Constitutional Tender: Transaction Monitoring Workflow\n")

    result = workflow.execute()

    print("\n✅ Workflow Complete!")
    print(f"Architecture design: {len(result['architecture_task'])} chars")
    print(f"Detection models: {len(result['models_task'])} chars")
    print(f"Code generated: {len(result['build_task'])} chars")
