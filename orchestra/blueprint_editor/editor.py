"""Orchestra Visual Blueprint Editor — backend and HTML generator.

Provides:
- BlueprintEditor: main class that parses .orc ↔ visual graph JSON
- HTML/JS single-page application served via a simple HTTP server
- REST API for import/export/validate operations
"""

from __future__ import annotations

import html
import http.server
import json
import logging
import os
import socketserver
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from orchestra.parser.lexer import Lexer, LexerError
from orchestra.parser.parser import Parser, ParseError
from orchestra.parser.compiler_bridge import OrcCompiler

logger = logging.getLogger("orchestra-blueprint-editor")


# ── Graph Data Structures ────────────────────────────────────────────

@dataclass
class NodePosition:
    x: float = 0.0
    y: float = 0.0


@dataclass
class GraphNode:
    id: str
    type: str  # workflow, step, parallel, guard, budget, quality_gate, circuit_breaker, if, match, try, finally, for_each
    label: str
    position: NodePosition = field(default_factory=NodePosition)
    properties: dict[str, Any] = field(default_factory=dict)
    children: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "position": {"x": self.position.x, "y": self.position.y},
            "properties": self.properties,
            "children": self.children,
        }


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    label: str = ""
    edge_type: str = "default"  # default, conditional, fallback, parallel

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "label": self.label,
            "type": self.edge_type,
        }


@dataclass
class WorkflowGraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "metadata": self.metadata,
        }


# ── Blueprint Editor ─────────────────────────────────────────────────

