# Orchestra DSL v2.0 - Example 1
# Constitutional Tender Credit Analysis
# Shows: Routing, Conditionals, Error Handling

workflow constitutional_tender_credit {
    version: "2.0"
    owner: "Constitutional Tender"

    # Input validation
    guard {
        require: input.borrower_id != null
        require: input.loan_amount > 0
        require: input.loan_amount <= 5000000
        on_violation: reject("Invalid loan parameters")
    }

    # Budget protection
    budget {
        per_task: 0.02
        hourly_limit: 500.0
        alert_at: 80.0
    }

    # Circuit breaker for API protection
    circuit_breaker {
        failure_threshold: 10
        timeout: 120.0
        half_open_after: 30.0
        on_open: alert("ops_team")
    }

    # Conditional routing based on loan amount
    if input.loan_amount > 1000000 {
        # High-value loans: Premium analysis with retries
        step high_value {
            try {
                agent: guardian_claude
                model: "claude-opus-4.5"
                task: "Comprehensive credit analysis"

                timeout {
                    soft: 15.0
                    hard: 30.0
                    on_soft_timeout: log("Analysis running slow")
                    on_hard_timeout: {
                        fallback: guardian_sonnet
                        alert: "Timeout on premium analysis"
                    }
                }

                validate_output {
                    assert: result.risk_tier in ["A", "B", "C", "D"]
                    assert: result.confidence > 0.85
                    assert: result.recommendation != null

                    on_validation_failure: {
                        log: "Output validation failed"
                        retry(max: 2)
                    }
                }

            } retry {
                strategy: exponential_backoff
                max_attempts: 3
                initial_delay: 2.0
                max_delay: 10.0

            } catch timeout_error {
                # Degrade to faster analysis
                agent: ultra_reasoning
                model: "deepseek-r1"
                alert: "Degraded to fallback agent"

            } catch any_error {
                # Final fallback
                agent: hydra_financial
                alert: "Using emergency fallback"
            }
        }

        # Parallel compliance checks for high-value
        parallel {
            step fraud_analysis {
                agent: ultra_reasoning
                task: "Deep fraud pattern analysis"
                timeout: 20.0
            }

            step regulatory_check {
                agent: hydra_compliance
                task: "Verify regulatory compliance"
                timeout: 15.0
            }

            step credit_bureau {
                agent: drone_fast
                task: "Credit bureau verification"
                timeout: 10.0
            }
        }

        on_partial_failure {
            strategy: continue
            min_success_rate: 0.66
            on_below_threshold: {
                alert: "Too many parallel failures"
                abort_workflow
            }
        }

    } else if input.loan_amount > 100000 {
        # Medium loans: Balanced analysis
        step medium_value {
            agent: route {
                if input.credit_score > 750 then hydra_financial
                if input.credit_score > 650 then ultra_reasoning
                else guardian_sonnet
            }

            task: "Standard credit analysis"

            timeout {
                hard: 15.0
                on_timeout: {
                    degrade_to: hydra_financial
                }
            }
        }

    } else {
        # Small loans: Fast & cheap
        step small_value {
            # Cascade through cheaper agents first
            agent: cascade [
                try: drone_ultra_cheap,
                fallback: hydra_financial,
                last_resort: ultra_reasoning
            ]

            task: "Quick credit check"

            timeout {
                hard: 5.0
                on_timeout: {
                    # Use cached result if available
                    return: cached_or_default
                }
            }
        }
    }

    # Final quality gate
    quality_gate {
        metrics: {
            accuracy: 0.95,
            completeness: 0.90,
            consistency: 0.85
        }

        on_failure {
            step manual_review {
                agent: guardian_claude
                task: "Manual review - quality gate failed"
                notify: compliance_team
                priority: high
            }
        }
    }

    # Always executed
    finally {
        step metrics {
            action: log_performance_data
            data: {
                workflow_duration,
                total_cost,
                agents_used,
                quality_score
            }
        }
    }
}
