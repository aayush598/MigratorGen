"""Argument parser — defines all CLI commands and flags."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrator-gen",
        description="Automated Python code migration infrastructure for library maintainers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  migrator-gen run path/to/file.py --rules rules.json\n"
            "  migrator-gen preview file.py --rules rules.json --json\n"
            "  migrator-gen rules --rules rules.json\n"
            "  migrator-gen interactive\n"
        ),
    )
    parser.add_argument("--config", help="Path to TOML config file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--version", action="store_true", help="Show version and exit")

    sub = parser.add_subparsers(dest="command")

    def _add(name: str, **kw: object) -> argparse.ArgumentParser:
        p = sub.add_parser(name, **kw)
        p.add_argument("--config", help="Path to TOML config file")
        p.add_argument("--json", action="store_true", help="Output as JSON")
        return p

    # ── create ──
    p = _add("create", help="Create migrator package from changelog")
    p.add_argument("--changelog", required=True, help="Path to changelog file")
    p.add_argument("--library", required=True, help="Library name")
    p.add_argument(
        "--output",
        default="./generated_migrator",
        help="Output directory (default: ./generated_migrator)",
    )

    # ── update ──
    p = _add("update", help="Update existing migrator with new changelog")
    p.add_argument("--existing", required=True, help="Path to existing migration_rules.json")
    p.add_argument("--new-changelog", required=True, help="Path to new changelog")
    p.add_argument("--output", help="Output directory (default: same as existing)")
    p.add_argument("--library", help="Library name override")

    # ── migrate / run ──
    p = _add("migrate", aliases=["run"], help="Run migration on a file or directory")
    p.add_argument("path", help="File or directory to migrate")
    p.add_argument("--rules", required=True, help="Path to migration_rules.json")
    p.add_argument("--from", dest="from_version", default="1.0.0")
    p.add_argument("--to", dest="to_version", default="latest")
    p.add_argument("--dry-run", action="store_true", help="Preview only, no file changes")

    # ── preview ──
    p = _add("preview", help="Preview migration diff")
    p.add_argument("file", help="Python file to preview")
    p.add_argument("--rules", required=True, help="Path to migration_rules.json")
    p.add_argument("--from", dest="from_version", default="1.0.0")
    p.add_argument("--to", dest="to_version", default="latest")

    # ── rules ──
    p = _add("rules", help="List rules from a rules file")
    p.add_argument("--rules", required=True, help="Path to migration_rules.json")

    # ── interactive ──
    p = _add("interactive", help="Interactive rule builder (guided prompts)")
    p.add_argument("--output", help="Output file for rules (default: rules_<version>.json)")

    # ── export-schema ──
    p = _add("export-schema", help="Export JSON schema for MigrationFile model")
    p.add_argument(
        "--output",
        default="migration-schema.json",
        help="Output file path (default: migration-schema.json)",
    )

    # ── validate-rules ──
    p = _add("validate-rules", help="Validate a rules file for correctness")
    p.add_argument("file", help="JSON rules file to validate")

    # ── diff-rules ──
    p = _add("diff-rules", help="Show diff between two rule sets")
    p.add_argument("--old", required=True, help="Old rules file")
    p.add_argument("--new", required=True, help="New rules file")

    # ── audit ──
    p = _add("audit", help="Audit migration status of a project")
    p.add_argument("directory", help="Project directory to scan")
    p.add_argument("--rules", required=True, help="Migration rules file")

    # ── auto-upgrade ──
    p = _add("auto-upgrade", help="Auto-detect dependencies and suggest migrations")
    p.add_argument("directory", help="Project directory")
    p.add_argument("--to", dest="to_version", default="latest", help="Target version")

    return parser
