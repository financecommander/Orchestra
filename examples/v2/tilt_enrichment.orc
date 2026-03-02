# Orchestra DSL v2.0 - Example 2
# TILT Lead Generation
# Shows: Load Balancing, Dynamic Routing

workflow tilt_lead_enrichment {
    version: "2.0"
    owner: "TILT"

    # High-volume workflow needs load balancing
    agent: balance {
        strategy: least_loaded
        pool: [
            "drone_1",
            "drone_2",
            "drone_3",
            "drone_4"
        ]
        max_concurrent: 50
    }

    budget {
        per_task: 0.005
        hourly_limit: 200.0
    }

    # Parallel data enrichment
    parallel {
        step property_data {
            agent: drone_cheap
            task: "Gather property information"
            timeout: 10.0
        }

        step owner_data {
            agent: drone_cheap
            task: "Identify property owner"
            timeout: 10.0
        }

        step market_data {
            agent: hydra_financial
            task: "Analyze market conditions"
            timeout: 15.0
        }

        step comparable_sales {
            agent: drone_fast
            task: "Find comparable sales"
            timeout: 10.0
        }
    }

    on_partial_failure {
        strategy: continue
        min_success_rate: 0.75
    }

    # Conditional deep analysis
    if enriched_data.equity_estimate > 100000 {
        step deep_analysis {
            agent: ultra_reasoning
            task: "Deep opportunity analysis"
        }
    }

    # Quality scoring
    step score {
        agent: cheapest_above(quality_threshold: 0.85)
        task: "Score lead quality"

        validate_output {
            assert: result.score >= 0
            assert: result.score <= 100
        }
    }
}