class BlueprintEditor:
    """Bidirectional converter between .orc source and visual workflow graphs."""

    def __init__(self) -> None:
        self._compiler = OrcCompiler()
        self._node_counter = 0

    def _next_id(self, prefix: str = "node") -> str:
        self._node_counter += 1
        return f"{prefix}_{self._node_counter}"

    # ── .orc → Graph ─────────────────────────────────────────────

    def orc_to_graph(self, source: str) -> WorkflowGraph:
        """Parse .orc source and convert to a visual graph representation."""
        self._node_counter = 0
        parser = Parser(source)
        workflows = parser.parse()

        graph = WorkflowGraph()
        y_offset = 0

        for wf in workflows:
            wf_node = self._workflow_to_graph(wf, graph, y_offset)
            y_offset += 200
            graph.metadata["workflow_name"] = getattr(wf, "name", "unknown")
            graph.metadata["version"] = getattr(wf, "version", "")
            graph.metadata["owner"] = getattr(wf, "owner", "")
            graph.metadata["protected_by"] = getattr(wf, "protected_by", "")

        return graph

    def _workflow_to_graph(self, wf, graph: WorkflowGraph, y_start: float) -> GraphNode:
        """Convert a WorkflowNode to graph nodes and edges."""
        wf_id = self._next_id("workflow")
        wf_node = GraphNode(
            id=wf_id,
            type="workflow",
            label=getattr(wf, "name", "workflow"),
            position=NodePosition(400, y_start),
            properties={
                "version": getattr(wf, "version", ""),
                "owner": getattr(wf, "owner", ""),
                "protected_by": getattr(wf, "protected_by", ""),
                "criticality": getattr(wf, "criticality", ""),
            },
        )
        graph.nodes.append(wf_node)

        prev_id = wf_id
        y = y_start + 120

        # Guard
        guard = getattr(wf, "guard", None)
        if guard:
            guard_id = self._next_id("guard")
            reqs = [getattr(r, "raw", str(r)) for r in getattr(guard, "requirements", [])]
            guard_node = GraphNode(
                id=guard_id, type="guard", label="guard",
                position=NodePosition(400, y),
                properties={"requirements": reqs},
            )
            graph.nodes.append(guard_node)
            graph.edges.append(GraphEdge(self._next_id("edge"), prev_id, guard_id))
            wf_node.children.append(guard_id)
            prev_id = guard_id
            y += 100

        # Budget
        budget = getattr(wf, "budget", None)
        if budget:
            budget_id = self._next_id("budget")
            budget_node = GraphNode(
                id=budget_id, type="budget", label="budget",
                position=NodePosition(400, y),
                properties={
                    "per_task": getattr(budget, "per_task", 0),
                    "hourly_limit": getattr(budget, "hourly_limit", 0),
                    "alert_at": getattr(budget, "alert_at", 0),
                },
            )
            graph.nodes.append(budget_node)
            graph.edges.append(GraphEdge(self._next_id("edge"), prev_id, budget_id))
            wf_node.children.append(budget_id)
            prev_id = budget_id
            y += 100

        # Circuit breaker
        cb = getattr(wf, "circuit_breaker", None)
        if cb:
            cb_id = self._next_id("cb")
            cb_node = GraphNode(
                id=cb_id, type="circuit_breaker", label="circuit_breaker",
                position=NodePosition(400, y),
                properties={
                    "failure_threshold": getattr(cb, "failure_threshold", 0),
                    "timeout": getattr(cb, "timeout", 0),
                    "half_open_after": getattr(cb, "half_open_after", 0),
                },
            )
            graph.nodes.append(cb_node)
            graph.edges.append(GraphEdge(self._next_id("edge"), prev_id, cb_id))
            wf_node.children.append(cb_id)
            prev_id = cb_id
            y += 100

        # Body nodes
        body = getattr(wf, "body", [])
        for node in body:
            new_id, y = self._body_node_to_graph(node, graph, prev_id, wf_node, 400, y)
            if new_id:
                prev_id = new_id

        # Quality gate
        qg = getattr(wf, "quality_gate", None)
        if qg:
            qg_id = self._next_id("qgate")
            qg_node = GraphNode(
                id=qg_id, type="quality_gate", label="quality_gate",
                position=NodePosition(400, y),
                properties={"metrics": getattr(qg, "metrics", {})},
            )
            graph.nodes.append(qg_node)
            graph.edges.append(GraphEdge(self._next_id("edge"), prev_id, qg_id))
            wf_node.children.append(qg_id)
            prev_id = qg_id
            y += 100

        # Finally
        fin = getattr(wf, "finally_block", None)
        if fin:
            fin_id = self._next_id("finally")
            fin_node = GraphNode(
                id=fin_id, type="finally", label="finally",
                position=NodePosition(400, y),
            )
            graph.nodes.append(fin_node)
            graph.edges.append(GraphEdge(self._next_id("edge"), prev_id, fin_id))
            wf_node.children.append(fin_id)

        return wf_node

    def _body_node_to_graph(self, node, graph: WorkflowGraph, prev_id: str, parent: GraphNode, x: float, y: float) -> tuple[str | None, float]:
        """Convert a body node (step, parallel, if, etc.) to graph nodes."""
        node_type = type(node).__name__

        if node_type == "StepNode":
            step_id = self._next_id("step")
            agent_str = self._agent_to_str(getattr(node, "agent", None))
            step_node = GraphNode(
                id=step_id, type="step", label=getattr(node, "name", "step"),
                position=NodePosition(x, y),
                properties={
                    "agent": agent_str,
                    "model": getattr(node, "model", ""),
                    "task": getattr(node, "task", ""),
                    "timeout": getattr(node, "timeout", None),
                },
            )
            graph.nodes.append(step_node)
            graph.edges.append(GraphEdge(self._next_id("edge"), prev_id, step_id))
            parent.children.append(step_id)
            return step_id, y + 100

        elif node_type == "ParallelNode":
            par_id = self._next_id("parallel")
            par_node = GraphNode(
                id=par_id, type="parallel", label="parallel",
                position=NodePosition(x, y),
            )
            graph.nodes.append(par_node)
            graph.edges.append(GraphEdge(self._next_id("edge"), prev_id, par_id))
            parent.children.append(par_id)

            steps = getattr(node, "steps", [])
            step_x = x - (len(steps) - 1) * 100
            for step in steps:
                step_id = self._next_id("step")
                agent_str = self._agent_to_str(getattr(step, "agent", None))
                step_gn = GraphNode(
                    id=step_id, type="step", label=getattr(step, "name", "step"),
                    position=NodePosition(step_x, y + 80),
                    properties={
                        "agent": agent_str,
                        "task": getattr(step, "task", ""),
                        "timeout": getattr(step, "timeout", None),
                    },
                )
                graph.nodes.append(step_gn)
                graph.edges.append(GraphEdge(self._next_id("edge"), par_id, step_id, edge_type="parallel"))
                par_node.children.append(step_id)
                step_x += 200

            return par_id, y + 180

        elif node_type == "IfNode":
            if_id = self._next_id("if")
            condition = getattr(node, "condition", None)
            cond_str = getattr(condition, "raw", str(condition)) if condition else ""
            if_node = GraphNode(
                id=if_id, type="if", label=f"if {cond_str}",
                position=NodePosition(x, y),
                properties={"condition": cond_str},
            )
            graph.nodes.append(if_node)
            graph.edges.append(GraphEdge(self._next_id("edge"), prev_id, if_id))
            parent.children.append(if_id)

            # Then branch
            then_body = getattr(node, "body", [])
            then_prev = if_id
            then_y = y + 100
            for child in then_body:
                new_id, then_y = self._body_node_to_graph(child, graph, then_prev, if_node, x - 150, then_y)
                if new_id:
                    then_prev = new_id

            # Else branch
            else_body = getattr(node, "else_body", [])
            else_prev = if_id
            else_y = y + 100
            for child in else_body:
                new_id, else_y = self._body_node_to_graph(child, graph, else_prev, if_node, x + 150, else_y)
                if new_id:
                    else_prev = new_id

            return if_id, max(then_y, else_y)

        elif node_type == "TryNode":
            try_id = self._next_id("try")
            try_node = GraphNode(
                id=try_id, type="try", label="try",
                position=NodePosition(x, y),
            )
            graph.nodes.append(try_node)
            graph.edges.append(GraphEdge(self._next_id("edge"), prev_id, try_id))
            parent.children.append(try_id)

            try_body = getattr(node, "body", [])
            try_prev = try_id
            try_y = y + 100
            for child in try_body:
                new_id, try_y = self._body_node_to_graph(child, graph, try_prev, try_node, x, try_y)
                if new_id:
                    try_prev = new_id

            return try_id, try_y

        elif node_type == "MatchNode":
            match_id = self._next_id("match")
            expr = getattr(node, "expression", None)
            expr_str = getattr(expr, "raw", str(expr)) if expr else ""
            match_node = GraphNode(
                id=match_id, type="match", label=f"match {expr_str}",
                position=NodePosition(x, y),
                properties={"expression": expr_str},
            )
            graph.nodes.append(match_node)
            graph.edges.append(GraphEdge(self._next_id("edge"), prev_id, match_id))
            parent.children.append(match_id)
            return match_id, y + 100

        elif node_type == "ForEachNode":
            fe_id = self._next_id("foreach")
            fe_node = GraphNode(
                id=fe_id, type="for_each",
                label=f"for each {getattr(node, 'variable', '')} in {getattr(node, 'collection', '')}",
                position=NodePosition(x, y),
            )
            graph.nodes.append(fe_node)
            graph.edges.append(GraphEdge(self._next_id("edge"), prev_id, fe_id))
            parent.children.append(fe_id)
            return fe_id, y + 100

        return None, y

    def _agent_to_str(self, agent) -> str:
        """Convert an agent AST node to a display string."""
        if agent is None:
            return ""
        node_type = type(agent).__name__
        if node_type == "AgentRef":
            return getattr(agent, "name", "")
        elif node_type == "TritonAgent":
            return f'triton_ternary("{getattr(agent, "model_name", "")}")'
        elif node_type == "CascadeAgent":
            parts = []
            if getattr(agent, "try_agent", None):
                parts.append(f"try: {getattr(agent.try_agent, 'name', '')}")
            if getattr(agent, "fallback", None):
                parts.append(f"fallback: {getattr(agent.fallback, 'name', '')}")
            return f"cascade [{', '.join(parts)}]"
        elif node_type == "CheapestAboveAgent":
            return f"cheapest_above({getattr(agent, 'quality_threshold', '')})"
        elif node_type == "BestForAgent":
            return "best_for(...)"
        return str(agent)

    # ── Graph → .orc ─────────────────────────────────────────────

    def graph_to_orc(self, graph_data: dict) -> str:
        """Convert a visual graph JSON back to .orc source code."""
        nodes = {n["id"]: n for n in graph_data.get("nodes", [])}
        edges = graph_data.get("edges", [])
        metadata = graph_data.get("metadata", {})

        # Find workflow root
        workflow_nodes = [n for n in nodes.values() if n["type"] == "workflow"]
        if not workflow_nodes:
            return ""

        lines: list[str] = []
        for wf in workflow_nodes:
            self._emit_workflow(wf, nodes, edges, metadata, lines)

        return "\n".join(lines) + "\n"

    def _emit_workflow(self, wf: dict, nodes: dict, edges: list, metadata: dict, lines: list[str]) -> None:
        """Emit .orc source for a workflow node."""
        name = wf.get("label", "workflow")
        lines.append(f"workflow {name} {{")

        props = wf.get("properties", {})
        if props.get("version"):
            lines.append(f'    version: "{props["version"]}"')
        elif metadata.get("version"):
            lines.append(f'    version: "{metadata["version"]}"')

        if props.get("owner"):
            lines.append(f'    owner: "{props["owner"]}"')
        elif metadata.get("owner"):
            lines.append(f'    owner: "{metadata["owner"]}"')

        if props.get("protected_by"):
            lines.append(f"    protected_by: {props['protected_by']}")
        elif metadata.get("protected_by"):
            lines.append(f"    protected_by: {metadata['protected_by']}")

        if props.get("criticality"):
            lines.append(f"    criticality: {props['criticality']}")

        lines.append("")

        # Emit children in order
        children_ids = wf.get("children", [])
        for child_id in children_ids:
            child = nodes.get(child_id)
            if child:
                self._emit_node(child, nodes, edges, lines, indent=1)

        lines.append("}")

    def _emit_node(self, node: dict, nodes: dict, edges: list, lines: list[str], indent: int = 1) -> None:
        """Emit .orc source for a graph node."""
        pad = "    " * indent
        node_type = node.get("type", "")
        props = node.get("properties", {})

        if node_type == "step":
            name = node.get("label", "step")
            lines.append(f"{pad}step {name} {{")
            if props.get("agent"):
                lines.append(f"{pad}    agent: {props['agent']}")
            if props.get("model"):
                lines.append(f'{pad}    model: "{props["model"]}"')
            if props.get("task"):
                lines.append(f'{pad}    task: "{props["task"]}"')
            if props.get("timeout"):
                lines.append(f"{pad}    timeout: {props['timeout']}")
            lines.append(f"{pad}}}")
            lines.append("")

        elif node_type == "parallel":
            lines.append(f"{pad}parallel {{")
            for child_id in node.get("children", []):
                child = nodes.get(child_id)
                if child:
                    self._emit_node(child, nodes, edges, lines, indent + 1)
            lines.append(f"{pad}}}")
            lines.append("")

        elif node_type == "guard":
            lines.append(f"{pad}guard {{")
            for req in props.get("requirements", []):
                lines.append(f"{pad}    require: {req}")
            lines.append(f"{pad}}}")
            lines.append("")

        elif node_type == "budget":
            lines.append(f"{pad}budget {{")
            if props.get("per_task"):
                lines.append(f"{pad}    per_task: {props['per_task']}")
            if props.get("hourly_limit"):
                lines.append(f"{pad}    hourly_limit: {props['hourly_limit']}")
            if props.get("alert_at"):
                lines.append(f"{pad}    alert_at: {props['alert_at']}")
            lines.append(f"{pad}}}")
            lines.append("")

        elif node_type == "circuit_breaker":
            lines.append(f"{pad}circuit_breaker {{")
            if props.get("failure_threshold"):
                lines.append(f"{pad}    failure_threshold: {props['failure_threshold']}")
            if props.get("timeout"):
                lines.append(f"{pad}    timeout: {props['timeout']}")
            if props.get("half_open_after"):
                lines.append(f"{pad}    half_open_after: {props['half_open_after']}")
            lines.append(f"{pad}}}")
            lines.append("")

        elif node_type == "quality_gate":
            lines.append(f"{pad}quality_gate {{")
            metrics = props.get("metrics", {})
            if metrics:
                lines.append(f"{pad}    metrics: {{")
                for k, v in metrics.items():
                    lines.append(f"{pad}        {k}: {v}")
                lines.append(f"{pad}    }}")
            lines.append(f"{pad}}}")
            lines.append("")

        elif node_type == "if":
            condition = props.get("condition", "true")
            lines.append(f"{pad}if {condition} {{")
            for child_id in node.get("children", []):
                child = nodes.get(child_id)
                if child:
                    self._emit_node(child, nodes, edges, lines, indent + 1)
            lines.append(f"{pad}}}")
            lines.append("")

        elif node_type == "try":
            lines.append(f"{pad}try {{")
            for child_id in node.get("children", []):
                child = nodes.get(child_id)
                if child:
                    self._emit_node(child, nodes, edges, lines, indent + 1)
            lines.append(f"{pad}}}")
            lines.append("")

        elif node_type == "finally":
            lines.append(f"{pad}finally {{")
            for child_id in node.get("children", []):
                child = nodes.get(child_id)
                if child:
                    self._emit_node(child, nodes, edges, lines, indent + 1)
            lines.append(f"{pad}}}")
            lines.append("")

    # ── Validation ───────────────────────────────────────────────

    def validate_orc(self, source: str) -> dict:
        """Validate .orc source and return results."""
        try:
            self._compiler.compile_source(source)
            return {"valid": True, "errors": []}
        except Exception as e:
            return {"valid": False, "errors": [str(e)]}

    # ── HTTP Server ──────────────────────────────────────────────

    def serve(self, host: str = "127.0.0.1", port: int = 8420) -> None:
        """Start the blueprint editor web server."""
        editor = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path == "/" or parsed.path == "/index.html":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(_EDITOR_HTML.encode("utf-8"))
                elif parsed.path == "/api/health":
                    self._json_response({"status": "ok"})
                else:
                    self.send_error(404)

            def do_POST(self) -> None:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""

                parsed = urlparse(self.path)

                if parsed.path == "/api/parse":
                    try:
                        data = json.loads(body)
                        source = data.get("source", "")
                        graph = editor.orc_to_graph(source)
                        self._json_response({"success": True, "graph": graph.to_dict()})
                    except Exception as e:
                        self._json_response({"success": False, "error": str(e)})

                elif parsed.path == "/api/generate":
                    try:
                        data = json.loads(body)
                        orc_source = editor.graph_to_orc(data.get("graph", {}))
                        self._json_response({"success": True, "source": orc_source})
                    except Exception as e:
                        self._json_response({"success": False, "error": str(e)})

                elif parsed.path == "/api/validate":
                    try:
                        data = json.loads(body)
                        source = data.get("source", "")
                        result = editor.validate_orc(source)
                        self._json_response({"success": True, "result": result})
                    except Exception as e:
                        self._json_response({"success": False, "error": str(e)})
                else:
                    self.send_error(404)

            def _json_response(self, data: dict) -> None:
                body = json.dumps(data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:
                logger.info(format, *args)

        with socketserver.TCPServer((host, port), Handler) as httpd:
            httpd.allow_reuse_address = True
            logger.info(f"Blueprint Editor running at http://{host}:{port}")
            print(f"🎼 Orchestra Blueprint Editor running at http://{host}:{port}")
            print("   Open in your browser to design workflows visually.")
            print("   Press Ctrl+C to stop.")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nEditor stopped.")


# ── HTML Application ─────────────────────────────────────────────────

_EDITOR_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Orchestra Blueprint Editor</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; height: 100vh; overflow: hidden; }
.header { background: #161b22; border-bottom: 1px solid #30363d; padding: 8px 16px; display: flex; align-items: center; justify-content: space-between; height: 48px; }
.header h1 { font-size: 16px; font-weight: 600; color: #f0f6fc; }
.header h1 span { color: #58a6ff; }
.toolbar { display: flex; gap: 8px; }
.btn { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; transition: all 0.15s; }
.btn:hover { background: #30363d; border-color: #8b949e; }
.btn-primary { background: #238636; border-color: #238636; color: #fff; }
.btn-primary:hover { background: #2ea043; }
.main { display: flex; height: calc(100vh - 48px); }
.sidebar { width: 240px; background: #161b22; border-right: 1px solid #30363d; overflow-y: auto; padding: 12px; flex-shrink: 0; }
.sidebar h3 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #8b949e; margin: 12px 0 8px; }
.sidebar h3:first-child { margin-top: 0; }
.block-item { background: #21262d; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; cursor: grab; font-size: 13px; transition: all 0.15s; display: flex; align-items: center; gap: 8px; }
.block-item:hover { border-color: #58a6ff; background: #1c2333; }
.block-item .icon { width: 20px; text-align: center; font-size: 14px; }
.canvas-area { flex: 1; position: relative; overflow: hidden; }
.canvas { width: 100%; height: 100%; }
.editor-panel { width: 400px; background: #161b22; border-left: 1px solid #30363d; display: flex; flex-direction: column; flex-shrink: 0; }
.editor-tabs { display: flex; border-bottom: 1px solid #30363d; }
.tab { padding: 8px 16px; font-size: 13px; cursor: pointer; border-bottom: 2px solid transparent; color: #8b949e; }
.tab.active { color: #f0f6fc; border-bottom-color: #f78166; }
.editor-content { flex: 1; overflow: hidden; }
textarea { width: 100%; height: 100%; background: #0d1117; color: #c9d1d9; border: none; padding: 12px; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px; line-height: 1.6; resize: none; outline: none; tab-size: 4; }
.properties-panel { padding: 12px; overflow-y: auto; height: 100%; }
.prop-group { margin-bottom: 16px; }
.prop-label { font-size: 12px; color: #8b949e; margin-bottom: 4px; display: block; }
.prop-input { width: 100%; background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 10px; border-radius: 4px; font-size: 13px; outline: none; }
.prop-input:focus { border-color: #58a6ff; }
.status-bar { background: #161b22; border-top: 1px solid #30363d; padding: 4px 16px; font-size: 12px; color: #8b949e; display: flex; justify-content: space-between; }
.node { position: absolute; background: #21262d; border: 2px solid #30363d; border-radius: 8px; padding: 8px 14px; cursor: move; font-size: 13px; min-width: 120px; text-align: center; user-select: none; transition: border-color 0.15s; z-index: 2; }
.node:hover { border-color: #58a6ff; }
.node.selected { border-color: #f78166; box-shadow: 0 0 0 2px rgba(247, 129, 102, 0.2); }
.node-type { font-size: 10px; text-transform: uppercase; color: #8b949e; letter-spacing: 0.5px; margin-bottom: 2px; }
.node-label { font-weight: 600; color: #f0f6fc; }
.node.type-workflow { border-color: #58a6ff; }
.node.type-step { border-color: #3fb950; }
.node.type-parallel { border-color: #d2a8ff; }
.node.type-guard { border-color: #f0883e; }
.node.type-budget { border-color: #f0883e; }
.node.type-quality_gate { border-color: #f85149; }
.node.type-if { border-color: #d2a8ff; }
.node.type-try { border-color: #79c0ff; }
.node.type-finally { border-color: #8b949e; }
svg.connections { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1; }
svg.connections line { stroke: #30363d; stroke-width: 2; }
.empty-canvas { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; color: #484f58; }
.empty-canvas p { font-size: 14px; margin-top: 8px; }
.diagnostic { padding: 6px 12px; font-size: 12px; border-bottom: 1px solid #30363d; }
.diagnostic.error { color: #f85149; }
.diagnostic.warning { color: #f0883e; }
.diagnostic.info { color: #58a6ff; }
</style>
</head>
<body>
<div class="header">
    <h1>&#127932; <span>Orchestra</span> Blueprint Editor</h1>
    <div class="toolbar">
        <button class="btn" onclick="importOrc()">Import .orc</button>
        <button class="btn" onclick="exportOrc()">Export .orc</button>
        <button class="btn" onclick="validateOrc()">Validate</button>
        <button class="btn btn-primary" onclick="syncFromCode()">Sync from Code</button>
    </div>
</div>
<div class="main">
    <div class="sidebar">
        <h3>Blocks</h3>
        <div class="block-item" draggable="true" ondragstart="dragBlock(event, 'step')">
            <span class="icon">&#9654;</span> Step
        </div>
        <div class="block-item" draggable="true" ondragstart="dragBlock(event, 'parallel')">
            <span class="icon">&#8694;</span> Parallel
        </div>
        <div class="block-item" draggable="true" ondragstart="dragBlock(event, 'if')">
            <span class="icon">&#10140;</span> Condition
        </div>
        <div class="block-item" draggable="true" ondragstart="dragBlock(event, 'try')">
            <span class="icon">&#128737;</span> Try/Catch
        </div>
        <h3>Constraints</h3>
        <div class="block-item" draggable="true" ondragstart="dragBlock(event, 'guard')">
            <span class="icon">&#128274;</span> Guard
        </div>
        <div class="block-item" draggable="true" ondragstart="dragBlock(event, 'budget')">
            <span class="icon">&#128176;</span> Budget
        </div>
        <div class="block-item" draggable="true" ondragstart="dragBlock(event, 'quality_gate')">
            <span class="icon">&#9989;</span> Quality Gate
        </div>
        <div class="block-item" draggable="true" ondragstart="dragBlock(event, 'circuit_breaker')">
            <span class="icon">&#9889;</span> Circuit Breaker
        </div>
        <h3>Lifecycle</h3>
        <div class="block-item" draggable="true" ondragstart="dragBlock(event, 'finally')">
            <span class="icon">&#127937;</span> Finally
        </div>
        <div class="block-item" draggable="true" ondragstart="dragBlock(event, 'match')">
            <span class="icon">&#128268;</span> Match/Case
        </div>
        <div class="block-item" draggable="true" ondragstart="dragBlock(event, 'for_each')">
            <span class="icon">&#128260;</span> For Each
        </div>
    </div>
    <div class="canvas-area" id="canvasArea" ondrop="dropBlock(event)" ondragover="event.preventDefault()">
        <svg class="connections" id="connections"></svg>
        <div id="nodeContainer"></div>
        <div class="empty-canvas" id="emptyCanvas">
            <div style="font-size: 48px; opacity: 0.5;">&#127932;</div>
            <p>Drag blocks from the sidebar or import a .orc file</p>
        </div>
    </div>
    <div class="editor-panel">
        <div class="editor-tabs">
            <div class="tab active" id="tabCode" onclick="switchTab('code')">Code</div>
            <div class="tab" id="tabProps" onclick="switchTab('props')">Properties</div>
            <div class="tab" id="tabDiag" onclick="switchTab('diagnostics')">Diagnostics</div>
        </div>
        <div class="editor-content">
            <div id="codeView" style="height:100%">
                <textarea id="codeEditor" spellcheck="false" placeholder="# Write or paste .orc code here..."></textarea>
            </div>
            <div id="propsView" style="display:none; height:100%">
                <div class="properties-panel" id="propsPanel">
                    <p style="color: #484f58; font-size: 13px;">Select a node to edit its properties.</p>
                </div>
            </div>
            <div id="diagView" style="display:none; height:100%">
                <div id="diagnosticsPanel" style="padding:8px;"></div>
            </div>
        </div>
    </div>
</div>
<div class="status-bar">
    <span id="statusText">Ready</span>
    <span id="nodeCount">0 nodes</span>
</div>
<script>
let graph = { nodes: [], edges: [], metadata: { version: "2.0", owner: "", protected_by: "bunny_guardian" } };
let selectedNodeId = null;
let nodeCounter = 0;
let dragging = null;
let dragOffset = { x: 0, y: 0 };

function nextId(prefix) { return prefix + '_' + (++nodeCounter); }

function dragBlock(e, type) { e.dataTransfer.setData('blockType', type); }

function dropBlock(e) {
    e.preventDefault();
    const type = e.dataTransfer.getData('blockType');
    if (!type) return;
    const rect = document.getElementById('canvasArea').getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    addNode(type, type, x, y);
}

function addNode(type, label, x, y, props) {
    const id = nextId(type);
    const node = {
        id, type, label: label || type,
        position: { x, y },
        properties: props || {},
        children: []
    };
    graph.nodes.push(node);
    renderGraph();
    selectNode(id);
    updateStatus('Added ' + type + ' node');
    document.getElementById('emptyCanvas').style.display = 'none';
    syncToCode();
    return id;
}

function renderGraph() {
    const container = document.getElementById('nodeContainer');
    container.innerHTML = '';
    graph.nodes.forEach(n => {
        const el = document.createElement('div');
        el.className = 'node type-' + n.type + (n.id === selectedNodeId ? ' selected' : '');
        el.style.left = n.position.x + 'px';
        el.style.top = n.position.y + 'px';
        el.id = 'node-' + n.id;
        el.innerHTML = '<div class="node-type">' + n.type + '</div><div class="node-label">' + escapeHtml(n.label) + '</div>';
        el.onmousedown = function(e) { startDrag(e, n.id); };
        el.onclick = function(e) { e.stopPropagation(); selectNode(n.id); };
        container.appendChild(el);
    });

    const svg = document.getElementById('connections');
    svg.innerHTML = '';
    graph.edges.forEach(edge => {
        const src = graph.nodes.find(n => n.id === edge.source);
        const tgt = graph.nodes.find(n => n.id === edge.target);
        if (src && tgt) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', src.position.x + 60);
            line.setAttribute('y1', src.position.y + 35);
            line.setAttribute('x2', tgt.position.x + 60);
            line.setAttribute('y2', tgt.position.y);
            svg.appendChild(line);
        }
    });

    document.getElementById('nodeCount').textContent = graph.nodes.length + ' nodes';
    if (graph.nodes.length === 0) document.getElementById('emptyCanvas').style.display = '';
}

function escapeHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function selectNode(id) {
    selectedNodeId = id;
    renderGraph();
    showProperties(id);
}

function showProperties(id) {
    const node = graph.nodes.find(n => n.id === id);
    const panel = document.getElementById('propsPanel');
    if (!node) { panel.innerHTML = '<p style="color:#484f58;font-size:13px;">Select a node.</p>'; return; }

    let html = '<div class="prop-group"><label class="prop-label">Type</label><input class="prop-input" value="' + node.type + '" disabled></div>';
    html += '<div class="prop-group"><label class="prop-label">Label</label><input class="prop-input" value="' + escapeHtml(node.label) + '" onchange="updateProp(\\'' + id + '\\', \\'label\\', this.value)"></div>';

    if (node.type === 'step') {
        html += propInput(id, 'agent', node.properties.agent || '');
        html += propInput(id, 'task', node.properties.task || '');
        html += propInput(id, 'timeout', node.properties.timeout || '');
        html += propInput(id, 'model', node.properties.model || '');
    } else if (node.type === 'guard') {
        html += propInput(id, 'requirements', (node.properties.requirements || []).join(', '));
    } else if (node.type === 'budget') {
        html += propInput(id, 'per_task', node.properties.per_task || '');
        html += propInput(id, 'hourly_limit', node.properties.hourly_limit || '');
        html += propInput(id, 'alert_at', node.properties.alert_at || '');
    } else if (node.type === 'if') {
        html += propInput(id, 'condition', node.properties.condition || '');
    } else if (node.type === 'circuit_breaker') {
        html += propInput(id, 'failure_threshold', node.properties.failure_threshold || '');
        html += propInput(id, 'timeout', node.properties.timeout || '');
        html += propInput(id, 'half_open_after', node.properties.half_open_after || '');
    }

    html += '<div style="margin-top:16px;"><button class="btn" style="width:100%;color:#f85149;" onclick="deleteNode(\\'' + id + '\\')">Delete Node</button></div>';
    panel.innerHTML = html;
}

function propInput(id, key, value) {
    return '<div class="prop-group"><label class="prop-label">' + key + '</label><input class="prop-input" value="' + escapeHtml(String(value)) + '" onchange="updateNodeProp(\\'' + id + '\\', \\'' + key + '\\', this.value)"></div>';
}

function updateProp(id, key, value) {
    const node = graph.nodes.find(n => n.id === id);
    if (node) { node[key] = value; renderGraph(); syncToCode(); }
}

function updateNodeProp(id, key, value) {
    const node = graph.nodes.find(n => n.id === id);
    if (node) { node.properties[key] = value; syncToCode(); }
}

function deleteNode(id) {
    graph.nodes = graph.nodes.filter(n => n.id !== id);
    graph.edges = graph.edges.filter(e => e.source !== id && e.target !== id);
    graph.nodes.forEach(n => { n.children = n.children.filter(c => c !== id); });
    selectedNodeId = null;
    renderGraph();
    showProperties(null);
    syncToCode();
}

function startDrag(e, id) {
    dragging = id;
    const node = graph.nodes.find(n => n.id === id);
    dragOffset = { x: e.clientX - node.position.x, y: e.clientY - node.position.y };
    document.onmousemove = function(e) {
        if (!dragging) return;
        const n = graph.nodes.find(n => n.id === dragging);
        if (n) { n.position.x = e.clientX - dragOffset.x; n.position.y = e.clientY - dragOffset.y; renderGraph(); }
    };
    document.onmouseup = function() { dragging = null; document.onmousemove = null; document.onmouseup = null; };
}

function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById('codeView').style.display = tab === 'code' ? '' : 'none';
    document.getElementById('propsView').style.display = tab === 'props' ? '' : 'none';
    document.getElementById('diagView').style.display = tab === 'diagnostics' ? '' : 'none';
    document.getElementById('tab' + tab.charAt(0).toUpperCase() + tab.slice(1)).classList.add('active');
    if (tab === 'code') document.getElementById('tabCode').classList.add('active');
    if (tab === 'props') document.getElementById('tabProps').classList.add('active');
    if (tab === 'diagnostics') document.getElementById('tabDiag').classList.add('active');
}

function syncToCode() {
    fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ graph: graph })
    }).then(r => r.json()).then(data => {
        if (data.success) document.getElementById('codeEditor').value = data.source;
    }).catch(() => {});
}

function syncFromCode() {
    const source = document.getElementById('codeEditor').value;
    if (!source.trim()) return;
    fetch('/api/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: source })
    }).then(r => r.json()).then(data => {
        if (data.success) {
            graph = data.graph;
            nodeCounter = graph.nodes.length + 10;
            renderGraph();
            updateStatus('Synced from code: ' + graph.nodes.length + ' nodes');
        } else {
            updateStatus('Parse error: ' + data.error);
        }
    }).catch(e => updateStatus('Error: ' + e));
}

function validateOrc() {
    const source = document.getElementById('codeEditor').value;
    fetch('/api/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: source })
    }).then(r => r.json()).then(data => {
        const panel = document.getElementById('diagnosticsPanel');
        if (data.success && data.result) {
            const r = data.result;
            let html = '';
            if (r.valid) html += '<div class="diagnostic info">Validation passed</div>';
            (r.errors || []).forEach(e => { html += '<div class="diagnostic error">' + escapeHtml(e) + '</div>'; });
            (r.warnings || []).forEach(w => { html += '<div class="diagnostic warning">' + escapeHtml(w) + '</div>'; });
            panel.innerHTML = html || '<div class="diagnostic info">No issues found</div>';
        } else {
            panel.innerHTML = '<div class="diagnostic error">' + escapeHtml(data.error || 'Validation failed') + '</div>';
        }
        switchTab('diagnostics');
    }).catch(e => updateStatus('Error: ' + e));
}

function importOrc() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.orc';
    input.onchange = function() {
        const file = input.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('codeEditor').value = e.target.result;
            syncFromCode();
        };
        reader.readAsText(file);
    };
    input.click();
}

function exportOrc() {
    const source = document.getElementById('codeEditor').value;
    const blob = new Blob([source], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (graph.metadata.workflow_name || 'workflow') + '.orc';
    a.click();
    URL.revokeObjectURL(url);
    updateStatus('Exported .orc file');
}

function updateStatus(msg) { document.getElementById('statusText').textContent = msg; }

document.getElementById('canvasArea').onclick = function() { selectedNodeId = null; renderGraph(); showProperties(null); };

renderGraph();
</script>
</body>
</html>"""


def main() -> None:
    """Entry point for the orchestra-editor console script."""
    import argparse
    ap = argparse.ArgumentParser(description="Orchestra Visual Blueprint Editor")
    ap.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8420, help="Port to bind (default: 8420)")
    args = ap.parse_args()
    editor = BlueprintEditor()
    editor.serve(host=args.host, port=args.port)
