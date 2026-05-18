"""
MigratorGen MCP Server - Model Context Protocol server for AI agent and IDE integration.

Exposes migration tools to:
- Claude Desktop
- Cursor
- VSCode Copilot agents
- OpenAI agents
- Any MCP-compatible AI tool

Tools exposed:
- generate_rules       - Generate migration rules from changelog/diff
- preview_migration   - Preview what a migration would do
- run_migration       - Apply migration to code
- validate_rules      - Validate migration rules
- analyze_code        - Analyze code for API patterns
- suggest_migrations - Suggest migrations for a codebase
- create_migrator     - Create a standalone migrator package
- list_migrations    - List available migrations for a library
- explain_breaking   - Explain breaking changes
"""

import sys
import json
import os
import tempfile
import shutil
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.changelog_parser import ChangelogParser, MigrationRule, ChangeType, VersionChangelog, MigrationFile
from core.version_resolver import VersionResolver, MigrationPath
from core.migration_engine import TransactionalMigrationEngine
from core.migrator_generator import MigratorGenerator
from core.validation import RuleValidator, ValidationReport, RuleDependencyGraph, IdempotencyChecker
from core.diff_analyzer import generate_from_git_diff, generate_from_changelog, export_rules, GitDiffAnalyzer
from core.symbol_resolver import SymbolResolver, ImportGraph


MCPServer = None
MCP_AVAILABLE = False


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable


@dataclass
class MCPServerInstance:
    name: str
    version: str
    tools: List[MCPTool] = field(default_factory=list)

    def add_tool(self, name: str, description: str, input_schema: Dict, handler: Callable):
        self.tools.append(MCPTool(name=name, description=description, input_schema=input_schema, handler=handler))


