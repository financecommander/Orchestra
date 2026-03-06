"""CLI entry point for the Orchestra .orc toolchain.

Commands::

    orchestra validate <file.orc>        # Validate syntax and structure
    orchestra compile  <file.orc>        # Compile to JSON execution plan
    orchestra parse    <file.orc>        # Dump AST (debug)
    orchestra info     <file.orc>        # Show summary info
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from orchestra.parser.compiler_bridge import OrcCompiler, CompilationError
from orchestra.parser.parser import Parser, ParseError
from orchestra.parser.lexer import Lexer, LexerError


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, 1 on failure."""
    args = _build_parser().parse_args(argv)

    if not hasattr(args, "command") or args.command is None:
        _build_parser().print_help()
        return 1

    try:
        handler = {
            "validate": _cmd_validate,
            "compile": _cmd_compile,
            "parse": _cmd_parse,
            "info": _cmd_info,
        }[args.command]
        return handler(args)
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130


# ── Argument parser ──────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="orchestra",
        description="Orchestra .orc DSL toolchain",
    )
    sub = p.add_subparsers(dest="command")

    # validate
    val = sub.add_parser("validate", help="Validate an .orc file")
    val.add_argument("file", help="Path to .orc file")

    # compile
    comp = sub.add_parser("compile", help="Compile .orc to execution plan")
    comp.add_argument("file", help="Path to .orc file")
    comp.add_argument("--output", "-o", help="Output file (default: stdout)")

    # parse (debug)
    par = sub.add_parser("parse", help="Parse and dump AST (debug)")
    par.add_argument("file", help="Path to .orc file")

    # info
    inf = sub.add_parser("info", help="Show summary of an .orc file")
    inf.add_argument("file", help="Path to .orc file")

    return p


# ── Commands ──────────────────────────────────────────────────────────

def _cmd_validate(args: argparse.Namespace) -> int:
    compiler = OrcCompiler()
    result = compiler.validate_file(args.file)

    if result["valid"]:
        print(f"✓ {args.file} is valid")
        for wf in result["workflows"]:
            print(f"  workflow: {wf['name']}")
            print(f"    agents: {', '.join(wf['agents']) or '(none)'}")
            print(f"    tasks:  {', '.join(wf['tasks']) or '(none)'}")
        if result["warnings"]:
            for w in result["warnings"]:
                print(f"  ⚠ {w}")
        return 0
    else:
        print(f"✗ {args.file} has errors:", file=sys.stderr)
        for e in result["errors"]:
            print(f"  {e}", file=sys.stderr)
        return 1


def _cmd_compile(args: argparse.Namespace) -> int:
    compiler = OrcCompiler()
    try:
        workflows = compiler.compile_file(args.file)
    except (ParseError, CompilationError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    plan = compiler.to_execution_plan(workflows)
    output = json.dumps(plan, indent=2, default=str)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"✓ Compiled {len(workflows)} workflow(s) → {args.output}")
    else:
        print(output)

    return 0


def _cmd_parse(args: argparse.Namespace) -> int:
    filepath = Path(args.file)
    if not filepath.exists():
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        return 1

    source = filepath.read_text(encoding="utf-8")
    try:
        parser = Parser(source)
        ast_nodes = parser.parse()
    except (LexerError, ParseError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    for wf in ast_nodes:
        _dump_node(wf, indent=0)

    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    compiler = OrcCompiler()
    try:
        workflows = compiler.compile_file(args.file)
    except (ParseError, CompilationError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    for wf in workflows:
        print(f"Workflow: {wf.name}")
        print(f"  Version:     {wf.metadata.get('orc_version', '—')}")
        print(f"  Owner:       {wf.metadata.get('owner', '—')}")
        print(f"  Protected:   {wf.metadata.get('protected_by', '—')}")
        print(f"  Criticality: {wf.metadata.get('criticality', '—')}")
        print(f"  Agents ({len(wf.agents)}):")
        for name, agent in wf.agents.items():
            prov = agent.provider or "—"
            print(f"    {name} (provider: {prov})")
        print(f"  Tasks ({len(wf.tasks)}):")
        for name, task in wf.tasks.items():
            deps = ", ".join(task.dependencies) if task.dependencies else "—"
            print(f"    {name} → agent: {task.agent or '—'}, deps: [{deps}]")
        print()

    return 0


# ── Debug helpers ─────────────────────────────────────────────────────

def _dump_node(node: object, indent: int = 0):
    """Recursively print an AST node tree."""
    prefix = "  " * indent
    name = type(node).__name__

    if hasattr(node, "__dataclass_fields__"):
        print(f"{prefix}{name}:")
        for field_name in node.__dataclass_fields__:
            val = getattr(node, field_name)
            if isinstance(val, list) and val:
                print(f"{prefix}  {field_name}:")
                for item in val:
                    if hasattr(item, "__dataclass_fields__"):
                        _dump_node(item, indent + 2)
                    else:
                        print(f"{prefix}    {item!r}")
            elif hasattr(val, "__dataclass_fields__"):
                print(f"{prefix}  {field_name}:")
                _dump_node(val, indent + 2)
            else:
                print(f"{prefix}  {field_name}: {val!r}")
    else:
        print(f"{prefix}{name}: {node!r}")


if __name__ == "__main__":
    sys.exit(main())
