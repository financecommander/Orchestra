# Orchestra DSL v2.0 - Example 5
# Dynamic Agent Selection
# Shows: Performance-Based Routing

workflow adaptive_analysis {
    version: "2.0"

    # Select agent based on recent performance
    agent: select {
        metric: performance_history
        timeframe: last_24h
        optimize_for: [speed, cost, accuracy]
        weights: [0.2, 0.5, 0.3]

        candidates: [
            "drone_ultra_cheap",
            "hydra_financial",
            "ultra_reasoning",
            "guardian_sonnet"
        ]

        fallback: guardian_claude
    }

    budget {
        per_task: 0.015
        alert_at: 90.0
    }

    step analysis {
        task: "Adaptive analysis"

        timeout {
            soft: 10.0
            hard: 20.0

            on_soft_timeout {
                # Switch to faster agent mid-flight
                degrade_to: drone_fast
            }
        }
    }
}