class MigratorGenMCPServer:
    """MCP Server for MigratorGen - exposes migration tools to AI agents."""

    def __init__(self):
        self.name = "migratorgen"
        self.version = "0.1.0"
        self.tools: Dict[str, MCPTool] = {}
        self._register_tools()

    def _register_tools(self):
        self.tools["generate_rules"] = MCPTool(
            name="generate_rules",
            description="Generate migration rules from a changelog file or git diff. "
                       "Provide either changelog_text (for markdown/text changelog) or "
                       "old_code + new_code (for AST-based diff analysis).",
            input_schema={
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["changelog", "diff"], "default": "changelog"},
                    "changelog_text": {"type": "string", "description": "Changelog text (markdown or plain)"},
                    "old_code": {"type": "string", "description": "Old version source code"},
                    "new_code": {"type": "string", "description": "New version source code"},
                    "version": {"type": "string", "default": "X.Y.Z"},
                    "module": {"type": "string", "default": ""},
                },
                "required": [],
            },
            handler=self._handle_generate_rules,
        )

        self.tools["preview_migration"] = MCPTool(
            name="preview_migration",
            description="Preview what a migration would do to source code without modifying it. "
                       "Returns a unified diff showing all changes.",
            input_schema={
                "type": "object",
                "properties": {
                    "source_code": {"type": "string", "description": "Source code to migrate"},
                    "rules": {"type": "array", "description": "Migration rules (array of rule objects)"},
                    "source_version": {"type": "string"},
                    "target_version": {"type": "string", "default": "latest"},
                },
                "required": ["source_code", "rules"],
            },
            handler=self._handle_preview_migration,
        )

        self.tools["run_migration"] = MCPTool(
            name="run_migration",
            description="Apply migration rules to source code. Returns the migrated code.",
            input_schema={
                "type": "object",
                "properties": {
                    "source_code": {"type": "string"},
                    "rules": {"type": "array"},
                    "dry_run": {"type": "boolean", "default": False},
                    "transactional": {"type": "boolean", "default": True},
                },
                "required": ["source_code", "rules"],
            },
            handler=self._handle_run_migration,
        )

        self.tools["validate_rules"] = MCPTool(
            name="validate_rules",
            description="Validate migration rules for correctness and conflicts.",
            input_schema={
                "type": "object",
                "properties": {
                    "rules": {"type": "array", "description": "Array of migration rule objects"},
                },
                "required": ["rules"],
            },
            handler=self._handle_validate_rules,
        )

        self.tools["analyze_code"] = MCPTool(
            name="analyze_code",
            description="Analyze source code and extract API information: imports, functions, classes, decorators.",
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
            description="Scan a directory of Python files and suggest which migrations are needed based on imports.",
            input_schema={
                "type": "object",
                "properties": {
                    "code_snippets": {"type": "array", "description": "Array of {filename, content} objects"},
                    "detect_frameworks": {"type": "boolean", "default": True},
                },
                "required": ["code_snippets"],
            },
            handler=self._handle_suggest_migrations,
        )

        self.tools["create_migrator"] = MCPTool(
            name="create_migrator",
            description="Create a standalone pip-installable migrator package from rules.",
            input_schema={
                "type": "object",
                "properties": {
                    "rules": {"type": "array"},
                    "library": {"type": "string"},
                    "package_name": {"type": "string"},
                    "output_dir": {"type": "string", "default": "./generated_migrator"},
                },
                "required": ["rules", "library"],
            },
            handler=self._handle_create_migrator,
        )

        self.tools["list_mibraries"] = MCPTool(
            name="list_libraries",
            description="List all libraries with available migration packs.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_list_libraries,
        )

        self.tools["explain_breaking_changes"] = MCPTool(
            name="explain_breaking_changes",
            description="Explain breaking changes in a migration in human-readable terms.",
            input_schema={
                "type": "object",
                "properties": {
                    "rules": {"type": "array"},
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
                    "changelog_json": {"type": "object"},
                    "source_version": {"type": "string"},
                    "target_version": {"type": "string"},
                },
                "required": ["changelog_json", "source_version", "target_version"],
            },
            handler=self._handle_resolve_path,
        )

    def _handle_generate_rules(self, **kwargs) -> str:
        mode = kwargs.get("mode", "changelog")

        if mode == "changelog":
            text = kwargs.get("changelog_text", "")
            version = kwargs.get("version", "X.Y.Z")
            rules = generate_from_changelog(text, version)
        else:
            old_code = kwargs.get("old_code", "")
            new_code = kwargs.get("new_code", "")
            module = kwargs.get("module", "")
            rules = generate_from_git_diff(old_code, new_code, module)

        if not rules:
            return "No migration rules could be generated from the input."

        output = f"Generated {len(rules)} migration rule(s):\n\n"
        for r in rules:
            ct = r.get("change_type", "unknown")
            desc = r.get("description", "No description")
            output += f"- [{ct}] {desc}\n"
            if r.get("old_name"):
                output += f"  old_name: {r['old_name']}\n"
            if r.get("new_name"):
                output += f"  new_name: {r['new_name']}\n"
            if r.get("function_name"):
                output += f"  function: {r['function_name']}\n"
            if r.get("source_module"):
                output += f"  module: {r['source_module']} -> {r.get('target_module', 'N/A')}\n"

        output += f"\n[JSON_RULES]\n{json.dumps(rules, indent=2)}\n[/JSON_RULES]"
        return output

    def _handle_preview_migration(self, **kwargs) -> str:
        source_code = kwargs.get("source_code", "")
        rules_data = kwargs.get("rules", [])
        source_version = kwargs.get("source_version", "1.0.0")
        target_version = kwargs.get("target_version", "latest")

        try:
            rules = [MigrationRule.from_dict(r) for r in rules_data]
        except Exception as e:
            return f"Error parsing rules: {e}"

        engine = TransactionalMigrationEngine(interactive_approval=False)
        preview = engine.preview_migration(source_code, rules)

        result = engine.migrate_code(source_code, rules, dry_run=False)
        conf = result.average_confidence

        risky = [r for r in result.rule_results if r.safety.value == "risky" if hasattr(r.safety, 'value')]
        review = [r for r in result.rule_results if r.safety.value == "review_required" if hasattr(r.safety, 'value')]

        summary = f"Preview: {source_version} -> {target_version}\n"
        summary += f"Changes: {len(result.changes)}, Confidence: {conf:.0%}\n"

        if risky:
            summary += f"\n[WARNING] {len(risky)} risky change(s) - manual review strongly recommended:\n"
            for r in risky:
                summary += f"  - {r.rule_description}\n"
        if review:
            summary += f"\n[CAUTION] {len(review)} change(s) require review:\n"
            for r in review:
                summary += f"  - {r.rule_description}\n"

        summary += f"\n--- Diff ---\n{preview}"
        return summary

    def _handle_run_migration(self, **kwargs) -> str:
        source_code = kwargs.get("source_code", "")
        rules_data = kwargs.get("rules", [])
        dry_run = kwargs.get("dry_run", False)
        transactional = kwargs.get("transactional", True)

        try:
            rules = [MigrationRule.from_dict(r) for r in rules_data]
        except Exception as e:
            return f"Error parsing rules: {e}"

        engine = TransactionalMigrationEngine(
            transactional=transactional,
            interactive_approval=False,
        )
        result = engine.migrate_code(source_code, rules, dry_run=dry_run)

        if not result.was_modified:
            return "No changes were needed."

        output = f"Migration complete ({len(result.changes)} change(s))\n"
        for c in result.changes:
            output += f"+ {c}\n"

        if dry_run:
            output += "\n[DRY RUN] No files were modified."
        else:
            output += f"\n--- Migrated Code ---\n{result.transformed_code}"

        return output

    def _handle_validate_rules(self, **kwargs) -> str:
        rules_data = kwargs.get("rules", [])

        try:
            rules = [MigrationRule.from_dict(r) for r in rules_data]
        except Exception as e:
            return f"Error parsing rules: {e}"

        report = RuleValidator().validate_rules(rules)

        output = f"Validation {'PASSED' if report.valid else 'FAILED'}\n"
        output += f"Errors: {len(report.errors)}, Warnings: {len(report.warnings)}, Info: {len(report.info)}\n"

        for e in report.errors:
            output += f"[ERROR] [{e.rule_id}] {e.message}\n"
        for w in report.warnings:
            output += f"[WARNING] [{w.rule_id}] {w.message}\n"
        for i in report.info:
            output += f"[INFO] [{i.rule_id}] {i.message}\n"

        return output

    def _handle_analyze_code(self, **kwargs) -> str:
        source_code = kwargs.get("source_code", "")
        resolver = SymbolResolver(source_code)

        imports = []
        functions = []
        classes = []

        for node in resolver._tree.body:
            if isinstance(node, cst.SimpleStatementLine):
                stmt = node.body[0] if node.body else None
                if isinstance(stmt, cst.ImportFrom):
                    module = ""
                    if stmt.module:
                        if isinstance(stmt.module, cst.Name):
                            module = stmt.module.value
                    if isinstance(stmt.names, cst.ImportStar):
                        imports.append(f"from {module} import *")
                    else:
                        for alias in stmt.names:
                            name = alias.name.value if isinstance(alias.name, cst.Name) else ""
                            imports.append(f"from {module} import {name}")
                elif isinstance(stmt, cst.Import):
                    for alias in stmt.names:
                        imports.append(f"import {alias.name.value}")
            elif isinstance(node, cst.FunctionDef):
                params = [p.name.value for p in node.params.params]
                functions.append(f"def {node.name.value}({', '.join(params)})")
            elif isinstance(node, cst.ClassDef):
                classes.append(f"class {node.name.value}")

        output = f"Analysis of source code:\n\n"
        if imports:
            output += f"Imports ({len(imports)}):\n"
            for i in imports[:30]:
                output += f"  {i}\n"
            if len(imports) > 30:
                output += f"  ... and {len(imports) - 30} more\n"
        if functions:
            output += f"\nFunctions ({len(functions)}):\n"
            for f in functions[:20]:
                output += f"  {f}\n"
            if len(functions) > 20:
                output += f"  ... and {len(functions) - 20} more\n"
        if classes:
            output += f"\nClasses ({len(classes)}):\n"
            for c in classes:
                output += f"  {c}\n"

        return output

    def _handle_suggest_migrations(self, **kwargs) -> str:
        snippets = kwargs.get("code_snippets", [])
        detect_frameworks = kwargs.get("detect_frameworks", True)

        all_imports = set()
        for snippet in snippets:
            content = snippet.get("content", "")
            filename = snippet.get("filename", "unknown")
            for match in re.findall(r'^from\s+([a-zA-Z_][a-zA-Z0-9_.]+)\s+import', content, re.MULTILINE):
                all_imports.add(match.split(".")[0])
            for match in re.findall(r'^import\s+([a-zA-Z_][a-zA-Z0-9_.]+)', content, re.MULTILINE):
                all_imports.add(match.split(".")[0])

        framework_map = {
            "pydantic": {"pydantic": "Pydantic V1 to V2 migration", "deprecated": False},
            "fastapi": {"fastapi": "FastAPI version migrations"},
            "httpx": {"httpx": "HTTPX version migrations"},
            "sqlalchemy": {"sqlalchemy": "SQLAlchemy version migrations"},
            "django": {"django": "Django version migrations"},
            "numpy": {"numpy": "NumPy version migrations"},
            "pandas": {"pandas": "Pandas version migrations"},
            "requests": {"requests": "Requests version migrations"},
            "flask": {"flask": "Flask version migrations"},
            "attrs": {"attrs": "Attrs version migrations"},
            "dataclasses": {"dataclasses": "stdlib migrations"},
        }

        suggestions = []
        for lib in all_imports:
            if lib in framework_map:
                suggestions.append(f"- **{lib}**: {framework_map[lib]}")

        if not suggestions:
            return "No known library migrations detected in the codebase."

        output = f"Detected {len(suggestions)} potential migration(s) needed:\n\n"
        output += "\n".join(suggestions)
        output += "\n\nUse /rules/generate-from-diff to create migration rules for any library."

        return output

    def _handle_create_migrator(self, **kwargs) -> str:
        rules_data = kwargs.get("rules", [])
        library = kwargs.get("library", "unknown")
        package_name = kwargs.get("package_name")
        output_dir = Path(kwargs.get("output_dir", "./generated_migrator"))

        try:
            changelogs = []
            rules_by_version: Dict[str, List] = {}
            for r in rules_data:
                v = r.get("version_introduced", "X.Y.Z")
                if v not in rules_by_version:
                    rules_by_version[v] = []
                rules_by_version[v].append(MigrationRule.from_dict(r))

            for v, rules in rules_by_version.items():
                changelogs.append(VersionChangelog(version=v, rules=rules))

            generator = MigratorGenerator(library_name=library, package_name=package_name)
            generator.generate(changelogs, output_dir)

            return (
                f"Migrator package created successfully!\n"
                f"Output: {output_dir}\n"
                f"Package: {generator.package_name}\n"
                f"Rules: {len(rules_data)}\n\n"
                f"Install: pip install -e {output_dir}\n"
                f"Run: python -m {generator.package_name} list-versions"
            )
        except Exception as e:
            return f"Error creating migrator: {e}"

    def _handle_list_libraries(self, **kwargs) -> str:
        known = [
            ("pydantic", "Pydantic V1 to V2"),
            ("fastapi", "FastAPI version migrations"),
            ("httpx", "HTTPX version migrations"),
            ("sqlalchemy", "SQLAlchemy version migrations"),
            ("django", "Django version migrations"),
            ("numpy", "NumPy version migrations"),
            ("pandas", "Pandas version migrations"),
            ("requests", "Requests version migrations"),
            ("flask", "Flask version migrations"),
            ("attrs", "Attrs version migrations"),
        ]

        output = "Libraries with migration packs:\n\n"
        for lib, desc in known:
            output += f"- **{lib}**: {desc}\n"

        output += "\nUse /rules/generate-from-diff to create rules for any library."
        return output

    def _handle_explain_breaking_changes(self, **kwargs) -> str:
        rules_data = kwargs.get("rules", [])

        breaking_categories = {
            "risky": [],
            "review": [],
            "safe": [],
        }

        for r_data in rules_data:
            safety = r_data.get("safety", "safe")
            ct = r_data.get("change_type", "unknown")
            desc = r_data.get("description", "No description")
            old_name = r_data.get("old_name", "")
            new_name = r_data.get("new_name", "")
            function = r_data.get("function_name", "")

            entry = f"- [{ct}] {desc}"
            if old_name and new_name:
                entry += f" ({old_name} -> {new_name})"
            elif old_name:
                entry += f" (removing: {old_name})"

            if safety == "risky":
                breaking_categories["risky"].append(entry)
            elif safety == "review_required":
                breaking_categories["review"].append(entry)
            else:
                breaking_categories["safe"].append(entry)

        output = "Breaking Changes Analysis:\n\n"

        if breaking_categories["risky"]:
            output += f"[HIGH RISK] {len(breaking_categories['risky'])} change(s) that may break code:\n"
            for entry in breaking_categories["risky"]:
                output += f"  {entry}\n"
            output += "\n"

        if breaking_categories["review"]:
            output += f"[REVIEW NEEDED] {len(breaking_categories['review'])} change(s):\n"
            for entry in breaking_categories["review"]:
                output += f"  {entry}\n"
            output += "\n"

        output += f"[SAFE] {len(breaking_categories['safe'])} non-breaking change(s)"
        return output

    def _handle_resolve_path(self, **kwargs) -> str:
        changelog_json = kwargs.get("changelog_json", {})
        source_version = kwargs.get("source_version", "1.0.0")
        target_version = kwargs.get("target_version", "latest")

        try:
            mf = MigrationFile(**changelog_json)
            changelogs = mf.versions
        except Exception:
            changelogs = []
            for item in changelog_json.get("versions", []):
                changelogs.append(VersionChangelog(**item))

        resolver = VersionResolver(changelogs)
        path = resolver.resolve_path(source_version, target_version)

        direction = "upgrade" if path.is_upgrade else "downgrade"
        output = f"Migration path: {source_version} -> {target_version} ({direction})\n"
        output += f"Steps: {len(path.steps)}, Rules: {len(path.rules)}\n\n"

        for step in path.steps:
            output += f"  v{step[0]} -> v{step[1]}\n"

        return output

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        if name not in self.tools:
            return f"Unknown tool: {name}. Available tools: {', '.join(self.tools.keys())}"

        tool = self.tools[name]
        try:
            return tool.handler(**arguments)
        except Exception as e:
            return f"Error calling {name}: {type(e).__name__}: {e}"

    def get_tools(self) -> List[MCPTool]:
        return list(self.tools.values())


