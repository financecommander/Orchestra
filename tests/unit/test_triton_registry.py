"""Tests for the Triton Model Registry."""

import json
import tempfile
import os

import pytest

from orchestra.triton_registry.registry import (
    CompressionProfile,
    ModelStatus,
    TritonModel,
    TritonModelRegistry,
)


# =====================================================================
# TritonModel TESTS
# =====================================================================

class TestTritonModel:
    """Tests for the TritonModel dataclass."""

    def test_basic_creation(self):
        model = TritonModel(name="test-model", version="1.0.0")
        assert model.name == "test-model"
        assert model.version == "1.0.0"
        assert model.compression_profile == "worker_fast"
        assert model.status == "available"

    def test_to_dict(self):
        model = TritonModel(name="m", version="1.0", accuracy=0.95)
        d = model.to_dict()
        assert d["name"] == "m"
        assert d["accuracy"] == 0.95

    def test_to_lsp_entry(self):
        model = TritonModel(
            name="fraud-v1",
            version="1.0",
            description="Fraud detector",
            compression_profile="worker_fast",
            accuracy=0.94,
            latency_ms=3.0,
            model_size_mb=50.0,
        )
        entry = model.to_lsp_entry()
        assert entry["name"] == "fraud-v1"
        assert "94" in entry["accuracy"]
        assert "3.0ms" == entry["latency"]
        assert "50.0MB" == entry["size"]

    def test_orc_reference(self):
        model = TritonModel(name="credit-risk-v4", version="4.0")
        assert model.orc_reference == 'triton_ternary("credit-risk-v4")'

    def test_matches_profile(self):
        model = TritonModel(name="m", version="1", compression_profile="worker_fast")
        assert model.matches_profile(CompressionProfile.WORKER_FAST)
        assert not model.matches_profile(CompressionProfile.PLANNER_SAFE)

    def test_matches_requirements_pass(self):
        model = TritonModel(
            name="m", version="1",
            accuracy=0.95, latency_ms=10.0, model_size_mb=100.0,
            tags=["finance", "risk"],
        )
        assert model.matches_requirements(
            min_accuracy=0.90,
            max_latency_ms=20.0,
            max_size_mb=200.0,
            required_tags=["finance"],
        )

    def test_matches_requirements_fail_accuracy(self):
        model = TritonModel(name="m", version="1", accuracy=0.80)
        assert not model.matches_requirements(min_accuracy=0.90)

    def test_matches_requirements_fail_latency(self):
        model = TritonModel(name="m", version="1", latency_ms=50.0)
        assert not model.matches_requirements(max_latency_ms=10.0)

    def test_matches_requirements_fail_size(self):
        model = TritonModel(name="m", version="1", model_size_mb=500.0)
        assert not model.matches_requirements(max_size_mb=100.0)

    def test_matches_requirements_fail_tags(self):
        model = TritonModel(name="m", version="1", tags=["finance"])
        assert not model.matches_requirements(required_tags=["security"])


# =====================================================================
# TritonModelRegistry TESTS
# =====================================================================

class TestTritonModelRegistry:
    """Tests for the TritonModelRegistry."""

    def test_register_and_get(self):
        reg = TritonModelRegistry()
        model = TritonModel(name="test-model", version="1.0")
        reg.register(model)
        assert reg.get("test-model") is model
        assert reg.get("nonexistent") is None

    def test_unregister(self):
        reg = TritonModelRegistry()
        reg.register(TritonModel(name="m", version="1"))
        assert reg.unregister("m")
        assert reg.get("m") is None
        assert not reg.unregister("m")

    def test_discover_loads_defaults(self):
        reg = TritonModelRegistry()
        models = reg.discover()
        assert len(models) > 0
        names = [m.name for m in models]
        assert "credit-risk-v4" in names
        assert "fraud-detection-v3" in names

    def test_discover_caches_results(self):
        reg = TritonModelRegistry()
        models1 = reg.discover()
        models2 = reg.discover()
        assert len(models1) == len(models2)

    def test_discover_force_refresh(self):
        reg = TritonModelRegistry()
        reg.discover()
        reg.register(TritonModel(name="extra", version="1"))
        models = reg.discover(force_refresh=True)
        names = [m.name for m in models]
        assert "extra" in names

    def test_search_by_query(self):
        reg = TritonModelRegistry()
        reg.discover()
        results = reg.search(query="fraud")
        assert len(results) >= 1
        assert all("fraud" in m.name.lower() or "fraud" in m.description.lower() for m in results)

    def test_search_by_profile(self):
        reg = TritonModelRegistry()
        reg.discover()
        results = reg.search(profile=CompressionProfile.PLANNER_SAFE)
        assert len(results) >= 1
        assert all(m.compression_profile == "planner_safe" for m in results)

    def test_search_by_tags(self):
        reg = TritonModelRegistry()
        reg.discover()
        results = reg.search(tags=["finance"])
        assert len(results) >= 1
        assert all("finance" in m.tags for m in results)

    def test_search_by_min_accuracy(self):
        reg = TritonModelRegistry()
        reg.discover()
        results = reg.search(min_accuracy=0.95)
        assert all(m.accuracy >= 0.95 for m in results)

    def test_recommend_for_compress_task(self):
        reg = TritonModelRegistry()
        reg.discover()
        results = reg.recommend_for_task("compress")
        assert len(results) >= 1
        profiles = {m.compression_profile for m in results}
        assert profiles <= {"worker_fast", "edge_extreme"}

    def test_recommend_for_preserve_task(self):
        reg = TritonModelRegistry()
        reg.discover()
        results = reg.recommend_for_task("preserve")
        assert len(results) >= 1
        assert all(m.compression_profile == "planner_safe" for m in results)

    def test_get_lsp_entries(self):
        reg = TritonModelRegistry()
        reg.discover()
        entries = reg.get_lsp_entries()
        assert len(entries) > 0
        assert all("name" in e and "description" in e for e in entries)

    def test_export_and_import(self):
        reg = TritonModelRegistry()
        reg.register(TritonModel(name="export-test", version="1.0", accuracy=0.99))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            reg.export_registry(path)
            new_reg = TritonModelRegistry()
            count = new_reg.import_registry(path)
            assert count == 1
            assert new_reg.get("export-test") is not None
            assert new_reg.get("export-test").accuracy == 0.99
        finally:
            os.unlink(path)

    def test_load_from_file(self):
        data = {
            "version": "1.0",
            "models": [
                {"name": "file-model", "version": "2.0", "accuracy": 0.88, "tags": ["test"]},
            ],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(data, f)
            path = f.name
        try:
            reg = TritonModelRegistry(registry_path=path)
            models = reg.discover()
            assert any(m.name == "file-model" for m in models)
        finally:
            os.unlink(path)

    def test_load_from_missing_file(self):
        reg = TritonModelRegistry(registry_path="/nonexistent/path.json")
        models = reg.discover()
        # Falls back to defaults
        assert len(models) > 0

    def test_env_var_config(self, monkeypatch):
        monkeypatch.setenv("TRITON_REGISTRY_URL", "http://example.com/registry")
        monkeypatch.setenv("TRITON_REGISTRY_PATH", "/some/path.json")
        reg = TritonModelRegistry()
        assert reg._registry_url == "http://example.com/registry"
        assert reg._registry_path == "/some/path.json"
