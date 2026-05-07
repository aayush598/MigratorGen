"""
MigratorGen CLI - Main command-line interface for the migration platform.

Commands:
  create       Create a new migrator from a changelog file
  update       Update an existing migrator with a new changelog
  run          Run a migration on code
  preview      Preview what would change without modifying files
  rules        List/inspect migration rules
  interactive  Interactive rule builder
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to sys.path so 'core' can be imported when running cli/cli.py directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.changelog_parser import ChangelogParser, VersionChangelog, MigrationRule, ChangeType
from core.version_resolver import VersionResolver
from core.migration_engine import MigrationEngine
from core.llm_parser import LLMParser
from core.migrator_generator import MigratorGenerator


def cmd_create(args):
    """Create a new migrator package from a changelog file."""
    changelog_path = Path(args.changelog)
    output_dir = Path(args.output)
    library_name = args.library
    use_llm = not args.no_llm

    if not changelog_path.exists():
        print(f"❌ Changelog file not found: {changelog_path}")
        sys.exit(1)

    print(f"📖 Reading changelog: {changelog_path}")
    content = changelog_path.read_text(encoding="utf-8")

    parser = ChangelogParser()
    fmt = "json" if changelog_path.suffix == ".json" else "auto"
    changelogs = parser.parse(content, fmt=fmt)

    print(f"   Found {len(changelogs)} version(s)")

    # Use LLM to extract rules from markdown changelogs
    if use_llm:
        needs_llm = [vc for vc in changelogs if vc.raw_notes and not vc.rules]
        if needs_llm:
            print(f"\n🤖 Using LLM to extract {len(needs_llm)} version changelog(s)...")
            llm = LLMParser()
            for vc in needs_llm:
                print(f"   Parsing v{vc.version}...")
                vc.rules = llm.parse_changelog_entry(vc.version, vc.raw_notes)
                print(f"   → {len(vc.rules)} rule(s) extracted")

    total_rules = sum(len(vc.rules) for vc in changelogs)
    print(f"\n📋 Total migration rules: {total_rules}")

    # Generate the migrator
    print(f"\n🔨 Generating migrator package...")
    generator = MigratorGenerator(library_name=library_name)
    generator.generate(changelogs, output_dir)

    print(f"\n✅ Done! Your migrator is at: {output_dir}")
    print(f"\nTo use it:")
    print(f"  cd {output_dir}")
    print(f"  pip install -e .")
    print(f"  {generator.package_name} list-versions")
    print(f"  {generator.package_name} migrate --from 1.0.0 --to 2.0.0 /path/to/project")


def cmd_update(args):
    """Update an existing migrator with a new changelog."""
    old_rules_path = Path(args.existing)
    new_changelog_path = Path(args.new_changelog)

    if not old_rules_path.exists():
        print(f"❌ Existing rules file not found: {old_rules_path}")
        sys.exit(1)

    print(f"📖 Loading existing migration rules: {old_rules_path}")
    old_data = json.loads(old_rules_path.read_text())
    old_changelogs = []
    for entry in old_data.get("versions", []):
        vc = VersionChangelog(
            version=entry["version"],
            release_date=entry.get("release_date"),
            raw_notes=entry.get("raw_notes", ""),
        )
        vc.rules = [MigrationRule.from_dict(r) for r in entry.get("rules", [])]
        old_changelogs.append(vc)

    print(f"   {len(old_changelogs)} existing version(s)")

    print(f"\n📖 Reading new changelog: {new_changelog_path}")
    new_content = new_changelog_path.read_text(encoding="utf-8")
    parser = ChangelogParser()
    new_changelogs = parser.parse(new_content, fmt="auto")

    # Find new versions
    merged = parser.merge_changelogs(old_changelogs, new_changelogs)
    print(f"   {len(merged)} new version(s) detected")

    if not merged:
        print("   No new versions found. Nothing to update.")
        return

    if not args.no_llm:
        print(f"\n🤖 Using LLM to parse new versions...")
        llm = LLMParser()
        for vc in merged:
            if vc.raw_notes and not vc.rules:
                vc.rules = llm.parse_changelog_entry(vc.version, vc.raw_notes)
                print(f"   v{vc.version}: {len(vc.rules)} rule(s)")

    all_changelogs = old_changelogs + merged
    library_name = old_data.get("library", args.library or "unknown")
    output_dir = Path(args.output) if args.output else old_rules_path.parent

    print(f"\n🔨 Regenerating migrator...")
    generator = MigratorGenerator(library_name=library_name)
    generator.generate(all_changelogs, output_dir)
    print("✅ Migrator updated!")


def cmd_run(args):
    """Run a migration on a file or directory."""
    source_path = Path(args.path)
    migration_rules_path = Path(args.rules) if args.rules else None

    if not source_path.exists():
        print(f"❌ Source path not found: {source_path}")
        sys.exit(1)

    # Load rules from JSON file or inline changelog
    if migration_rules_path and migration_rules_path.exists():
        data = json.loads(migration_rules_path.read_text())
        changelogs = []
        for entry in data.get("versions", []):
            vc = VersionChangelog(
                version=entry["version"],
                release_date=entry.get("release_date"),
            )
            vc.rules = [MigrationRule.from_dict(r) for r in entry.get("rules", [])]
            changelogs.append(vc)
    else:
        print("❌ Must provide --rules path to migration_rules.json")
        sys.exit(1)

    resolver = VersionResolver(changelogs)
    path = resolver.resolve_path(args.from_version, args.to_version)

    print(f"\n🚀 Migration: v{path.source_version} -> v{path.target_version}")
    print(f"   Direction: {'upgrade ⬆' if path.is_upgrade else 'downgrade ⬇'}")
    print(f"   Rules to apply: {len(path.rules)}")

    engine = MigrationEngine()

    if source_path.is_file():
        result = engine.migrate_file(
            source_path, path.rules,
            dry_run=args.dry_run,
            backup=not args.no_backup,
        )
        if result.was_modified:
            print(f"\n📝 {source_path}:")
            for c in result.changes:
                print(f"   ✓ {c}")
        else:
            print(f"   No changes needed in {source_path}")
        if result.errors:
            for e in result.errors:
                print(f"   ✗ {e}")
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

    data = json.loads(rules_path.read_text())
    changelogs = []
    for entry in data.get("versions", []):
        vc = VersionChangelog(version=entry["version"], release_date=entry.get("release_date"))
        vc.rules = [MigrationRule.from_dict(r) for r in entry.get("rules", [])]
        changelogs.append(vc)

    resolver = VersionResolver(changelogs)
    path = resolver.resolve_path(args.from_version, args.to_version)

    engine = MigrationEngine()
    preview = engine.preview_migration(source_code, path.rules)
    print(preview)


def cmd_rules(args):
    """List and inspect migration rules."""
    rules_path = Path(args.rules)
    if not rules_path.exists():
        print(f"❌ Rules file not found: {rules_path}")
        sys.exit(1)

    data = json.loads(rules_path.read_text())
    library = data.get("library", "Unknown")

    print(f"\n📚 Migration rules for: {library}")
    print("=" * 50)

    for entry in data.get("versions", []):
        version = entry["version"]
        rules = entry.get("rules", [])
        date = entry.get("release_date", "")
        print(f"\n  v{version} {f'({date})' if date else ''} - {len(rules)} rule(s)")
        for rule in rules:
            ct = rule.get("change_type", "?")
            desc = rule.get("description", "")
            old = rule.get("old_name", "")
            new = rule.get("new_name", "")
            rename_str = f" [{old} -> {new}]" if old and new else ""
            print(f"    • [{ct}]{rename_str} {desc}")


def cmd_interactive(args):
    """Interactive rule builder - build rules manually without LLM."""
    print("\n🔧 Interactive Rule Builder")
    print("=" * 40)
    print("Build migration rules step by step.\n")

    rules = []
    version = input("Version (e.g. 2.0.0): ").strip()

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
            "change_type": change_type.value,
            "version_introduced": version,
            "description": input("Description: ").strip(),
        }

        # Prompt for relevant fields based on type
        if change_type in (ChangeType.RENAME_FUNCTION, ChangeType.RENAME_CLASS, ChangeType.RENAME_ATTRIBUTE):
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

        try:
            rule = MigrationRule.from_dict(rule_data)
            rules.append(rule)
            print(f"✓ Rule added: {rule.change_type.value}")
        except Exception as e:
            print(f"❌ Invalid rule: {e}")

    if rules:
        output = args.output or f"rules_{version}.json"
        vc = VersionChangelog(version=version, release_date=None, rules=rules)
        data = {
            "library": input("\nLibrary name: ").strip(),
            "versions": [vc.to_dict()],
        }
        Path(output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"\n✅ Saved {len(rules)} rule(s) to {output}")
    else:
        print("No rules created.")


def main():
    parser = argparse.ArgumentParser(
        description="MigratorGen - Generate code migrators from changelogs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a migrator from a JSON changelog
  python cli.py create --changelog changelog.json --library mylib --output ./dist/

  # Create from a markdown CHANGELOG.md (uses LLM)
  python cli.py create --changelog CHANGELOG.md --library mylib --output ./dist/

  # Run migration
  python cli.py run --rules dist/migration_rules.json --from 1.0.0 --to 2.0.0 ./myproject/

  # Preview changes only
  python cli.py preview --rules dist/migration_rules.json --from 1.0.0 --to 2.0.0 myfile.py

  # Interactive rule builder
  python cli.py interactive

  # List rules
  python cli.py rules --rules dist/migration_rules.json
        """,
    )

    subparsers = parser.add_subparsers(dest="command")

    # create
    p = subparsers.add_parser("create", help="Create migrator from changelog")
    p.add_argument("--changelog", required=True, help="Path to changelog file")
    p.add_argument("--library", required=True, help="Library name")
    p.add_argument("--output", default="./generated_migrator", help="Output directory")
    p.add_argument("--no-llm", action="store_true", help="Skip LLM parsing")

    # update
    p = subparsers.add_parser("update", help="Update existing migrator")
    p.add_argument("--existing", required=True, help="Path to existing migration_rules.json")
    p.add_argument("--new-changelog", required=True, help="Path to new changelog")
    p.add_argument("--output", help="Output directory (default: same as existing)")
    p.add_argument("--library", help="Library name override")
    p.add_argument("--no-llm", action="store_true")

    # run
    p = subparsers.add_parser("run", help="Run migration on code")
    p.add_argument("path", help="File or directory to migrate")
    p.add_argument("--rules", required=True, help="Path to migration_rules.json")
    p.add_argument("--from", dest="from_version", required=True)
    p.add_argument("--to", dest="to_version", default="latest")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-backup", action="store_true")

    # preview
    p = subparsers.add_parser("preview", help="Preview migration changes")
    p.add_argument("file", help="Python file to preview")
    p.add_argument("--rules", required=True)
    p.add_argument("--from", dest="from_version", required=True)
    p.add_argument("--to", dest="to_version", default="latest")

    # rules
    p = subparsers.add_parser("rules", help="List migration rules")
    p.add_argument("--rules", required=True)

    # interactive
    p = subparsers.add_parser("interactive", help="Interactive rule builder")
    p.add_argument("--output", help="Output file for rules")

    args = parser.parse_args()

    commands = {
        "create": cmd_create,
        "update": cmd_update,
        "run": cmd_run,
        "preview": cmd_preview,
        "rules": cmd_rules,
        "interactive": cmd_interactive,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()