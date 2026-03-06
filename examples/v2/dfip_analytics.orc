# Orchestra DSL v2.0 - Example 3
# DFIP Analytics Pipeline
# Shows: Pattern Matching, Error Recovery

workflow dfip_analytics {
    version: "2.0"
    owner: "DFIP"

    # Route based on data source
    match input.source_type {
        case "real_time_market" => {
            agent: drone_fast
            model: "llama-4-maverick"
            latency_priority: high
        }

        case "regulatory_filing" => {
            agent: hydra_compliance
            model: "gemini-2.5-flash"
            accuracy_priority: high
        }

        case "earnings_report" => {
            agent: ultra_reasoning
            model: "deepseek-r1"
            depth_priority: high
        }

        case "social_sentiment" => {
            agent: drone_ultra_cheap
            model: "gemini-1.5-flash"
            cost_priority: high
        }

        default => {
            agent: hydra_financial
            model: "gemini-2.5-flash"
        }
    }

    try {
        step analysis {
            task: "Analyze financial data"

            timeout {
                soft: 30.0
                hard: 60.0
            }
        }

    } on_error {
        # Comprehensive error handling
        capture: {
            error_type,
            error_message,
            stack_trace,
            input_data,
            timestamp,
            attempted_agent
        }

        log {
            level: error
            message: "Analysis failed"
            context: captured_data
            alert: data_team
        }

        # Attempt recovery with different agent
        step recovery {
            agent: guardian_claude
            task: "Recover analysis from error"
            context: captured_data
        }

    } finally {
        # Always clean up
        step cleanup {
            action: release_resources
            action: update_metrics
        }
    }
}
