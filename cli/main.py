"""MigratorGen CLI — command-line interface for the migration platform.

Usage
-----
.. code-block:: bash

    migrator-gen --help
    migrator-gen --version
    migrator-gen run path/to/file.py --rules rules.json
    migrator-gen preview path/to/file.py --rules rules.json --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from migrator_gen import (
    ChangeType,
    MigrationClient,
    MigrationFile,
    Rule,
    SafetyLevel,
    SDKConfig,
    VersionChangelog,
)
from migrator_gen.exceptions import SDKError

try:
    from rich.console import Console
    from rich.table import Table
    from rich.syntax import Syntax
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import print as rprint
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False


_STDLIB_MODULES = {
    "sys", "os", "re", "json", "math", "time", "datetime",
    "pathlib", "typing", "dataclasses", "collections", "functools",
    "itertools", "abc", "enum", "hashlib", "uuid", "io", "base64",
    "textwrap", "string", "random", "statistics", "bisect",
}


# ── Console helpers ───────────────────────────────────────────────

_console = Console() if _HAS_RICH else None


def _client(args: argparse.Namespace) -> MigrationClient:
    kwargs: Dict[str, Any] = {"mode": "local"}
    if getattr(args, "config", None):
        kwargs["config_path"] = args.config
    return MigrationClient(**kwargs)


def _info(msg: str, json_out: bool = False) -> None:
    if json_out:
        return
    if _HAS_RICH:
        _console.print(f"[blue]*[/blue] {msg}")
    else:
        print(f"[INFO] {msg}")


def _ok(msg: str, json_out: bool = False) -> None:
    if json_out:
        return
    if _HAS_RICH:
        _console.print(f"[green]+[/green] {msg}")
    else:
        print(f"[SUCCESS] {msg}")


def _warn(msg: str, json_out: bool = False) -> None:
    if json_out:
        return
    if _HAS_RICH:
        _console.print(f"[yellow]![/yellow] {msg}")
    else:
        print(f"[WARNING] {msg}")


def _err(msg: str, code: int = 1) -> None:
    if _HAS_RICH:
        _console.print(f"[red]-[/red] {msg}")
    else:
        print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def _is_json(args: argparse.Namespace) -> bool:
    return getattr(args, "json", False)


def _read_rules_file(path: Path) -> List[VersionChangelog]:
    client = MigrationClient(mode="local")
    mf = client.parse_changelog(str(path))
    return mf.versions if mf else []


def _all_rules(path: Path) -> List[Rule]:
    versions = _read_rules_file(path)
    return [r for v in versions for r in v.rules]


def _library_name(path: Path) -> str:
    try:
        client = MigrationClient(mode="local")
        mf = client.parse_changelog(str(path))
        return mf.library
    except Exception:
        return "unknown"


# ── Commands ──────────────────────────────────────────────────────


def cmd_create(args: argparse.Namespace) -> None:
    j = _is_json(args)
    changelog_path = Path(args.changelog)
    output_dir = Path(args.output)

    if not changelog_path.exists():
        _err(f"Changelog file not found: {changelog_path}")

    _info(f"Reading changelog: {changelog_path}", j)
    client = _client(args)

    try:
        mf = client.parse_changelog(str(changelog_path))
    except SDKError as e:
        _err(f"Failed to parse changelog: {e}")

    _info(f"Found {len(mf.versions)} version(s) for library: {mf.library}", j)
    total_rules = sum(len(v.rules) for v in mf.versions)
    _info(f"Total migration rules: {total_rules}", j)

    _info("Creating migrator package ...", j)
    out_path = client.generate_migrator_package(mf.library, str(output_dir))

    if j:
        print(json.dumps({"library": mf.library, "versions": len(mf.versions),
                          "rules": total_rules, "output": out_path}))
    else:
        _ok(f"Migrator created at: {out_path}")


def cmd_update(args: argparse.Namespace) -> None:
    j = _is_json(args)
    old_rules_path = Path(args.existing)
    new_changelog_path = Path(args.new_changelog)

    for p, label in [(old_rules_path, "Existing rules"), (new_changelog_path, "New changelog")]:
        if not p.exists():
            _err(f"{label} not found: {p}")

    client = _client(args)

    _info("Loading existing migration rules ...", j)
    old_mf = client.parse_changelog(str(old_rules_path))
    new_mf = client.parse_changelog(str(new_changelog_path))

    existing_versions = {vc.version for vc in old_mf.versions}
    merged = [vc for vc in new_mf.versions if vc.version not in existing_versions]

    if not merged:
        if j:
            print(json.dumps({"status": "no_changes"}))
        else:
            _info("No new versions found. Nothing to update.")
        return

    all_versions = old_mf.versions + merged
    library = args.library or old_mf.library or "unknown"
    output_dir = Path(args.output) if args.output else old_rules_path.parent

    _info("Regenerating migrator package ...", j)
    out_path = client.generate_migrator_package(library, str(output_dir))

    if j:
        print(json.dumps({"new_versions": len(merged), "output": str(out_path)}))
    else:
        _ok(f"Migrator updated! Added {len(merged)} version(s)")
        _info(f"Output: {out_path}")


def cmd_migrate(args: argparse.Namespace) -> None:
    """Run migration on a file or directory."""
    j = _is_json(args)
    source_path = Path(args.path)
    if not source_path.exists():
        _err(f"Source path not found: {source_path}")

    rules_path = Path(args.rules)
    if not rules_path.exists():
        _err(f"Rules file not found: {rules_path}")

    client = _client(args)

    _info("Loading migration rules ...", j)
    versions = client.parse_changelog(str(rules_path)).versions
    rules = [r for v in versions for r in v.rules]
    _info(f"Loaded {len(rules)} rule(s) across {len(versions)} version(s)", j)

    if j:
        results = []
        for f in ([source_path] if source_path.is_file() else list(source_path.rglob("*.py"))):
            try:
                code = f.read_text(encoding="utf-8")
                res = client.migrate_code(code, rules)
                results.append({
                    "file": str(f),
                    "modified": res.was_modified,
                    "changes": res.changes,
                    "errors": res.errors,
                })
            except Exception as exc:
                results.append({"file": str(f), "modified": False, "changes": [], "errors": [str(exc)]})
        print(json.dumps({"files": results, "dry_run": args.dry_run}))
        return

    if source_path.is_file():
        code = source_path.read_text(encoding="utf-8")
        result = client.migrate_code(code, rules, dry_run=args.dry_run)
        if result.was_modified:
            if not args.dry_run:
                backup = source_path.with_suffix(source_path.suffix + ".bak")
                source_path.rename(backup)
                source_path.write_text(result.transformed_code, encoding="utf-8")
                _ok(f"Modified: {source_path} (backup: {backup})")
            else:
                _info(f"Would modify: {source_path}")
            for c in result.changes:
                print(f"   - {c}")
        else:
            _info("No changes needed.")
        if result.errors:
            for e in result.errors:
                _warn(e)
    else:
        files_modified = 0
        files_failed = 0
        for f in source_path.rglob("*.py"):
            try:
                code = f.read_text(encoding="utf-8")
                res = client.migrate_code(code, rules, dry_run=args.dry_run)
                if res.was_modified:
                    files_modified += 1
                    if not args.dry_run:
                        backup = f.with_suffix(f.suffix + ".bak")
                        f.rename(backup)
                        f.write_text(res.transformed_code, encoding="utf-8")
                if res.errors:
                    files_failed += 1
            except Exception as exc:
                files_failed += 1
                _warn(f"Failed {f}: {exc}")

        _info(f"Processed: modified={files_modified}, failed={files_failed}")

    if args.dry_run:
        _info("Dry run — no files were modified.")


def cmd_preview(args: argparse.Namespace) -> None:
    j = _is_json(args)
    source_path = Path(args.file)
    if not source_path.exists():
        _err(f"File not found: {source_path}")

    rules_path = Path(args.rules)
    if not rules_path.exists():
        _err(f"Rules file not found: {rules_path}")

    client = _client(args)
    source_code = source_path.read_text(encoding="utf-8")
    rules = _all_rules(rules_path)

    preview = client.preview_migration(source_code, rules)

    if j:
        print(preview.model_dump_json(indent=2))
    elif _HAS_RICH:
        _console.print(Syntax(preview.diff or "(no diff)", "diff"))
    else:
        print(preview.diff or "(no diff)")


def cmd_rules(args: argparse.Namespace) -> None:
    j = _is_json(args)
    rules_path = Path(args.rules)
    if not rules_path.exists():
        _err(f"Rules file not found: {rules_path}")

    client = _client(args)
    mf = client.parse_changelog(str(rules_path))

    if j:
        print(mf.model_dump_json(indent=2))
        return

    if _HAS_RICH:
        _console.print(f"\n[bold]Library:[/bold] {mf.library}")
        for vc in mf.versions:
            date = vc.release_date or ""
            _console.print(f"\n[bold cyan]v{vc.version}[/bold cyan]  {f'({date})' if date else ''}  — {len(vc.rules)} rule(s)")
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID", style="dim")
            table.add_column("Type")
            table.add_column("Action")
            table.add_column("Safety")
            for rule in vc.rules:
                ct = rule.change_type.value if hasattr(rule.change_type, "value") else rule.change_type
                old = rule.old_name or ""
                new = rule.new_name or ""
                action = f"{old} → {new}" if old and new else rule.description
                table.add_row(rule.id, ct, action, rule.safety)
            _console.print(table)
    else:
        _print_rule_versions_plain(mf)


def _print_rule_versions_plain(mf: MigrationFile) -> None:
    print(f"\n[LIBRARY] {mf.library}")
    print("=" * 50)
    for vc in mf.versions:
        date = vc.release_date or ""
        print(f"\n  v{vc.version}  {f'({date})' if date else ''}  — {len(vc.rules)} rule(s)")
        for rule in vc.rules:
            ct = rule.change_type.value if hasattr(rule.change_type, "value") else rule.change_type
            old = rule.old_name or ""
            new = rule.new_name or ""
            rename = f" [{old} -> {new}]" if old and new else ""
            print(f"    [{rule.id}] [{ct}]{rename} {rule.description}")


def cmd_interactive(args: argparse.Namespace) -> None:
    if _HAS_RICH:
        _console.print("\n[bold]Interactive Rule Builder[/bold]")
    else:
        print("\n[INTERACTIVE] Rule Builder")
    print("=" * 40)

    rules: List[Rule] = []
    version = input("Version (e.g. 2.0.0): ").strip()
    counter = 1

    while True:
        print("\nChange types:")
        for i, ct in enumerate(ChangeType, 1):
            print(f"  {i}. {ct.value}")
        print("  0. Done")

        choice = input("\nSelect change type (number): ").strip()
        if choice == "0":
            break

        try:
            idx = int(choice) - 1
            change_type = list(ChangeType)[idx]
        except (ValueError, IndexError):
            print("Invalid choice, try again.")
            continue

        data: Dict[str, Any] = {
            "id": f"RULE-{counter:03d}",
            "change_type": change_type.value,
            "version_introduced": version,
            "description": input("Description: ").strip(),
        }

        rename_types = {
            ChangeType.RENAME_FUNCTION, ChangeType.RENAME_CLASS,
            ChangeType.RENAME_ATTRIBUTE, ChangeType.REPLACE_WITH_PROPERTY,
            ChangeType.RENAME_PARAMETER,
        }
        if change_type in rename_types:
            data["old_name"] = input("Old name: ").strip()
            data["new_name"] = input("New name: ").strip()
        elif change_type == ChangeType.RENAME_IMPORT:
            data["old_name"] = input("Old symbol: ").strip()
            data["new_name"] = input("New symbol: ").strip()
            data["old_module"] = input("Old module: ").strip()
            data["new_module"] = input("New module: ").strip()
        elif change_type in (ChangeType.ADD_ARGUMENT, ChangeType.REMOVE_ARGUMENT):
            data["function_name"] = input("Function name: ").strip()
            data["argument_name"] = input("Argument name: ").strip()
            if change_type == ChangeType.ADD_ARGUMENT:
                data["default_value"] = input("Default value: ").strip()
        elif change_type == ChangeType.CHANGE_ARGUMENT_DEFAULT:
            data["argument_name"] = input("Argument name: ").strip()
            data["default_value"] = input("Default value: ").strip()
        elif change_type == ChangeType.REORDER_ARGUMENTS:
            data["function_name"] = input("Function name: ").strip()
            data["new_order"] = [x.strip() for x in input("New order (comma sep): ").split(",")]
        elif change_type == ChangeType.MOVE_TO_MODULE:
            data["old_name"] = input("Symbol: ").strip()
            data["source_module"] = input("Source module: ").strip()
            data["target_module"] = input("Target module: ").strip()
        elif change_type == ChangeType.DEPRECATE_FUNCTION:
            data["old_name"] = input("Function name: ").strip()
            data["replacement"] = input("Replacement (or Enter): ").strip() or None
        elif change_type in (ChangeType.ADD_DECORATOR, ChangeType.REMOVE_DECORATOR):
            data["function_name"] = input("Function name: ").strip()
            data["decorator_name"] = input("Decorator (without @): ").strip()
        elif change_type in (ChangeType.RENAME_ARGUMENT,):
            data["function_name"] = input("Function name: ").strip()
            data["argument_name"] = input("Old argument name: ").strip()
            data["new_argument_name"] = input("New argument name: ").strip()
        elif change_type in (ChangeType.REMOVE_FUNCTION, ChangeType.REMOVE_CLASS):
            data["old_name"] = input("Symbol name: ").strip()

        try:
            rule = Rule(**data)
            rules.append(rule)
            print(f"  [OK] Rule added: {rule.change_type} ({rule.id})")
            counter += 1
        except Exception as e:
            print(f"  [ERROR] Invalid rule: {e}")

    if not rules:
        print("No rules created.")
        return

    output = Path(args.output or f"rules_{version}.json")
    lib = input("\nLibrary name: ").strip()
    mf = MigrationFile(
        library=lib,
        versions=[VersionChangelog(version=version, rules=rules)],
    )
    output.write_text(mf.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")
    _ok(f"Saved {len(rules)} rule(s) to {output}")


def cmd_export_schema(args: argparse.Namespace) -> None:
    schema = MigrationFile.model_json_schema()
    output_path = Path(args.output) if args.output else Path("migration-schema.json")
    output_path.write_text(json.dumps(schema, indent=2))
    _ok(f"Schema exported to {output_path}")


def cmd_validate_rules(args: argparse.Namespace) -> None:
    j = _is_json(args)
    path = Path(args.file)
    if not path.exists():
        _err(f"File not found: {path}")

    client = _client(args)
    _info(f"Validating {path} ...", j)

    try:
        mf = client.parse_changelog(str(path))
    except SDKError as e:
        _err(f"Parse error: {e}")

    all_rules = [r for v in mf.versions for r in v.rules]
    report = client.validate_rules(str(path))

    if j:
        print(report.model_dump_json(indent=2))
        return

    if report.valid:
        _ok("All rules are valid.")
    else:
        _console.print(f"[red]-[/red] {len(report.errors)} error(s):") if _HAS_RICH else print(f"[ERROR] {len(report.errors)} error(s):")
        for e in report.errors:
            print(f"  - [{e.rule_id}] {e.message}")

    if report.warnings:
        print(f"\n[WARNINGS] {len(report.warnings)}:")
        for w in report.warnings:
            print(f"  - [{w.rule_id}] {w.message}")

    if report.info:
        print(f"\n[INFO] {len(report.info)}:")
        for i in report.info:
            print(f"  - [{i.rule_id}] {i.message}")

    if not report.valid:
        sys.exit(1)


def cmd_diff_rules(args: argparse.Namespace) -> None:
    j = _is_json(args)
    old_path, new_path = Path(args.old), Path(args.new)
    for p, label in [(old_path, "Old"), (new_path, "New")]:
        if not p.exists():
            _err(f"{label} rules file not found: {p}")

    old_rules = _rules_by_id(old_path)
    new_rules = _rules_by_id(new_path)

    added = set(new_rules) - set(old_rules)
    removed = set(old_rules) - set(new_rules)
    modified = []

    for rid in set(new_rules) & set(old_rules):
        o, n = old_rules[rid], new_rules[rid]
        changes = []
        for field in ["old_name", "new_name", "function_name", "argument_name",
                       "old_module", "new_module", "safety", "priority"]:
            ov = getattr(o, field, None)
            nv = getattr(n, field, None)
            if ov != nv:
                changes.append(f"  {field}: {ov} -> {nv}")
        if changes:
            modified.append((rid, changes))

    if j:
        print(json.dumps({
            "added": list(added),
            "removed": list(removed),
            "modified": [{"id": rid, "changes": ch} for rid, ch in modified],
        }))
        return

    if added:
        print(f"[+ADDED] {len(added)} rule(s):")
        for rid in sorted(added):
            r = new_rules[rid]
            print(f"  + {rid}: [{r.change_type}] {r.description}")
    if removed:
        print(f"\n[-REMOVED] {len(removed)} rule(s):")
        for rid in sorted(removed):
            r = old_rules[rid]
            print(f"  - {rid}: [{r.change_type}] {r.description}")
    if modified:
        print(f"\n[~MODIFIED] {len(modified)} rule(s):")
        for rid, changes in modified:
            print(f"  ~ {rid}:")
            for c in changes:
                print(c)
    if not added and not removed and not modified:
        _info("No differences found.")


def _rules_by_id(path: Path) -> Dict[str, Rule]:
    client = MigrationClient(mode="local")
    mf = client.parse_changelog(str(path))
    return {r.id: r for v in mf.versions for r in v.rules}


def cmd_audit(args: argparse.Namespace) -> None:
    j = _is_json(args)
    directory = Path(args.directory)
    if not directory.exists():
        _err(f"Directory not found: {directory}")

    rules_path = Path(args.rules) if args.rules else None
    if not rules_path or not rules_path.exists():
        _err("--rules is required for audit")

    client = _client(args)
    mf = client.parse_changelog(str(rules_path))
    available = [v.version for v in mf.versions]

    py_files = list(directory.rglob("*.py"))
    pattern = re.compile(r'["\']?(\d+\.\d+\.\d+)["\']?')

    if j:
        results = []
        for f in py_files:
            content = f.read_text(encoding="utf-8", errors="ignore")
            found = pattern.findall(content)
            if found:
                results.append({"file": str(f), "versions": sorted(set(found))})
        print(json.dumps({
            "directory": str(directory),
            "available_versions": available,
            "file_count": len(py_files),
            "version_references": results,
        }))
        return

    print(f"\n[AUDIT] Scanning: {directory}")
    print(f"   Rules: {rules_path}")
    print(f"   Available versions: {', '.join(available)}")
    print(f"   Python files: {len(py_files)}\n")

    for f in py_files[:20]:
        content = f.read_text(encoding="utf-8", errors="ignore")
        found = pattern.findall(content)
        if found:
            print(f"  {f.relative_to(directory)}: mentions {set(found)}")

    if len(py_files) > 20:
        print(f"  ... and {len(py_files) - 20} more files")


def cmd_auto_upgrade(args: argparse.Namespace) -> None:
    j = _is_json(args)
    directory = Path(args.directory)
    if not directory.exists():
        _err(f"Directory not found: {directory}")

    if j:
        info: Dict[str, Any] = {"directory": str(directory)}
        req_file = directory / "requirements.txt"
        pyproject_file = directory / "pyproject.toml"

        if req_file.exists():
            deps = [d.strip() for d in req_file.read_text().splitlines()
                    if d.strip() and not d.startswith("#")]
            info["type"] = "requirements.txt"
            info["dependencies"] = deps
        elif pyproject_file.exists():
            matches = re.findall(r'["\']?([a-zA-Z0-9_-]+)\s*[<>=!]+', pyproject_file.read_text())
            info["type"] = "pyproject.toml"
            info["dependencies"] = matches
        else:
            info["type"] = "scan"
            imports_found = _scan_imports(directory)
            info["imports"] = sorted(imports_found)
        print(json.dumps(info))
        return

    print(f"\n[AUTO-UPGRADE] Analyzing: {directory}")

    req_file = directory / "requirements.txt"
    pyproject_file = directory / "pyproject.toml"

    if req_file.exists():
        print("\n[INFO] Found requirements.txt")
        deps = [d.strip() for d in req_file.read_text().splitlines()
                if d.strip() and not d.startswith("#")]
        for dep in deps:
            print(f"   - {dep}")
    elif pyproject_file.exists():
        print("\n[INFO] Found pyproject.toml")
        matches = re.findall(r'["\']?([a-zA-Z0-9_-]+)\s*[<>=!]+', pyproject_file.read_text())
        for dep in matches:
            print(f"   - {dep}")
    else:
        print("\n[INFO] Scanning Python files for imports ...")
        imports_found = _scan_imports(directory)
        for imp in sorted(imports_found)[:20]:
            print(f"   - {imp}")
        if len(imports_found) > 20:
            print(f"   ... and {len(imports_found) - 20} more")


def _scan_imports(directory: Path) -> set:
    imports_found: set = set()
    for f in directory.rglob("*.py"):
        content = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'^import\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.MULTILINE):
            base = m.group(1).split(".")[0]
            if base not in _STDLIB_MODULES:
                imports_found.add(base)
        for m in re.finditer(r'^from\s+([a-zA-Z_][a-zA-Z0-9_.]+)\s+import', content, re.MULTILINE):
            base = m.group(1).split(".")[0]
            if base not in _STDLIB_MODULES:
                imports_found.add(base)
    return imports_found


# ── Parser ────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrator-gen",
        description="Migration infrastructure for library maintainers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--config", help="Path to TOML config file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--version", action="store_true", help="Show version and exit")

    sub = parser.add_subparsers(dest="command")

    # create
    p = sub.add_parser("create", help="Create migrator from changelog")
    p.add_argument("--changelog", required=True, help="Path to changelog file")
    p.add_argument("--library", required=True, help="Library name")
    p.add_argument("--output", default="./generated_migrator", help="Output directory")

    # update
    p = sub.add_parser("update", help="Update existing migrator")
    p.add_argument("--existing", required=True, help="Path to existing migration_rules.json")
    p.add_argument("--new-changelog", required=True, help="Path to new changelog")
    p.add_argument("--output", help="Output directory (default: same as existing)")
    p.add_argument("--library", help="Library name override")

    # migrate
    p = sub.add_parser("migrate", aliases=["run"], help="Run migration on code")
    p.add_argument("path", help="File or directory to migrate")
    p.add_argument("--rules", required=True, help="Path to migration_rules.json")
    p.add_argument("--from", dest="from_version", default="1.0.0")
    p.add_argument("--to", dest="to_version", default="latest")
    p.add_argument("--dry-run", action="store_true", help="Preview only, no file changes")

    # preview
    p = sub.add_parser("preview", help="Preview migration changes")
    p.add_argument("file", help="Python file to preview")
    p.add_argument("--rules", required=True)
    p.add_argument("--from", dest="from_version", default="1.0.0")
    p.add_argument("--to", dest="to_version", default="latest")

    # rules
    p = sub.add_parser("rules", help="List migration rules")
    p.add_argument("--rules", required=True)

    # interactive
    p = sub.add_parser("interactive", help="Interactive rule builder")
    p.add_argument("--output", help="Output file for rules")

    # export-schema
    p = sub.add_parser("export-schema", help="Export JSON schema for rules")
    p.add_argument("--output", help="Output file path")

    # validate-rules
    p = sub.add_parser("validate-rules", help="Validate a rules file")
    p.add_argument("file", help="JSON rules file to validate")

    # diff-rules
    p = sub.add_parser("diff-rules", help="Show diff between two rule sets")
    p.add_argument("--old", required=True, help="Old rules file")
    p.add_argument("--new", required=True, help="New rules file")

    # audit
    p = sub.add_parser("audit", help="Audit migration status of a project")
    p.add_argument("directory", help="Project directory to audit")
    p.add_argument("--rules", required=True, help="Migration rules file")

    # auto-upgrade
    p = sub.add_parser("auto-upgrade", help="Auto-detect and run migrations")
    p.add_argument("directory", help="Project directory")
    p.add_argument("--to", dest="to_version", default="latest", help="Target version")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if getattr(args, "version", False):
        from migrator_gen import __version__
        print(f"migrator-gen {__version__}")
        return

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "create": cmd_create,
        "update": cmd_update,
        "migrate": cmd_migrate,
        "run": cmd_migrate,
        "preview": cmd_preview,
        "rules": cmd_rules,
        "interactive": cmd_interactive,
        "export-schema": cmd_export_schema,
        "validate-rules": cmd_validate_rules,
        "diff-rules": cmd_diff_rules,
        "audit": cmd_audit,
        "auto-upgrade": cmd_auto_upgrade,
    }

    try:
        commands[args.command](args)
    except SDKError as e:
        _err(str(e))
    except KeyboardInterrupt:
        if _HAS_RICH:
            _console.print("\n[yellow]Aborted.[/yellow]")
        else:
            print("\nAborted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
