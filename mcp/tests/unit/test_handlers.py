"""Tests for MCP tool handlers."""

from __future__ import annotations

import json
from pathlib import Path

from migrator_gen import Rule

from migrator_gen_mcp.server.app import MigratorGenMCPServer


class TestToolHandlers:
    def setup_method(self):
        self.server = MigratorGenMCPServer()

    def test_list_libraries(self):
        result = self.server.call_tool("list_libraries", {})
        assert isinstance(result, str)

    def test_validate_rules(self, sample_rules_file: Path):
        result = self.server.call_tool("validate_rules", {"rules_file_path": str(sample_rules_file)})
        assert "PASSED" in result or "FAILED" in result

    def test_explain_breaking_changes(self):
        rule = {
            "id": "R-001",
            "change_type": "rename_function",
            "old_name": "connect",
            "new_name": "create_connection",
            "description": "Renamed for clarity",
            "version_introduced": "2.0.0",
            "safety": "review_required",
        }
        result = self.server.call_tool("explain_breaking_changes", {"rules": [rule]})
        assert "REVIEW NEEDED" in result
        assert "connect" in result

    def test_resolve_path_missing_params(self):
        result = self.server.call_tool("resolve_path", {})
        assert "Missing required parameters" in result or "Missing required field" in result

    def test_unknown_tool(self):
        result = self.server.call_tool("does_not_exist", {})
        assert "Unknown tool" in result

    def test_generate_rules_no_text(self):
        result = self.server.call_tool("generate_rules", {"mode": "changelog"})
        assert "No changelog text" in result

    def test_preview_migration_no_code(self):
        result = self.server.call_tool("preview_migration", {})
        assert "No source_code" in result or "Missing required field" in result

    def test_run_migration_no_code(self):
        result = self.server.call_tool("run_migration", {})
        assert "No source_code" in result or "Missing required field" in result

    def test_analyze_code(self):
        code = "import os\n\ndef hello(name):\n    return f'Hello, {name}'\n"
        result = self.server.call_tool("analyze_code", {"source_code": code})
        assert "Analysis" in result
        assert "hello" in result

    def test_get_tools(self):
        tools = self.server.get_tools()
        assert len(tools) == 10
        names = [t.name for t in tools]
        assert "generate_rules" in names
        assert "preview_migration" in names
        assert "run_migration" in names
        assert "validate_rules" in names
        assert "analyze_code" in names
        assert "suggest_migrations" in names
        assert "list_libraries" in names
        assert "explain_breaking_changes" in names
        assert "resolve_path" in names
        assert "create_migrator" in names

    def test_validate_required_fields(self):
        result = self.server.call_tool("run_migration", {"source_code": "x = 1"})
        assert "No source_code" not in result
