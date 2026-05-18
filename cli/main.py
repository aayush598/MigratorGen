"""
MigratorGen CLI - Main command-line interface for the migration platform.

Commands:
  create          Create a new migrator from a changelog file
  update          Update an existing migrator with a new changelog
  run             Run a migration on code
  preview         Preview what would change without modifying files
  rules           List/inspect migration rules
  interactive     Interactive rule builder
  export-schema   Export JSON schema for migration rules
  validate-rules  Validate a migration rules JSON file
  diff-rules      Show diff between two rule sets
  audit           Audit migration status of a project
  auto-upgrade    Auto-detect and run migrations
"""

import argparse
import json
import sys
import re
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, ROOT)

from core.changelog_parser import ChangelogParser, VersionChangelog, MigrationRule, ChangeType, MigrationFile, RuleWhenCondition
from core.version_resolver import VersionResolver
from core.migration_engine import TransactionalMigrationEngine
from core.migrator_generator import MigratorGenerator
from core.validation import RuleValidator, ValidationReport, RuleDependencyGraph, IdempotencyChecker
from core.symbol_resolver import ImportGraph
from pydantic import ValidationError


def cmd_create(args):
    """Create a new migrator package from a changelog file."""
    changelog_path = Path(args.changelog)
    output_dir = Path(args.output)
    library_name = args.library

    if not changelog_path.exists():
        print(f"[ERROR] Changelog file not found: {changelog_path}")
        sys.exit(1)

    print(f"[INFO] Reading changelog: {changelog_path}")
    content = changelog_path.read_text(encoding="utf-8")

    parser = ChangelogParser()
    try:
        changelogs = parser.parse(content, fmt="json")
    except ValidationError as e:
        print(f"[ERROR] Validation failed for {changelog_path}:")
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            print(f"  - {loc}: {error['msg']}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to parse {changelog_path}: {e}")
        sys.exit(1)

    print(f"   Found {len(changelogs)} version(s)")

    total_rules = sum(len(vc.rules) for vc in changelogs)
    print(f"\n[INFO] Total migration rules: {total_rules}")

    print(f"\n[GENERATING] Creating migrator package...")
    generator = MigratorGenerator(library_name=library_name)
    generator.generate(changelogs, output_dir)

    print(f"\n[SUCCESS] Done! Your migrator is at: {output_dir}")


def cmd_update(args):
    """Update an existing migrator with a new changelog."""
    old_rules_path = Path(args.existing)
    new_changelog_path = Path(args.new_changelog)

    if not old_rules_path.exists():
        print(f"[ERROR] Existing rules file not found: {old_rules_path}")
        sys.exit(1)

    print(f"[INFO] Loading existing migration rules: {old_rules_path}")
    parser = ChangelogParser()
    try:
        old_changelogs = parser.parse(old_rules_path.read_text(encoding="utf-8"), fmt="json")
    except Exception as e:
        print(f"[ERROR] Failed to parse existing rules: {e}")
        sys.exit(1)

    print(f"   {len(old_changelogs)} existing version(s)")

    print(f"\n[INFO] Reading new changelog: {new_changelog_path}")
    try:
        new_changelogs = parser.parse(new_changelog_path.read_text(encoding="utf-8"), fmt="json")
    except Exception as e:
        print(f"[ERROR] Failed to parse new changelog: {e}")
        sys.exit(1)

    merged = parser.merge_changelogs(old_changelogs, new_changelogs)
    print(f"   {len(merged)} new version(s) detected")

    if not merged:
        print("   No new versions found. Nothing to update.")
        return

    all_changelogs = old_changelogs + merged

    try:
        old_data = json.loads(old_rules_path.read_text(encoding="utf-8"))
        library_name = old_data.get("library", args.library or "unknown")
    except:
        library_name = args.library or "unknown"

    output_dir = Path(args.output) if args.output else old_rules_path.parent

    print(f"\n[GENERATING] Regenerating migrator...")
    generator = MigratorGenerator(library_name=library_name)
    generator.generate(all_changelogs, output_dir)
    print("[SUCCESS] Migrator updated!")


