# Orchestra DSL v2.0 - Example 4
# Fraud Detection
# Shows: Guard Clauses, Validation, Retries

workflow fraud_detection {
    version: "2.0"
    owner: "Constitutional Tender"
    criticality: critical

    # Strict input validation
    guard {
        require: input.transaction_id != null
        require: input.amount > 0
        require: input.timestamp != null
        require: input.merchant_id != null
        on_violation: reject_and_alert("Invalid transaction data")
    }

    # Circuit breaker for external API
    circuit_breaker {
        failure_threshold: 5
        timeout: 30.0
        half_open_after: 15.0
        on_open: {
            fallback: cached_fraud_model
            alert: security_team
        }
    }

    # Multi-stage fraud analysis
    step quick_check {
        agent: drone_ultra_cheap
        task: "Quick fraud indicators check"

        timeout {
            hard: 2.0
            on_timeout: skip_to_deep_analysis
        }
    }

    # Conditional deep analysis
    if quick_check.risk_score > 0.3 {
        step deep_analysis {
            try {
                agent: ultra_reasoning
                model: "deepseek-r1"
                task: "Deep fraud pattern analysis"

                validate_output {
                    assert: result.fraud_probability >= 0.0
                    assert: result.fraud_probability <= 1.0
                    assert: result.factors != null
                    assert: len(result.factors) > 0
                }

            } retry {
                strategy: exponential_backoff
                max_attempts: 3
                initial_delay: 1.0

            } catch validation_error {
                # Use conservative default
                return: {
                    fraud_probability: 0.9,
                    recommendation: "manual_review"
                }
            }
        }

        # Parallel verification
        parallel {
            step behavioral_analysis {
                agent: ultra_reasoning
                task: "Analyze transaction behavior"
            }

            step network_analysis {
                agent: hydra_financial
                task: "Check transaction network"
            }

            step historical_comparison {
                agent: drone_fast
                task: "Compare to user history"
            }
        }
    }

    # Final decision with quality gate
    quality_gate {
        metrics: {
            confidence: 0.90,
            completeness: 0.95
        }

        on_failure {
            # Too risky to proceed
            action: manual_review_required
            alert: fraud_team
            priority: urgent
        }
    }
}