def run_stdio_server():
    """Run the MCP server using stdio transport."""
    if not MCP_AVAILABLE:
        print("[ERROR] MCP library not installed. Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)

    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

    server = Server("migratorgen")

    mcp_server = MigratorGenMCPServer()

    @server.list_tools()
    async def list_tools():
        tools = []
        for tool in mcp_server.get_tools():
            tools.append(Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.input_schema,
            ))
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]):
        result = mcp_server.call_tool(name, arguments)
        return [TextContent(type="text", text=result)]

    import asyncio

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(main())


def run_http_server():
    """Run the MCP server as an HTTP endpoint (alternative transport)."""
    import uvicorn
    from fastapi import FastAPI
    from pydantic import BaseModel

    mcp_server = MigratorGenMCPServer()

    app = FastAPI(title="MigratorGen MCP HTTP")

    @app.get("/tools")
    async def list_tools():
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
            }
            for t in mcp_server.get_tools()
        ]

    @app.post("/tools/{tool_name}/call")
    async def call_tool(tool_name: str, arguments: Dict[str, Any] = {}):
        result = mcp_server.call_tool(tool_name, arguments)
        return {"result": result}

    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MigratorGen MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)

    args = parser.parse_args()

    if args.transport == "stdio":
        run_stdio_server()
    else:
        run_http_server()