def cmd_run(args):
    """Run a migration on a file or directory."""
    source_path = Path(args.path)
    migration_rules_path = Path(args.rules) if args.rules else None

    if not source_path.exists():
        print(f"[ERROR] Source path not found: {source_path}")
        sys.exit(1)

    if migration_rules_path and migration_rules_path.exists():
        parser = ChangelogParser()
        try:
            changelogs = parser.parse(migration_rules_path.read_text(encoding="utf-8"), fmt="json")
        except Exception as e:
            print(f"[ERROR] Invalid rules file: {e}")
            sys.exit(1)
    else:
        print("[ERROR] Must provide --rules path to migration_rules.json")
        sys.exit(1)

    resolver = VersionResolver(changelogs)
    path = resolver.resolve_path(args.from_version, args.to_version)

    print(f"\n[MIGRATION] v{path.source_version} -> v{path.target_version}")
    print(f"   Direction: {'upgrade' if path.is_upgrade else 'downgrade'}")
    print(f"   Rules to apply: {len(path.rules)}")

    engine = TransactionalMigrationEngine(
        transactional=args.transactional,
        interactive_approval=args.interactive,
        idempotency_check=not args.no_idempotency_check,
    )

    if source_path.is_file():
        result = engine.migrate_file(
            source_path, path.rules,
            dry_run=args.dry_run,
            backup=not args.no_backup,
        )
        if result.was_modified:
            print(f"\n[MODIFIED] {source_path}:")
            for c in result.changes:
                print(f"   + {c}")
        else:
            print(f"   No changes needed in {source_path}")
        if result.errors:
            for e in result.errors:
                print(f"   ! {e}")
        if result.rule_results:
            avg_conf = result.average_confidence
            print(f"\n   Confidence: {avg_conf:.0%}")
    else:
        report = engine.migrate_directory(
            source_path, path,
            dry_run=args.dry_run,
            backup=not args.no_backup,
        )
        print(f"\n{report.summary()}")

    if args.dry_run:
        print("\n[DRY RUN] No files were modified.")


def cmd_preview(args):
    """Preview migration changes without modifying files."""
    source_code = Path(args.file).read_text(encoding="utf-8")
    rules_path = Path(args.rules)

    parser = ChangelogParser()
    changelogs = parser.parse(rules_path.read_text(encoding="utf-8"), fmt="json")

    resolver = VersionResolver(changelogs)
    path = resolver.resolve_path(args.from_version, args.to_version)

    engine = TransactionalMigrationEngine(interactive_approval=False)
    preview = engine.preview_migration(source_code, path.rules)
    print(preview)


def cmd_rules(args):
    """List and inspect migration rules."""
    rules_path = Path(args.rules)
    if not rules_path.exists():
        print(f"[ERROR] Rules file not found: {rules_path}")
        sys.exit(1)

    try:
        content = rules_path.read_text(encoding="utf-8")
        mf = MigrationFile.model_validate_json(content)
        library = mf.library
        versions = mf.versions
    except Exception as e:
        parser = ChangelogParser()
        versions = parser.parse(rules_path.read_text(encoding="utf-8"), fmt="json")
        library = "Unknown"

    print(f"\n[LIBRARY] Migration rules for: {library}")
    print("=" * 50)

    for vc in versions:
        date = vc.release_date or ""
        print(f"\n  v{vc.version} {f'({date})' if date else ''} - {len(vc.rules)} rule(s)")
        for rule in vc.rules:
            ct = rule.change_type.value
            desc = rule.description
            old = rule.old_name
            new = rule.new_name
            rename_str = f" [{old} -> {new}]" if old and new else ""
            safety_icon = {"safe": "OK", "review_required": "?", "risky": "!"}[rule.safety]
            when_str = ""
            if rule.when:
                parts = []
                if rule.when.imported_from:
                    parts.append(f"from {rule.when.imported_from}")
                if rule.when.inside_class:
                    parts.append(f"inside {rule.when.inside_class}")
                if parts:
                    when_str = f" (when: {' '.join(parts)})"
            print(f"    [{safety_icon}] [{ct}]{rename_str} {desc}{when_str}")


