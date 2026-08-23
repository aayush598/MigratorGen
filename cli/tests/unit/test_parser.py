"""Tests for argument parser."""

from cli.cli.parser import build_parser


class TestBuildParser:
    def test_creates_parser(self):
        parser = build_parser()
        assert parser.prog == "migrator-gen"

    def test_version_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--version"])
        assert args.version is True

    def test_json_flag(self):
        parser = build_parser()
        args = parser.parse_args(["rules", "--rules", "x.json", "--json"])
        assert args.json is True

    def test_create_command(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "create",
                "--changelog",
                "changelog.json",
                "--library",
                "mylib",
            ]
        )
        assert args.command == "create"
        assert args.changelog == "changelog.json"
        assert args.library == "mylib"

    def test_migrate_command(self):
        parser = build_parser()
        args = parser.parse_args(["migrate", "src/", "--rules", "rules.json"])
        assert args.command == "migrate"
        assert args.path == "src/"
        assert args.rules == "rules.json"

    def test_migrate_with_dry_run(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "migrate",
                "file.py",
                "--rules",
                "r.json",
                "--dry-run",
            ]
        )
        assert args.dry_run is True

    def test_preview_command(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "preview",
                "file.py",
                "--rules",
                "rules.json",
            ]
        )
        assert args.command == "preview"

    def test_interactive_command(self):
        parser = build_parser()
        args = parser.parse_args(["interactive", "--output", "out.json"])
        assert args.command == "interactive"
        assert args.output == "out.json"

    def test_validate_rules_command(self):
        parser = build_parser()
        args = parser.parse_args(["validate-rules", "rules.json"])
        assert args.command == "validate-rules"
        assert args.file == "rules.json"

    def test_diff_rules_command(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "diff-rules",
                "--old",
                "a.json",
                "--new",
                "b.json",
            ]
        )
        assert args.command == "diff-rules"

    def test_audit_command(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "audit",
                "project/",
                "--rules",
                "rules.json",
            ]
        )
        assert args.command == "audit"

    def test_auto_upgrade_command(self):
        parser = build_parser()
        args = parser.parse_args(["auto-upgrade", "project/"])
        assert args.command == "auto-upgrade"

    def test_export_schema_command(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "export-schema",
                "--output",
                "schema.json",
            ]
        )
        assert args.command == "export-schema"

    def test_config_flag(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "rules",
                "--rules",
                "x.json",
                "--config",
                "config.toml",
            ]
        )
        assert args.config == "config.toml"

    def test_run_alias(self):
        parser = build_parser()
        args = parser.parse_args(["run", "file.py", "--rules", "r.json"])
        assert args.command == "run"

    def test_create_default_output(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "create",
                "--changelog",
                "c.json",
                "--library",
                "l",
            ]
        )
        assert args.output == "./generated_migrator"

    def test_export_schema_default_output(self):
        parser = build_parser()
        args = parser.parse_args(["export-schema"])
        assert args.output == "migration-schema.json"

    def test_invalid_command(self):
        import pytest

        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["invalid"])
