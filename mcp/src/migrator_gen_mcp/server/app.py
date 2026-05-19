"""MCP Server — main app class, tool registration, and CLI entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from migrator_gen import SyncMigrationClient
from migrator_gen.exceptions import SDKError

from ..config import MCPSettings, load_settings, merge_settings
from ..config.settings import MCPSettings as _MCPSettings
from ..transport import run_http_server, run_stdio_server
from .handlers import ToolHandlers
from .tools import MCPTool, ToolRegistry

log = logging.getLogger("migrator-gen.mcp")


class MigratorGenMCPServer:
    """MCP server exposing all migration operations via SDK-backed tools."""

    def __init__(self, settings: _MCPSettings | None = None) -> None:
        self.name = "migrator-gen"
        self.version = "0.2.0"
        self.settings = settings or MCPSettings()
        self._client = SyncMigrationClient(mode="local")
        self._handlers = ToolHandlers(self._client)
        self._registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self) -> None:
        self._registry.register(MCPTool(
            name="generate_rules",
            description="Generate migration rules from a changelog or by comparing old and new code.",
            categories=["generation"],
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
            handler=self._handlers.generate_rules,
        ))
        self._registry.register(MCPTool(
            name="preview_migration",
            description="Preview migration changes as a unified diff.",
            categories=["migration"],
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
            handler=self._handlers.preview_migration,
        ))
        self._registry.register(MCPTool(
            name="run_migration",
            description="Apply migration rules to source code.",
            categories=["migration"],
            input_schema={
                "type": "object",
                "properties": {
                    "source_code": {"type": "string"},
                    "rules": {"type": "array", "items": {"type": "object"}},
                    "dry_run": {"type": "boolean", "default": False},
                },
                "required": ["source_code", "rules"],
            },
            handler=self._handlers.run_migration,
        ))
        self._registry.register(MCPTool(
            name="validate_rules",
            description="Validate migration rules from a file.",
            categories=["validation"],
            input_schema={
                "type": "object",
                "properties": {
                    "rules_file_path": {"type": "string", "description": "Path to a rules JSON file"},
                },
                "required": ["rules_file_path"],
            },
            handler=self._handlers.validate_rules,
        ))
        self._registry.register(MCPTool(
            name="analyze_code",
            description="Analyse source code: extract imports, functions, classes.",
            categories=["analysis"],
            input_schema={
                "type": "object",
                "properties": {
                    "source_code": {"type": "string"},
                },
                "required": ["source_code"],
            },
            handler=self._handlers.analyze_code,
        ))
        self._registry.register(MCPTool(
            name="suggest_migrations",
            description="Analyse a file and suggest migration packs that apply.",
            categories=["analysis"],
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "destination_library": {"type": "string"},
                },
                "required": ["file_path", "destination_library"],
            },
            handler=self._handlers.suggest_migrations,
        ))
        self._registry.register(MCPTool(
            name="list_libraries",
            description="List libraries with available migration packs.",
            categories=["discovery"],
            input_schema={"type": "object", "properties": {}},
            handler=self._handlers.list_libraries,
        ))
        self._registry.register(MCPTool(
            name="explain_breaking_changes",
            description="Explain breaking changes from a set of rules in human-readable terms.",
            categories=["analysis"],
            input_schema={
                "type": "object",
                "properties": {
                    "rules": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["rules"],
            },
            handler=self._handlers.explain_breaking_changes,
        ))
        self._registry.register(MCPTool(
            name="resolve_path",
            description="Resolve the migration path between two versions of a library.",
            categories=["migration"],
            input_schema={
                "type": "object",
                "properties": {
                    "source_version": {"type": "string"},
                    "target_version": {"type": "string"},
                    "library_name": {"type": "string"},
                },
                "required": ["source_version", "target_version", "library_name"],
            },
            handler=self._handlers.resolve_path,
        ))
        self._registry.register(MCPTool(
            name="create_migrator",
            description="Generate a standalone pip-installable migrator package.",
            categories=["generation"],
            input_schema={
                "type": "object",
                "properties": {
                    "library_name": {"type": "string"},
                    "output_dir": {"type": "string", "default": "."},
                },
                "required": ["library_name"],
            },
            handler=self._handlers.create_migrator,
        ))

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self._registry.get(name)
        if not tool:
            available = ", ".join(self._registry.names())
            return f"Unknown tool: {name}. Available: {available}"

        try:
            if self.settings.request_validation:
                self._validate_input(tool, arguments)
            return tool.handler(**arguments)
        except SDKError as e:
            log.exception("SDK error calling tool %s", name)
            return f"SDK Error: {e}"
        except Exception as e:
            log.exception("Tool call failed: %s", name)
            return f"Error calling {name}: {type(e).__name__}: {e}"

    def get_tools(self) -> list[MCPTool]:
        return self._registry.all()

    def _validate_input(self, tool: MCPTool, arguments: dict[str, Any]) -> None:
        schema = tool.input_schema
        required = schema.get("required", [])
        for field in required:
            if field not in arguments or arguments[field] is None:
                raise ValueError(f"Missing required field: {field}")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for migrator-gen-mcp."""
    parser = argparse.ArgumentParser(description="MigratorGen MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--config", help="Path to TOML config file")
    parser.add_argument("--version", action="store_true", help="Show version")
    args = parser.parse_args(argv)

    if args.version:
        from ..version import __version__
        print(f"migrator-gen-mcp {__version__}")
        return

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    settings = load_settings(args.config) if args.config else MCPSettings()
    settings = merge_settings(settings, {
        "host": args.host,
        "port": args.port,
        "transport": args.transport,
        "log_level": args.log_level,
    })

    log.info("Starting MCP server (transport=%s, host=%s, port=%d)", settings.transport, settings.host, settings.port)

    if settings.transport == "stdio":
        run_stdio_server()
    else:
        run_http_server(settings=settings)


if __name__ == "__main__":
    main()
