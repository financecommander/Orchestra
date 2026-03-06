"""Triton Model Registry Integration.

Provides auto-discovery and dynamic selection of Triton-compiled
ternary models from BUNNY's model registry. Enables:

- Registry client for discovering available models
- Model metadata (compression profile, accuracy, latency, size)
- Dynamic model suggestions for .orc autocomplete
- Compression profile matching for task requirements
- Integration with the Orchestra LSP and Blueprint Editor
"""

from orchestra.triton_registry.registry import TritonModelRegistry, TritonModel

__all__ = ["TritonModelRegistry", "TritonModel"]
