# Triton Runtime Contract — Phase 37 Update

**Source**: [`financecommander/Triton@b0ef84f`](https://github.com/financecommander/Triton/commit/b0ef84f)
**Date**: 2026-03-09

---

## Dual Backend Architecture

The Triton inference runtime now supports **two concurrent backends** on swarm-gpu (35.227.111.161):

| Backend | Port | Engine | Tiers | Best For |
|---------|------|--------|-------|----------|
| **Rust triton-rs** | 8081 | candle + CUDA PTX | 15/15 | Brain tiers, cold-start, low-VRAM |
| **NVIDIA Triton** | 8000 | PyTorch + torch.compile | 12/15 | Batch throughput, sustained concurrency |

### Routing Recommendation for Orchestra Workflows

```
workflow inference_routing {
    if task.tier in [brain_a, brain_b, brain_c] {
        # Only Rust serves brain tiers
        endpoint: "http://35.227.111.161:8081/v1/models/{tier}/generate"
    } else if task.concurrency > 8 {
        # NVIDIA Triton wins at high concurrency (490 RPS)
        endpoint: "http://35.227.111.161:8000/v2/models/{tier}/infer"
    } else {
        # Rust for single/low-concurrency (502 tok/s, 8x less VRAM)
        endpoint: "http://35.227.111.161:8081/v1/models/{tier}/generate"
    }
}
```

### A/B Benchmark Summary

| Metric | Rust triton-rs | NVIDIA Triton |
|--------|---------------|---------------|
| Tiers working | 15/15 | 12/15 |
| Single-stream | 502 tok/s | N/A |
| Concurrent RPS | 12.5 | 490 |
| Cold-start | 5.8x faster | — |
| VRAM | 1.5 GB | 11.8 GB |

### 15-Tier Model Ladder (All LIVE)

cell_pico, cell, dot, ultra_micro, micro, tiny, small, medium, large, extra_large, deep_narrow, wide_deep, gqa, ffn_heavy, brain_a

### Changes Since Phase 36

- Rust CUDA backend built with cudarc 0.13
- Tensor contiguity fixes for GQA attention
- Custom softmax for CUDA compatibility
- All 15 tiers validated on NVIDIA L4 24GB
- Full A/B benchmark report committed

### Full Report

See [`Triton/benchmarks/AB_REPORT.md`](https://github.com/financecommander/Triton/blob/main/benchmarks/AB_REPORT.md).