def cmd_interactive(args):
    """Interactive rule builder - build rules manually."""
    print("\n[INTERACTIVE] Rule Builder")
    print("=" * 40)
    print("Build migration rules step by step.\n")

    rules = []
    version = input("Version (e.g. 2.0.0): ").strip()
    rule_counter = 1

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

        rule_data = {
            "id": f"RULE-{rule_counter:03d}",
            "change_type": change_type.value,
            "version_introduced": version,
            "description": input("Description: ").strip(),
        }

        if change_type in (ChangeType.RENAME_FUNCTION, ChangeType.RENAME_CLASS, ChangeType.RENAME_ATTRIBUTE, ChangeType.REPLACE_WITH_PROPERTY):
            rule_data["old_name"] = input("Old name: ").strip()
            rule_data["new_name"] = input("New name: ").strip()

        elif change_type == ChangeType.RENAME_IMPORT:
            rule_data["old_name"] = input("Old symbol name: ").strip()
            rule_data["new_name"] = input("New symbol name: ").strip()
            rule_data["old_module"] = input("Old module (e.g. mylib.old): ").strip()
            rule_data["new_module"] = input("New module (e.g. mylib.new): ").strip()

        elif change_type in (ChangeType.ADD_ARGUMENT, ChangeType.REMOVE_ARGUMENT):
            rule_data["function_name"] = input("Function name: ").strip()
            rule_data["argument_name"] = input("Argument name: ").strip()
            if change_type == ChangeType.ADD_ARGUMENT:
                rule_data["default_value"] = input("Default value (Python expr): ").strip()

        elif change_type == ChangeType.CHANGE_ARGUMENT_DEFAULT:
            rule_data["argument_name"] = input("Argument name: ").strip()
            rule_data["default_value"] = input("Default value (Python expr): ").strip()

        elif change_type == ChangeType.REORDER_ARGUMENTS:
            rule_data["function_name"] = input("Function name: ").strip()
            rule_data["new_order"] = [x.strip() for x in input("New order (comma separated): ").split(',')]

        elif change_type == ChangeType.MOVE_TO_MODULE:
            rule_data["old_name"] = input("Symbol name: ").strip()
            rule_data["source_module"] = input("Source module: ").strip()
            rule_data["target_module"] = input("Target module: ").strip()

        elif change_type == ChangeType.DEPRECATE_FUNCTION:
            rule_data["old_name"] = input("Function name: ").strip()
            rule_data["replacement"] = input("Replacement (or press Enter for none): ").strip() or None

        elif change_type in (ChangeType.ADD_DECORATOR, ChangeType.REMOVE_DECORATOR):
            rule_data["function_name"] = input("Function name: ").strip()
            rule_data["decorator_name"] = input("Decorator name (without @): ").strip()

        elif change_type == ChangeType.RENAME_ARGUMENT:
            rule_data["function_name"] = input("Function name: ").strip()
            rule_data["argument_name"] = input("Old argument name: ").strip()
            rule_data["new_argument_name"] = input("New argument name: ").strip()

        elif change_type in (ChangeType.REMOVE_FUNCTION, ChangeType.REMOVE_CLASS):
            rule_data["old_name"] = input("Symbol name: ").strip()

        try:
            rule = MigrationRule(**rule_data)
            rules.append(rule)
            print(f"[OK] Rule added: {rule.change_type.value} with ID {rule.id}")
            rule_counter += 1
        except Exception as e:
            print(f"[ERROR] Invalid rule: {e}")

    if rules:
        output = args.output or f"rules_{version}.json"
        vc = VersionChangelog(version=version, rules=rules)
        lib = input("\nLibrary name: ").strip()
        mf = MigrationFile(library=lib, versions=[vc])
        Path(output).write_text(mf.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")
        print(f"\n[SUCCESS] Saved {len(rules)} rule(s) to {output}")
    else:
        print("No rules created.")


def cmd_export_schema(args):
    """Export JSON schema for migration rules."""
    schema = MigrationFile.model_json_schema()
    output_path = Path(args.output) if args.output else Path("migration-schema.json")
    output_path.write_text(json.dumps(schema, indent=2))
    print(f"[SUCCESS] Schema exported to {output_path}")


def cmd_validate_rules(args):
    """Validate a migration rules JSON file."""
    rules_path = Path(args.file)
    if not rules_path.exists():
        print(f"[ERROR] File not found: {rules_path}")
        sys.exit(1)

    print(f"[INFO] Validating {rules_path}...")
    try:
        content = rules_path.read_text(encoding="utf-8")
        data = json.loads(content)

        if isinstance(data, list):
            for item in data:
                VersionChangelog(**item)
        else:
            MigrationFile(**data)

        all_rules = []
        if isinstance(data, list):
            for vc in data:
                all_rules.extend(vc.get("rules", []))
        else:
            for vc in data.get("versions", []):
                all_rules.extend(vc.get("rules", []))

        report = RuleValidator().validate_rules([MigrationRule.from_dict(r) for r in all_rules])

        if report.valid:
            print("[SUCCESS] Validation successful! All rules are valid.")
        else:
            print(f"[ERROR] Validation failed with {len(report.errors)} error(s):")
            for e in report.errors:
                print(f"  - [{e.rule_id}] {e.message}")

        if report.warnings:
            print(f"\n[WARNINGS] {len(report.warnings)} warning(s):")
            for w in report.warnings:
                print(f"  - [{w.rule_id}] {w.message}")

        if report.info:
            print(f"\n[INFO] {len(report.info)} note(s):")
            for i in report.info:
                print(f"  - [{i.rule_id}] {i.message}")

        if not report.valid:
            sys.exit(1)

    except ValidationError as e:
        print("[ERROR] Validation Failed:")
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            print(f"  - {loc}: {msg}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Validation Failed with unexpected error: {e}")
        sys.exit(1)


def cmd_diff_rules(args):
    """Show diff between two rule files."""
    old_path = Path(args.old)
    new_path = Path(args.new)

    if not old_path.exists() or not new_path.exists():
        print("[ERROR] Both rule files must exist")
        sys.exit(1)

    print(f"[INFO] Comparing:\n  Old: {old_path}\n  New: {new_path}\n")

    parser = ChangelogParser()
    old_rules = {}
    new_rules = {}

    try:
        old_mf = MigrationFile.model_validate_json(old_path.read_text())
        new_mf = MigrationFile.model_validate_json(new_path.read_text())
    except:
        old_changelogs = parser.parse(old_path.read_text(), fmt="json")
        new_changelogs = parser.parse(new_path.read_text(), fmt="json")
        for vc in old_changelogs:
            for r in vc.rules:
                old_rules[r.id] = r
        for vc in new_changelogs:
            for r in vc.rules:
                new_rules[r.id] = r
    else:
        for vc in old_mf.versions:
            for r in vc.rules:
                old_rules[r.id] = r
        for vc in new_mf.versions:
            for r in vc.rules:
                new_rules[r.id] = r

    added = set(new_rules.keys()) - set(old_rules.keys())
    removed = set(old_rules.keys()) - set(new_rules.keys())
    modified = []

    for rid in set(new_rules.keys()) & set(old_rules.keys()):
        old_r = old_rules[rid]
        new_r = new_rules[rid]
        changes = []
        for field in ["old_name", "new_name", "function_name", "argument_name", "old_module", "new_module", "safety", "priority"]:
            ov = getattr(old_r, field, None)
            nv = getattr(new_r, field, None)
            if ov != nv:
                changes.append(f"  {field}: {ov} -> {nv}")
        if changes:
            modified.append((rid, changes))

    if added:
        print(f"[+ADDED] {len(added)} rule(s):")
        for rid in sorted(added):
            r = new_rules[rid]
            print(f"  + {rid}: [{r.change_type.value}] {r.description}")
    if removed:
        print(f"\n[-REMOVED] {len(removed)} rule(s):")
        for rid in sorted(removed):
            r = old_rules[rid]
            print(f"  - {rid}: [{r.change_type.value}] {r.description}")
    if modified:
        print(f"\n[~MODIFIED] {len(modified)} rule(s):")
        for rid, changes in modified:
            print(f"  ~ {rid}:")
            for c in changes:
                print(c)
    if not added and not removed and not modified:
        print("[INFO] No differences found.")


def cmd_audit(args):
    """Audit migration status of a project directory."""
    directory = Path(args.directory)
    if not directory.exists():
        print(f"[ERROR] Directory not found: {directory}")
        sys.exit(1)

    rules_path = Path(args.rules) if args.rules else None
    if not rules_path:
        print("[ERROR] --rules is required for audit")
        sys.exit(1)

    parser = ChangelogParser()
    changelogs = parser.parse(rules_path.read_text(), fmt="json")
    resolver = VersionResolver(changelogs)
    available = resolver.available_versions

    print(f"\n[AUDIT] Scanning: {directory}")
    print(f"   Rules: {rules_path}")
    print(f"   Available versions: {', '.join(available)}\n")

    py_files = list(directory.rglob("*.py"))
    print(f"   Python files: {len(py_files)}")

    import re
    version_pattern = re.compile(r'["\']?(\d+\.\d+\.\d+)["\']?')

    print("\n[FILE SCAN]")
    for f in py_files[:20]:
        content = f.read_text(encoding="utf-8", errors="ignore")
        versions_found = version_pattern.findall(content)
        if versions_found:
            print(f"  {f.relative_to(directory)}: mentions {set(versions_found)}")

    if len(py_files) > 20:
        print(f"  ... and {len(py_files) - 20} more files")


def cmd_auto_upgrade(args):
    """Auto-detect outdated dependencies and run migrations."""
    directory = Path(args.directory)
    if not directory.exists():
        print(f"[ERROR] Directory not found: {directory}")
        sys.exit(1)

    print(f"\n[AUTO-UPGRADE] Analyzing: {directory}")
    print("   This feature scans requirements.txt / pyproject.toml,")
    print("   detects outdated packages, fetches migration rules,")
    print("   and runs migrations automatically.")

    req_file = directory / "requirements.txt"
    pyproject = directory / "pyproject.toml"

    if req_file.exists():
        print(f"\n[INFO] Found requirements.txt")
        deps = req_file.read_text().splitlines()
        for dep in deps:
            dep = dep.strip()
            if dep and not dep.startswith("#"):
                print(f"   - {dep}")
    elif pyproject.exists():
        print(f"\n[INFO] Found pyproject.toml")
        content = pyproject.read_text()
        deps = re.findall(r'["\']?([a-zA-Z0-9_-]+)\s*[<>=!]+.*["\']?', content)
        for dep in deps:
            print(f"   - {dep}")
    else:
        print("[INFO] No dependency file found.")
        print("   Scanning Python files for imports...")

        py_files = list(directory.rglob("*.py"))
        imports_found = set()
        for f in py_files:
            content = f.read_text(encoding="utf-8", errors="ignore")
            for match in re.findall(r'^import\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content, re.MULTILINE):
                base = match.split(".")[0]
                if base not in ("sys", "os", "re", "json", "math", "time", "datetime", "pathlib", "typing", "dataclasses"):
                    imports_found.add(base)
            for match in re.findall(r'^from\s+([a-zA-Z_][a-zA-Z0-9_.]+)\s+import', content, re.MULTILINE):
                base = match.split(".")[0]
                if base not in ("sys", "os", "re", "json", "math", "time", "datetime", "pathlib", "typing", "dataclasses"):
                    imports_found.add(base)

        for imp in sorted(imports_found)[:20]:
            print(f"   - {imp}")
        if len(imports_found) > 20:
            print(f"   ... and {len(imports_found) - 20} more")


def main():
    parser = argparse.ArgumentParser(
        description="MigratorGen - AI-native migration infrastructure for library maintainers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("create", help="Create migrator from changelog")
    p.add_argument("--changelog", required=True, help="Path to changelog file")
    p.add_argument("--library", required=True, help="Library name")
    p.add_argument("--output", default="./generated_migrator", help="Output directory")

    p = subparsers.add_parser("update", help="Update existing migrator")
    p.add_argument("--existing", required=True, help="Path to existing migration_rules.json")
    p.add_argument("--new-changelog", required=True, help="Path to new changelog")
    p.add_argument("--output", help="Output directory (default: same as existing)")
    p.add_argument("--library", help="Library name override")

    p = subparsers.add_parser("run", help="Run migration on code")
    p.add_argument("path", help="File or directory to migrate")
    p.add_argument("--rules", required=True, help="Path to migration_rules.json")
    p.add_argument("--from", dest="from_version", required=True)
    p.add_argument("--to", dest="to_version", default="latest")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-backup", action="store_true")
    p.add_argument("--transactional", action="store_true", default=True, help="Enable transactional mode (rollback on failure)")
    p.add_argument("--no-transactional", dest="transactional", action="store_false", help="Disable transactional mode")
    p.add_argument("--interactive", action="store_true", help="Interactive approval for risky transforms")
    p.add_argument("--no-idempotency-check", dest="no_idempotency_check", action="store_true", help="Skip idempotency checks")

    p = subparsers.add_parser("preview", help="Preview migration changes")
    p.add_argument("file", help="Python file to preview")
    p.add_argument("--rules", required=True)
    p.add_argument("--from", dest="from_version", required=True)
    p.add_argument("--to", dest="to_version", default="latest")

    p = subparsers.add_parser("rules", help="List migration rules")
    p.add_argument("--rules", required=True)

    p = subparsers.add_parser("interactive", help="Interactive rule builder")
    p.add_argument("--output", help="Output file for rules")

    p = subparsers.add_parser("export-schema", help="Export JSON schema for rules")
    p.add_argument("--output", help="Output file path")

    p = subparsers.add_parser("validate-rules", help="Validate a rules file")
    p.add_argument("file", help="JSON rules file to validate")

    p = subparsers.add_parser("diff-rules", help="Show diff between two rule sets")
    p.add_argument("--old", required=True, help="Old rules file")
    p.add_argument("--new", required=True, help="New rules file")

    p = subparsers.add_parser("audit", help="Audit migration status of a project")
    p.add_argument("directory", help="Project directory to audit")
    p.add_argument("--rules", help="Migration rules file")

    p = subparsers.add_parser("auto-upgrade", help="Auto-detect and run migrations")
    p.add_argument("directory", help="Project directory")
    p.add_argument("--rules", help="Migration rules file")
    p.add_argument("--to", dest="to_version", default="latest", help="Target version")

    args = parser.parse_args()

    commands = {
        "create": cmd_create,
        "update": cmd_update,
        "run": cmd_run,
        "preview": cmd_preview,
        "rules": cmd_rules,
        "interactive": cmd_interactive,
        "export-schema": cmd_export_schema,
        "validate-rules": cmd_validate_rules,
        "diff-rules": cmd_diff_rules,
        "audit": cmd_audit,
        "auto-upgrade": cmd_auto_upgrade,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()