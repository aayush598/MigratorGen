"""Workflow integration tests — real migration with libcst."""

from __future__ import annotations

import json
from pathlib import Path

from cli.cli.app import main


def _write_rules(path: Path) -> None:
    data = {
        "library": "demo",
        "versions": [
            {
                "version": "2.0.0",
                "release_date": "2025-01-01",
                "rules": [
                    {
                        "id": "W-001",
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
    path.write_text(json.dumps(data, indent=2))


def _write_source(path: Path) -> None:
    path.write_text("from demo import connect\nc = connect()\n")


class TestMigrateWorkflow:
    def test_migrate_file(self, tmp_path: Path, capsys):
        rules_file = tmp_path / "rules.json"
        source_file = tmp_path / "src" / "app.py"
        source_file.parent.mkdir(parents=True)
        _write_rules(rules_file)
        _write_source(source_file)

        main(["migrate", str(source_file), "--rules", str(rules_file)])
        captured = capsys.readouterr()
        assert "Modified" in captured.out

        # Verify backup
        backup = source_file.with_suffix(".py.bak")
        assert backup.exists()

        # Verify migration content
        content = source_file.read_text()
        assert "create_connection" in content
        import re
        assert not re.search(r'\bconnect\b', content)

    def test_migrate_dry_run(self, tmp_path: Path, capsys):
        rules_file = tmp_path / "rules.json"
        source_file = tmp_path / "app.py"
        _write_rules(rules_file)
        _write_source(source_file)

        main(["migrate", str(source_file), "--rules", str(rules_file), "--dry-run"])
        captured = capsys.readouterr()
        assert "Would modify" in captured.out

        # File should NOT have changed
        content = source_file.read_text()
        assert "connect" in content

    def test_migrate_directory(self, tmp_path: Path, capsys):
        rules_file = tmp_path / "rules.json"
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        _write_rules(rules_file)
        _write_source(src_dir / "a.py")
        _write_source(src_dir / "b.py")

        main(["migrate", str(src_dir), "--rules", str(rules_file)])
        captured = capsys.readouterr()
        assert "modified=" in captured.out

    def test_preview(self, tmp_path: Path, capsys):
        rules_file = tmp_path / "rules.json"
        source_file = tmp_path / "app.py"
        _write_rules(rules_file)
        _write_source(source_file)

        main(["preview", str(source_file), "--rules", str(rules_file)])
        captured = capsys.readouterr()
        assert "diff" in captured.out.lower() or "rename" in captured.out or "create_connection" in captured.out

    def test_rules_list(self, tmp_path: Path, capsys):
        rules_file = tmp_path / "rules.json"
        _write_rules(rules_file)

        main(["rules", "--rules", str(rules_file)])
        captured = capsys.readouterr()
        assert "testlib" in captured.out or "W-001" in captured.out or "demo" in captured.out

    def test_validate_rules(self, tmp_path: Path, capsys):
        rules_file = tmp_path / "rules.json"
        _write_rules(rules_file)

        main(["validate-rules", str(rules_file)])
        captured = capsys.readouterr()
        assert "valid" in captured.out.lower()

    def test_diff_rules(self, tmp_path: Path, capsys):
        old = tmp_path / "old.json"
        new = tmp_path / "new.json"
        _write_rules(old)
        new.write_text(
            json.dumps({
                "library": "demo",
                "versions": [
                    {
                        "version": "2.0.0",
                        "rules": [
                            {
                                "id": "W-001",
                                "change_type": "rename_class",
                                "description": "OldC → NewC",
                                "old_name": "OldC",
                                "new_name": "NewC",
                                "version_introduced": "2.0.0",
                            }
                        ],
                    }
                ],
            })
        )

        main(["diff-rules", "--old", str(old), "--new", str(new)])
        captured = capsys.readouterr()
        assert "REMOVED" in captured.out or "MODIFIED" in captured.out

    def test_json_output(self, tmp_path: Path, capsys):
        rules_file = tmp_path / "rules.json"
        _write_rules(rules_file)

        main(["rules", "--rules", str(rules_file), "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "library" in data
