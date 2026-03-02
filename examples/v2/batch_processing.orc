# Orchestra DSL v2.0 - Example 6
# Batch Processing with Resilience
# Shows: Batch Handling, Partial Failures

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
