"""Tests for the Orchestra Visual Blueprint Editor."""

import json
import pytest

from orchestra.blueprint_editor.editor import (
    BlueprintEditor,
    GraphNode,
    GraphEdge,
    WorkflowGraph,
    NodePosition,
)


# =====================================================================
# ORC → GRAPH CONVERSION TESTS
# =====================================================================

class TestOrcToGraph:
    """Tests for parsing .orc source into visual graph."""

    def setup_method(self):
        self.editor = BlueprintEditor()

    def test_simple_workflow(self):
        source = '''workflow TestFlow {
    step analyze {
        agent: "gpt-4"
        prompt: "Analyze data"
    }
}
'''
        graph = self.editor.orc_to_graph(source)
        assert graph is not None
        assert len(graph.nodes) >= 2  # workflow + step
        types = [n.type for n in graph.nodes]
        assert "workflow" in types
        assert "step" in types

    def test_parallel_block(self):
        source = '''workflow Test {
    parallel {
        step a {
            agent: "gpt-4"
            prompt: "A"
        }
        step b {
            agent: "gpt-4"
            prompt: "B"
        }
    }
}
'''
        graph = self.editor.orc_to_graph(source)
        types = [n.type for n in graph.nodes]
        assert "parallel" in types

    def test_invalid_source_returns_none_or_empty(self):
        result = self.editor.orc_to_graph("not valid orc { {{")
        # Should return None or an empty/error graph
        assert result is None or len(result.nodes) == 0

    def test_empty_source(self):
        result = self.editor.orc_to_graph("")
        assert result is None or len(result.nodes) == 0


# =====================================================================
# GRAPH → ORC CONVERSION TESTS
# =====================================================================

class TestGraphToOrc:
    """Tests for generating .orc source from visual graph."""

    def setup_method(self):
        self.editor = BlueprintEditor()

    def test_basic_graph_to_orc(self):
        graph_data = {
            "nodes": [
                {"id": "w1", "type": "workflow", "label": "TestFlow",
                 "position": {"x": 0, "y": 0}, "properties": {}, "children": ["s1"]},
                {"id": "s1", "type": "step", "label": "analyze",
                 "position": {"x": 100, "y": 100},
                 "properties": {"agent": "gpt-4", "prompt": "Analyze data"},
                 "children": []},
            ],
            "edges": [
                {"source": "w1", "target": "s1", "label": ""},
            ],
        }
        orc = self.editor.graph_to_orc(graph_data)
        assert "workflow" in orc
        assert "TestFlow" in orc
        assert "step" in orc
        assert "analyze" in orc

    def test_empty_graph(self):
        graph_data = {"nodes": [], "edges": []}
        orc = self.editor.graph_to_orc(graph_data)
        assert isinstance(orc, str)


# =====================================================================
# VALIDATION TESTS
# =====================================================================

class TestValidation:
    """Tests for .orc validation through the editor."""

    def setup_method(self):
        self.editor = BlueprintEditor()

    def test_validate_valid_source(self):
        source = '''workflow TestFlow {
    step analyze {
        agent: "gpt-4"
        prompt: "Analyze data"
    }
}
'''
        result = self.editor.validate_orc(source)
        assert result is not None
        assert isinstance(result, dict)

    def test_validate_invalid_source(self):
        result = self.editor.validate_orc("not valid {{")
        assert result is not None


# =====================================================================
# ROUNDTRIP TESTS
# =====================================================================

class TestRoundtrip:
    """Tests for orc → graph → orc roundtrip fidelity."""

    def setup_method(self):
        self.editor = BlueprintEditor()

    def test_simple_roundtrip(self):
        source = '''workflow TestFlow {
    step analyze {
        agent: "gpt-4"
        prompt: "Analyze data"
    }
}
'''
        graph = self.editor.orc_to_graph(source)
        if graph is not None and len(graph.nodes) > 0:
            graph_data = graph.to_dict()
            orc = self.editor.graph_to_orc(graph_data)
            assert "workflow" in orc
            assert "step" in orc


# =====================================================================
# DATA STRUCTURE TESTS
# =====================================================================

class TestGraphDataStructures:
    """Tests for graph data structures."""

    def test_graph_node_creation(self):
        node = GraphNode(id="n1", type="step", label="analyze")
        assert node.id == "n1"
        assert node.type == "step"
        assert node.position.x == 0.0

    def test_graph_edge_creation(self):
        edge = GraphEdge(id="e1", source="n1", target="n2")
        assert edge.source == "n1"
        assert edge.target == "n2"
        assert edge.id == "e1"

    def test_workflow_graph(self):
        graph = WorkflowGraph()
        graph.nodes.append(GraphNode(id="n1", type="workflow", label="Test"))
        assert len(graph.nodes) == 1

    def test_graph_node_to_dict(self):
        node = GraphNode(id="n1", type="step", label="test")
        d = node.to_dict()
        assert d["id"] == "n1"
        assert d["type"] == "step"

    def test_node_position(self):
        pos = NodePosition(x=100.0, y=200.0)
        assert pos.x == 100.0
        assert pos.y == 200.0
