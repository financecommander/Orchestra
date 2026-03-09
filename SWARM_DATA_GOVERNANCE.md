# Swarm Data Governance — Orchestra

**Calculus Ecosystem • Governance Rule 4 Compliance**

## Rule

> **super-duper-spork retains ALL swarm management data.**
>
> External repos that generate, test, or benchmark swarm algorithms
> must push assessment results back to `financecommander/super-duper-spork`.

## This Repo's Obligations

Orchestra defines workflow DSL (.orc files) that reference swarm task
routing and algorithm dispatch. When workflow execution produces swarm
performance data or algorithm selection metrics, those must be reported.

| Obligation | Target | Format |
|-----------|--------|--------|
| Push workflow-level swarm routing metrics | `super-duper-spork/swarm/assessments/` | `orchestra_{description}_{YYYY-MM-DD}.md` |

## Canonical Source of Truth

The single source of truth for all swarm state is:

    financecommander/super-duper-spork

This repo defines workflows. super-duper-spork retains all swarm
management data, assessment results, and cross-repo totals.

---
*Governance Rule 4 — established 2026-03-09*
