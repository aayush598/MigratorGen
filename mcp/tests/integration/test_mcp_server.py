"""Integration tests for MCP server — end-to-end workflow validation."""

from __future__ import annotations

from migrator_gen_mcp.server.app import MigratorGenMCPServer


class TestMCPIntegration:
    def setup_method(self):
        self.server = MigratorGenMCPServer()

    def test_end_to_end_migration(self):
        """Simulate: generate rules → preview → run → validate."""
        source = "from demo import connect\nc = connect()\n"
        rule = {
            "id": "W-001",
            "change_type": "rename_function",
            "old_name": "connect",
            "new_name": "create_connection",
            "description": "Renamed for clarity",
            "version_introduced": "2.0.0",
        }

        preview = self.server.call_tool(
            "preview_migration",
            {
                "source_code": source,
                "rules": [rule],
            },
        )
        assert "Preview:" in preview
        assert "create_connection" in preview

        result = self.server.call_tool(
            "run_migration",
            {
                "source_code": source,
                "rules": [rule],
            },
        )
        assert "Migration complete" in result
        assert "create_connection" in result

    def test_analyze_then_migrate(self):
        source = "import os\n\ndef get_path():\n    return os.getcwd()\n"
        analyze = self.server.call_tool("analyze_code", {"source_code": source})
        assert "get_path" in analyze
        assert "os" in analyze

    def test_explain_and_validate(self):
        rules = [
            {
                "id": "R-001",
                "change_type": "rename_function",
                "old_name": "old_func",
                "new_name": "new_func",
                "description": "Renamed for clarity",
                "version_introduced": "2.0.0",
                "safety": "risky",
            },
            {
                "id": "R-002",
                "change_type": "add_argument",
                "function_name": "setup",
                "argument_name": "verbose",
                "default_value": "False",
                "description": "Added verbose argument",
                "version_introduced": "2.0.0",
                "safety": "safe",
            },
        ]

        explanation = self.server.call_tool("explain_breaking_changes", {"rules": rules})
        assert "HIGH RISK" in explanation
        assert "SAFE" in explanation

    def test_list_and_describe(self):
        tools = self.server.get_tools()
        assert len(tools) == 10

        libraries = self.server.call_tool("list_libraries", {})
        assert isinstance(libraries, str)

    def test_resolve_path_endpoint(self):
        result = self.server.call_tool(
            "resolve_path",
            {
                "source_version": "1.0.0",
                "target_version": "2.0.0",
                "library_name": "test_lib",
            },
        )
        assert isinstance(result, str)
