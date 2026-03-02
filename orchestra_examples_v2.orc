# Orchestra DSL v2.0 - Example Workflows
# Demonstrating Advanced Features

## Example 1: Constitutional Tender Credit Analysis
## Shows: Routing, Conditionals, Error Handling

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


## Example 2: TILT Lead Generation
## Shows: Load Balancing, Dynamic Routing

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


## Example 3: DFIP Analytics Pipeline
## Shows: Pattern Matching, Error Recovery

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


## Example 4: Fraud Detection
## Shows: Guard Clauses, Validation, Retries

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


## Example 5: Dynamic Agent Selection
## Shows: Performance-Based Routing

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


## Example 6: Batch Processing with Resilience
## Shows: Batch Handling, Partial Failures

workflow batch_credit_analysis {
    version: "2.0"
    
    # Process multiple items
    for each item in input.batch {
        step analyze_item {
            agent: balance {
                strategy: round_robin
                pool: ["drone_1", "drone_2", "drone_3"]
                max_concurrent: 20
            }
            
            task: "Analyze credit for item ${item.id}"
            
            try {
                timeout {
                    hard: 10.0
                }
                
            } catch timeout_error {
                # Log and continue with others
                log: "Item ${item.id} timed out"
                mark_for_retry: item.id
                continue
                
            } catch any_error {
                # Log but don't fail entire batch
                log: "Item ${item.id} failed: ${error}"
                continue
            }
        }
    }
    
    # Handle items that need retry
    if marked_for_retry.count > 0 {
        step retry_failed {
            agent: guardian_claude
            for each item in marked_for_retry {
                task: "Retry analysis for ${item}"
            }
        }
    }
    
    # Batch summary
    finally {
        step summary {
            action: generate_batch_report
            data: {
                total_items: input.batch.count,
                successful: success_count,
                failed: failure_count,
                retried: retry_count,
                total_cost: batch_cost
            }
        }
    }
}
