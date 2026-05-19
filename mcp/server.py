"""MigratorGen MCP Server — Model Context Protocol for IDE and tool integration.

Tools
-----
- generate_rules          Generate migration rules from changelog / diff
- preview_migration       Dry-run a migration and return the diff
- run_migration           Apply migration rules to source code
- validate_rules          Validate migration rules from a file
- analyze_code            Extract imports / functions / classes from code
- suggest_migrations      Suggest applicable migrations for a codebase
- create_migrator         Generate a standalone pip-installable migrator package
- list_libraries          List libraries with available migration packs
- explain_breaking_changes  Explain breaking changes in a migration rule-set
- resolve_path            Resolve migration path between two versions
"""

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from migrator_gen import (
    MigrationClient,
    Rule,
)
from migrator_gen.exceptions import SDKError

log = logging.getLogger("migrator-gen.mcp")


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., str]


class MigratorGenMCPServer:
    """MCP server exposing all migration operations via SDK-backed tools."""

    def __init__(self) -> None:
        self.name = "migrator-gen"
        self.version = "0.1.0"
        self._client = MigrationClient(mode="local")
        self.tools: Dict[str, MCPTool] = {}
        self._register_tools()

    # ── Tool registry ────────────────────────────────────────────

    def _register_tools(self) -> None:
        self.tools["generate_rules"] = MCPTool(
            name="generate_rules",
            description="Generate migration rules from a changelog or by comparing old and new code.",
            input_schema={
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["changelog", "diff"], "default": "changelog"},
                    "changelog_text": {"type": "string", "description": "Changelog text (markdown)"},
                    "library_name": {"type": "string", "default": "unknown"},
                    "old_code": {"type": "string", "description": "Original source code"},
                    "new_code": {"type": "string", "description": "Updated source code"},
                },
            },
            handler=self._handle_generate_rules,
        )

        self.tools["preview_migration"] = MCPTool(
            name="preview_migration",
            description="Preview migration changes as a unified diff.",
            input_schema={
                "type": "object",
                "properties": {
                    "source_code": {"type": "string"},
                    "rules": {"type": "array", "items": {"type": "object"}},
                    "source_version": {"type": "string"},
                    "target_version": {"type": "string", "default": "latest"},
                },
                "required": ["source_code", "rules"],
            },
            handler=self._handle_preview_migration,
        )

        self.tools["run_migration"] = MCPTool(
            name="run_migration",
            description="Apply migration rules to source code.",
            input_schema={
                "type": "object",
                "properties": {
                    "source_code": {"type": "string"},
                    "rules": {"type": "array", "items": {"type": "object"}},
                    "dry_run": {"type": "boolean", "default": False},
                },
                "required": ["source_code", "rules"],
            },
            handler=self._handle_run_migration,
        )

        self.tools["validate_rules"] = MCPTool(
            name="validate_rules",
            description="Validate migration rules from a file.",
            input_schema={
                "type": "object",
                "properties": {
                    "rules_file_path": {"type": "string", "description": "Path to a rules JSON file"},
                },
                "required": ["rules_file_path"],
            },
            handler=self._handle_validate_rules,
        )

        self.tools["analyze_code"] = MCPTool(
            name="analyze_code",
            description="Analyse source code: extract imports, functions, classes.",
            input_schema={
                "type": "object",
                "properties": {
                    "source_code": {"type": "string"},
                },
                "required": ["source_code"],
            },
            handler=self._handle_analyze_code,
        )

        self.tools["suggest_migrations"] = MCPTool(
            name="suggest_migrations",
            description="Analyse a file and suggest migration packs that apply.",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "destination_library": {"type": "string"},
                },
                "required": ["file_path", "destination_library"],
            },
            handler=self._handle_suggest_migrations,
        )

        self.tools["list_libraries"] = MCPTool(
            name="list_libraries",
            description="List libraries with available migration packs.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_list_libraries,
        )

        self.tools["explain_breaking_changes"] = MCPTool(
            name="explain_breaking_changes",
            description="Explain breaking changes from a set of rules in human-readable terms.",
            input_schema={
                "type": "object",
                "properties": {
                    "rules": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["rules"],
            },
            handler=self._handle_explain_breaking_changes,
        )

        self.tools["resolve_path"] = MCPTool(
            name="resolve_path",
            description="Resolve the migration path between two versions of a library.",
            input_schema={
                "type": "object",
                "properties": {
                    "source_version": {"type": "string"},
                    "target_version": {"type": "string"},
                    "library_name": {"type": "string"},
                },
                "required": ["source_version", "target_version", "library_name"],
            },
            handler=self._handle_resolve_path,
        )

        self.tools["create_migrator"] = MCPTool(
            name="create_migrator",
            description="Generate a standalone pip-installable migrator package.",
            input_schema={
                "type": "object",
                "properties": {
                    "library_name": {"type": "string"},
                    "output_dir": {"type": "string", "default": "."},
                },
                "required": ["library_name"],
            },
            handler=self._handle_create_migrator,
        )

    # ── Handlers ─────────────────────────────────────────────────

    def _handle_generate_rules(self, **kwargs: Any) -> str:
        mode = kwargs.get("mode", "changelog")

        try:
            if mode == "changelog":
                text = kwargs.get("changelog_text", "")
                lib = kwargs.get("library_name", "unknown")
                result = self._client.generate_rules_from_changelog(text, lib)
                rules = result.rules
            else:
                old_code = kwargs.get("old_code", "")
                new_code = kwargs.get("new_code", "")
                rules = self._client.generate_rules_from_diff(old_code, new_code)
        except SDKError as e:
            return f"Error: {e}"

        if not rules:
            return "No migration rules could be generated from the input."

        lines = [f"Generated {len(rules)} migration rule(s):\n"]
        for r in rules:
            ct = r.change_type.value if hasattr(r.change_type, "value") else r.change_type
            lines.append(f"- [{ct}] {r.description}")
            if r.old_name and r.new_name:
                lines.append(f"  {r.old_name} -> {r.new_name}")

        rules_json = json.dumps([r.to_dict() for r in rules], indent=2)
        lines.append(f"\n[JSON_RULES]\n{rules_json}\n[/JSON_RULES]")
        return "\n".join(lines)

    def _handle_preview_migration(self, **kwargs: Any) -> str:
        source_code = kwargs.get("source_code", "")
        rules_data = kwargs.get("rules", [])
        source_version = kwargs.get("source_version", "1.0.0")
        target_version = kwargs.get("target_version", "latest")

        rules = self._parse_rules(rules_data)
        if isinstance(rules, str):
            return rules

        try:
            preview = self._client.preview_migration(source_code, rules)
        except SDKError as e:
            return f"Error: {e}"

        parts = [f"Preview: {source_version} -> {target_version}"]
        parts.append(f"Changes: {preview.change_count}, Confidence: {preview.average_confidence:.0%}")
        parts.append(f"\n--- Diff ---\n{preview.diff}")
        return "\n".join(parts)

    def _handle_run_migration(self, **kwargs: Any) -> str:
        source_code = kwargs.get("source_code", "")
        rules_data = kwargs.get("rules", [])
        dry_run = kwargs.get("dry_run", False)

        rules = self._parse_rules(rules_data)
        if isinstance(rules, str):
            return rules

        try:
            result = self._client.migrate_code(source_code, rules, dry_run=dry_run)
        except SDKError as e:
            return f"Error: {e}"

        if not result.was_modified:
            return "No changes were needed."

        lines = [f"Migration complete ({len(result.changes)} change(s))"]
        for c in result.changes:
            lines.append(f"+ {c}")

        if not dry_run:
            lines.append(f"\n--- Migrated Code ---\n{result.transformed_code}")

        return "\n".join(lines)

    def _handle_validate_rules(self, **kwargs: Any) -> str:
        rules_file = kwargs.get("rules_file_path", "")

        if not rules_file or not Path(rules_file).exists():
            return f"File not found: {rules_file}"

        try:
            report = self._client.validate_rules(rules_file)
        except SDKError as e:
            return f"Validation error: {e}"

        lines = [f"Validation {'PASSED' if report.valid else 'FAILED'}"]
        lines.append(f"Errors: {report.error_count}, Warnings: {report.warning_count}, Info: {report.info_count}")
        for e in report.errors:
            lines.append(f"[ERROR] [{e.rule_id}] {e.message}")
        for w in report.warnings:
            lines.append(f"[WARNING] [{w.rule_id}] {w.message}")

        return "\n".join(lines)

    def _handle_analyze_code(self, **kwargs: Any) -> str:
        source_code = kwargs.get("source_code", "")

        # Use suggest_migrations as a proxy for analysis
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        try:
            tmp.write(source_code)
            tmp.close()
            analysis = self._client.suggest_migrations(tmp.name, "unknown")
        except Exception as exc:
            return f"Analysis error: {exc}"
        finally:
            Path(tmp.name).unlink(missing_ok=True)

        lines = ["Analysis of source code:\n"]
        if analysis.imports:
            lines.append(f"Imports ({len(analysis.imports)}):")
            for imp in analysis.imports[:30]:
                tag = f"from {imp.module} import {imp.name}" if imp.module else f"import {imp.name}"
                lines.append(f"  {tag}")
        if analysis.functions:
            lines.append(f"\nFunctions ({len(analysis.functions)}):")
            for fn in analysis.functions[:20]:
                params = ", ".join(fn.params)
                lines.append(f"  def {fn.name}({params})")
        if analysis.classes:
            lines.append(f"\nClasses ({len(analysis.classes)}):")
            for cls in analysis.classes:
                lines.append(f"  class {cls.name}")

        return "\n".join(lines)

    def _handle_suggest_migrations(self, **kwargs: Any) -> str:
        file_path = kwargs.get("file_path", "")
        dest_lib = kwargs.get("destination_library", "")

        if not file_path or not Path(file_path).exists():
            return f"File not found: {file_path}"

        try:
            analysis = self._client.suggest_migrations(file_path, dest_lib)
        except SDKError as e:
            return f"Error: {e}"

        if not analysis.suggested_migrations:
            return f"No known migrations detected for '{dest_lib}' in {file_path}."

        lines = [f"Detected {len(analysis.suggested_migrations)} potential migration(s):\n"]
        for s in analysis.suggested_migrations:
            lines.append(f"- {s}")
        return "\n".join(lines)

    def _handle_list_libraries(self, **kwargs: Any) -> str:
        try:
            libraries = self._client.list_libraries()
        except SDKError as e:
            return f"Error: {e}"

        if not libraries:
            return "No migration packs found."

        lines = ["Libraries with migration packs:\n"]
        for name, info in libraries.items():
            lines.append(f"- **{name}**: {info.get('rule_count', 0)} rules (v{info.get('version', '?')})")
        return "\n".join(lines)

    def _handle_explain_breaking_changes(self, **kwargs: Any) -> str:
        rules_data = kwargs.get("rules", [])
        rules = self._parse_rules(rules_data)
        if isinstance(rules, str):
            return rules

        risky: List[str] = []
        review: List[str] = []
        safe: List[str] = []

        for r in rules:
            ct = r.change_type.value if hasattr(r.change_type, "value") else r.change_type
            entry = f"- [{ct}] {r.description}"
            if r.old_name and r.new_name:
                entry += f" ({r.old_name} -> {r.new_name})"
            elif r.old_name:
                entry += f" (removing: {r.old_name})"

            safety = r.safety.value if hasattr(r.safety, "value") else r.safety
            if safety == "risky":
                risky.append(entry)
            elif safety == "review_required":
                review.append(entry)
            else:
                safe.append(entry)

        lines = ["Breaking Changes Analysis:\n"]
        if risky:
            lines.append(f"[HIGH RISK] {len(risky)} change(s):")
            lines.extend(f"  {e}" for e in risky)
        if review:
            lines.append(f"\n[REVIEW NEEDED] {len(review)} change(s):")
            lines.extend(f"  {e}" for e in review)
        lines.append(f"\n[SAFE] {len(safe)} non-breaking change(s)")
        return "\n".join(lines)

    def _handle_resolve_path(self, **kwargs: Any) -> str:
        src = kwargs.get("source_version", "")
        tgt = kwargs.get("target_version", "")
        lib = kwargs.get("library_name", "")

        if not src or not tgt or not lib:
            return "Missing required parameters: source_version, target_version, library_name"

        try:
            path = self._client.resolve_path(src, tgt, lib)
        except SDKError as e:
            return f"Error: {e}"

        direction = "upgrade" if path.is_upgrade else "downgrade"
        lines = [f"Migration path: {src} -> {tgt} ({direction})"]
        lines.append(f"Steps: {len(path.steps)}, Rules: {path.rule_count}\n")
        for s in path.steps:
            lines.append(f"  {s.source} -> {s.target}")
        return "\n".join(lines)

    def _handle_create_migrator(self, **kwargs: Any) -> str:
        lib = kwargs.get("library_name", "")
        out_dir = kwargs.get("output_dir", ".")

        if not lib:
            return "Missing required parameter: library_name"

        try:
            out_path = self._client.generate_migrator_package(lib, out_dir)
            return (
                f"Migrator package created for '{lib}'!\n"
                f"Output: {out_path}\n\n"
                f"Install: pip install -e {out_path}\n"
                f"Run: python -m {out_path.name} list-versions"
            )
        except SDKError as e:
            return f"Error: {e}"

    # ── Utilities ────────────────────────────────────────────────

    def _parse_rules(self, data: List[Dict[str, Any]]) -> Any:
        try:
            return [Rule.from_dict(r) for r in data]
        except Exception as e:
            return f"Error parsing rules: {e}"

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        tool = self.tools.get(name)
        if not tool:
            available = ", ".join(self.tools)
            return f"Unknown tool: {name}. Available: {available}"
        try:
            return tool.handler(**arguments)
        except Exception as e:
            log.exception("Tool call failed: %s", name)
            return f"Error calling {name}: {type(e).__name__}: {e}"

    def get_tools(self) -> List[MCPTool]:
        return list(self.tools.values())


# ── Transport: stdio ─────────────────────────────────────────────


def run_stdio_server() -> None:
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
    except ImportError:
        print("[ERROR] MCP library not installed. Install: pip install mcp", file=sys.stderr)
        sys.exit(1)

    server = Server("migrator-gen")
    mcp_server = MigratorGenMCPServer()

    @server.list_tools()
    async def list_tools():
        return [
            Tool(name=t.name, description=t.description, inputSchema=t.input_schema)
            for t in mcp_server.get_tools()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]):
        result = mcp_server.call_tool(name, arguments)
        return [TextContent(type="text", text=result)]

    import asyncio

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(main())


# ── Transport: HTTP ──────────────────────────────────────────────


def run_http_server(host: str = "0.0.0.0", port: int = 8001) -> None:
    try:
        import uvicorn
        from fastapi import FastAPI
    except ImportError:
        print("[ERROR] fastapi/uvicorn not installed. Install: pip install fastapi uvicorn", file=sys.stderr)
        sys.exit(1)

    mcp_server = MigratorGenMCPServer()

    app = FastAPI(title="MigratorGen MCP HTTP")

    @app.get("/tools")
    async def list_tools():
        return [
            {"name": t.name, "description": t.description, "inputSchema": t.input_schema}
            for t in mcp_server.get_tools()
        ]

    @app.post("/tools/{tool_name}/call")
    async def call_tool(tool_name: str, arguments: Dict[str, Any] = {}):
        return {"result": mcp_server.call_tool(tool_name, arguments)}

    uvicorn.run(app, host=host, port=port)


# ── Entry point ──────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="MigratorGen MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.transport == "stdio":
        run_stdio_server()
    else:
        run_http_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
