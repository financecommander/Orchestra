"""Triton Model Registry — client for discovering ternary models.

Connects to BUNNY's model registry to discover available Triton-compiled
ternary models. Supports local file-based registries for offline use and
remote HTTP registries for production.

The registry provides model metadata to the Orchestra LSP for autocomplete
and to the Blueprint Editor for model selection.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger("orchestra-triton-registry")


class CompressionProfile(Enum):
    """Compression profiles matching the Shapeshifter architecture."""
    PLANNER_SAFE = "planner_safe"
    SPECIALIST_BALANCED = "specialist_balanced"
    WORKER_FAST = "worker_fast"
    EDGE_EXTREME = "edge_extreme"


class ModelStatus(Enum):
    """Model deployment status."""
    AVAILABLE = "available"
    DEPLOYING = "deploying"
    DEPRECATED = "deprecated"
    UNAVAILABLE = "unavailable"


@dataclass
class TritonModel:
    """A Triton-compiled ternary model from the registry."""
    name: str
    version: str
    description: str = ""
    compression_profile: str = "worker_fast"
    quantization: str = "ternary"
    accuracy: float = 0.0
    latency_ms: float = 0.0
    model_size_mb: float = 0.0
    max_batch_size: int = 1
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    status: str = "available"
    endpoint: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_lsp_entry(self) -> dict[str, str]:
        """Convert to a dict suitable for LSP autocomplete."""
        return {
            "name": self.name,
            "description": self.description,
            "compression": self.compression_profile,
            "latency": f"{self.latency_ms}ms",
            "accuracy": f"{self.accuracy:.1%}" if self.accuracy else "N/A",
            "size": f"{self.model_size_mb}MB" if self.model_size_mb else "N/A",
        }

    @property
    def orc_reference(self) -> str:
        """Return the .orc agent reference string."""
        return f'triton_ternary("{self.name}")'

    def matches_profile(self, profile: CompressionProfile) -> bool:
        """Check if this model matches a compression profile."""
        return self.compression_profile == profile.value

    def matches_requirements(
        self,
        min_accuracy: float = 0.0,
        max_latency_ms: float = float("inf"),
        max_size_mb: float = float("inf"),
        required_tags: list[str] | None = None,
    ) -> bool:
        """Check if this model meets the given requirements."""
        if self.accuracy < min_accuracy:
            return False
        if self.latency_ms > max_latency_ms:
            return False
        if self.model_size_mb > max_size_mb:
            return False
        if required_tags:
            if not all(tag in self.tags for tag in required_tags):
                return False
        return True


class TritonModelRegistry:
    """Client for the Triton model registry.

    Supports multiple backends:
    - Local file-based registry (JSON files)
    - Remote HTTP registry (BUNNY API)
    - In-memory registry (for testing)
    """

    def __init__(
        self,
        registry_url: str | None = None,
        registry_path: str | None = None,
        cache_ttl: int = 300,
    ) -> None:
        self._registry_url = registry_url or os.environ.get(
            "TRITON_REGISTRY_URL",
            # Default: swarm-gpu internal IP (us-east1-b), Triton HTTP port
            "http://10.142.0.6:8000/v2/models",
        )
        self._registry_path = registry_path or os.environ.get("TRITON_REGISTRY_PATH")
        self._cache_ttl = cache_ttl
        self._models: dict[str, TritonModel] = {}
        self._cache_time: float = 0
        self._default_models_loaded = False

    # ── Model Management ─────────────────────────────────────────

    def register(self, model: TritonModel) -> None:
        """Register a model in the local registry."""
        self._models[model.name] = model
        logger.info(f"Registered model: {model.name} v{model.version}")

    def unregister(self, name: str) -> bool:
        """Remove a model from the local registry."""
        if name in self._models:
            del self._models[name]
            logger.info(f"Unregistered model: {name}")
            return True
        return False

    # ── Discovery ────────────────────────────────────────────────

    def discover(self, force_refresh: bool = False) -> list[TritonModel]:
        """Discover all available models from all configured sources."""
        if not force_refresh and self._is_cache_valid():
            return list(self._models.values())

        # Load from all sources
        if self._registry_path:
            self._load_from_file(self._registry_path)

        if self._registry_url:
            self._load_from_remote(self._registry_url)

        # Load built-in defaults if no models found
        if not self._models and not self._default_models_loaded:
            self._load_defaults()
            self._default_models_loaded = True

        self._cache_time = time.time()
        return list(self._models.values())

    def get(self, name: str) -> TritonModel | None:
        """Get a specific model by name."""
        if not self._models:
            self.discover()
        return self._models.get(name)

    def search(
        self,
        query: str = "",
        profile: CompressionProfile | None = None,
        tags: list[str] | None = None,
        min_accuracy: float = 0.0,
        max_latency_ms: float = float("inf"),
        status: str = "available",
    ) -> list[TritonModel]:
        """Search for models matching criteria."""
        if not self._models:
            self.discover()

        results = []
        query_lower = query.lower()

        for model in self._models.values():
            if status and model.status != status:
                continue
            if profile and not model.matches_profile(profile):
                continue
            if query_lower and query_lower not in model.name.lower() and query_lower not in model.description.lower():
                continue
            if not model.matches_requirements(min_accuracy=min_accuracy, max_latency_ms=max_latency_ms, required_tags=tags):
                continue
            results.append(model)

        return results

    def recommend_for_task(
        self,
        task_class: str,
        domain: str = "",
    ) -> list[TritonModel]:
        """Recommend models based on task classification.

        Task classes from the Shapeshifter architecture:
        - compress: formatting, tests, lint fixes → worker_fast / edge_extreme
        - balance: bug fixes, repo review → specialist_balanced
        - preserve: architecture changes → planner_safe
        """
        profile_map = {
            "compress": [CompressionProfile.WORKER_FAST, CompressionProfile.EDGE_EXTREME],
            "balance": [CompressionProfile.SPECIALIST_BALANCED],
            "preserve": [CompressionProfile.PLANNER_SAFE],
        }

        profiles = profile_map.get(task_class.lower(), [CompressionProfile.SPECIALIST_BALANCED])
        results = []

        for profile in profiles:
            results.extend(self.search(profile=profile, query=domain))

        # Sort by accuracy (descending) then latency (ascending)
        results.sort(key=lambda m: (-m.accuracy, m.latency_ms))
        return results

    # ── LSP Integration ──────────────────────────────────────────

    def get_lsp_entries(self) -> list[dict[str, str]]:
        """Get all models formatted for LSP autocomplete."""
        if not self._models:
            self.discover()
        return [m.to_lsp_entry() for m in self._models.values() if m.status == "available"]

    # ── Export / Import ──────────────────────────────────────────

    def export_registry(self, path: str) -> None:
        """Export the registry to a JSON file."""
        data = {
            "version": "1.0",
            "models": [m.to_dict() for m in self._models.values()],
        }
        Path(path).write_text(json.dumps(data, indent=2))
        logger.info(f"Exported {len(self._models)} models to {path}")

    def import_registry(self, path: str) -> int:
        """Import models from a JSON file. Returns count of models imported."""
        return self._load_from_file(path)

    # ── Private Methods ──────────────────────────────────────────

    def _is_cache_valid(self) -> bool:
        return bool(self._models) and (time.time() - self._cache_time) < self._cache_ttl

    def _load_from_file(self, path: str) -> int:
        """Load models from a local JSON registry file."""
        try:
            data = json.loads(Path(path).read_text())
            models = data.get("models", [])
            count = 0
            for entry in models:
                model = TritonModel(**{k: v for k, v in entry.items() if k in TritonModel.__dataclass_fields__})
                self._models[model.name] = model
                count += 1
            logger.info(f"Loaded {count} models from {path}")
            return count
        except FileNotFoundError:
            logger.warning(f"Registry file not found: {path}")
            return 0
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error loading registry from {path}: {e}")
            return 0

    def _load_from_remote(self, url: str) -> int:
        """Load models from a remote HTTP registry."""
        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            models = data.get("models", [])
            count = 0
            for entry in models:
                model = TritonModel(**{k: v for k, v in entry.items() if k in TritonModel.__dataclass_fields__})
                self._models[model.name] = model
                count += 1
            logger.info(f"Loaded {count} models from {url}")
            return count
        except (URLError, OSError) as e:
            logger.warning(f"Cannot reach remote registry at {url}: {e}")
            return 0
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error parsing remote registry response: {e}")
            return 0

    def _load_defaults(self) -> None:
        """Load built-in default Triton ternary models."""
        defaults = [
            TritonModel(
                name="credit-risk-v4",
                version="4.0.0",
                description="Credit risk assessment model for financial applications",
                compression_profile="specialist_balanced",
                quantization="4-bit mixed",
                accuracy=0.96,
                latency_ms=12.5,
                model_size_mb=245.0,
                tags=["finance", "risk", "credit"],
                status="available",
            ),
            TritonModel(
                name="fraud-detection-v3",
                version="3.2.1",
                description="Real-time fraud detection for transaction monitoring",
                compression_profile="worker_fast",
                quantization="ternary",
                accuracy=0.94,
                latency_ms=3.2,
                model_size_mb=48.0,
                tags=["finance", "fraud", "security"],
                status="available",
            ),
            TritonModel(
                name="document-classifier-v2",
                version="2.1.0",
                description="Multi-class document classification and routing",
                compression_profile="worker_fast",
                quantization="ternary",
                accuracy=0.92,
                latency_ms=5.1,
                model_size_mb=62.0,
                tags=["nlp", "classification"],
                status="available",
            ),
            TritonModel(
                name="sentiment-analyzer-v3",
                version="3.0.0",
                description="Financial sentiment analysis for market signals",
                compression_profile="specialist_balanced",
                quantization="4-bit",
                accuracy=0.95,
                latency_ms=8.3,
                model_size_mb=128.0,
                tags=["finance", "nlp", "sentiment"],
                status="available",
            ),
            TritonModel(
                name="code-reviewer-v2",
                version="2.0.0",
                description="Automated code review with security analysis",
                compression_profile="planner_safe",
                quantization="mixed precision",
                accuracy=0.98,
                latency_ms=45.0,
                model_size_mb=890.0,
                tags=["code", "review", "security"],
                status="available",
            ),
            TritonModel(
                name="lead-enrichment-v3",
                version="3.1.0",
                description="Contact data enrichment and intent signal extraction",
                compression_profile="worker_fast",
                quantization="ternary",
                accuracy=0.91,
                latency_ms=4.8,
                model_size_mb=55.0,
                tags=["marketing", "enrichment"],
                status="available",
            ),
            TritonModel(
                name="intent-scoring-v2",
                version="2.3.0",
                description="Purchase intent scoring from behavioral signals",
                compression_profile="worker_fast",
                quantization="ternary",
                accuracy=0.89,
                latency_ms=3.5,
                model_size_mb=42.0,
                tags=["marketing", "scoring"],
                status="available",
            ),
            TritonModel(
                name="opportunity-analyzer-v1",
                version="1.2.0",
                description="Deep opportunity analysis with firmographic context",
                compression_profile="specialist_balanced",
                quantization="4-bit mixed",
                accuracy=0.93,
                latency_ms=22.0,
                model_size_mb=340.0,
                tags=["marketing", "analysis", "opportunity"],
                status="available",
            ),
            TritonModel(
                name="compliance-checker-v2",
                version="2.0.0",
                description="Regulatory compliance validation for financial workflows",
                compression_profile="planner_safe",
                quantization="mixed precision",
                accuracy=0.99,
                latency_ms=38.0,
                model_size_mb=720.0,
                tags=["compliance", "regulation", "finance"],
                status="available",
            ),
            TritonModel(
                name="edge-classifier-v1",
                version="1.0.0",
                description="Lightweight classifier for edge deployment",
                compression_profile="edge_extreme",
                quantization="ternary",
                accuracy=0.85,
                latency_ms=1.2,
                model_size_mb=8.0,
                max_batch_size=32,
                tags=["edge", "classification"],
                status="available",
            ),
            TritonModel(
                name="summarizer-v2",
                version="2.1.0",
                description="Text summarization for documents and reports",
                compression_profile="specialist_balanced",
                quantization="4-bit",
                accuracy=0.94,
                latency_ms=15.0,
                model_size_mb=210.0,
                tags=["nlp", "summarization"],
                status="available",
            ),
            TritonModel(
                name="entity-extractor-v3",
                version="3.0.0",
                description="Named entity recognition for financial documents",
                compression_profile="worker_fast",
                quantization="ternary",
                accuracy=0.93,
                latency_ms=4.0,
                model_size_mb=52.0,
                tags=["nlp", "ner", "finance"],
                status="available",
            ),
        ]

        for model in defaults:
            self._models[model.name] = model

        logger.info(f"Loaded {len(defaults)} default Triton models")
