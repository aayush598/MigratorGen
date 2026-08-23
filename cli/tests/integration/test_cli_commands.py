"""Integration tests for CLI commands (requires SDK + libcst installed)."""

from __future__ import annotations

import json
from pathlib import Path

from cli.cli.app import main

SAMPLE_CHANGELOG = json.dumps(
    {
        "library": "testlib",
        "versions": [
            {
                "version": "2.0.0",
                "release_date": "2025-01-01",
                "rules": [
                    {
                        "id": "T-001",
                        "change_type": "rename_function",
                        "description": "connect → create_connection",
                        "old_name": "connect",
                        "new_name": "create_connection",
                        "version_introduced": "2.0.0",
                    }
                ],
            }
        ],
    }
)


class TestMainDispatch:
    def test_version_flag(self, capsys):
        try:
            main(["--version"])
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "migrator-gen" in captured.out

    def test_export_schema(self, tmp_path: Path, capsys):
        out = tmp_path / "schema.json"
        main(["export-schema", "--output", str(out)])
        assert out.exists()
        schema = json.loads(out.read_text())
        assert "properties" in schema

    def test_no_command_shows_help(self, capsys):
        try:
            main([])
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "usage:" in captured.out

    def test_nonexistent_file_error(self, capsys):
        try:
            main(["preview", "/nonexistent/file.py", "--rules", "/nonexistent/rules.json"])
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "not found" in captured.out
