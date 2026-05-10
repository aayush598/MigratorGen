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
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to sys.path so 'core' can be imported when running cli/cli.py directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.changelog_parser import ChangelogParser, VersionChangelog, MigrationRule, ChangeType, MigrationFile
from core.version_resolver import VersionResolver
from core.migration_engine import MigrationEngine
from core.migrator_generator import MigratorGenerator
from pydantic import ValidationError


def cmd_create(args):
    """Create a new migrator package from a changelog file."""
    changelog_path = Path(args.changelog)
    output_dir = Path(args.output)
    library_name = args.library

    if not changelog_path.exists():
        print(f"❌ Changelog file not found: {changelog_path}")
        sys.exit(1)

    print(f"📖 Reading changelog: {changelog_path}")
    content = changelog_path.read_text(encoding="utf-8")

    parser = ChangelogParser()
    try:
        changelogs = parser.parse(content, fmt="json")
    except ValidationError as e:
        print(f"❌ Validation failed for {changelog_path}:\n{e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to parse {changelog_path}:\n{e}")
        sys.exit(1)

    print(f"   Found {len(changelogs)} version(s)")

    total_rules = sum(len(vc.rules) for vc in changelogs)
    print(f"\n📋 Total migration rules: {total_rules}")

    print(f"\n🔨 Generating migrator package...")
    generator = MigratorGenerator(library_name=library_name)
    generator.generate(changelogs, output_dir)

    print(f"\n✅ Done! Your migrator is at: {output_dir}")


def cmd_update(args):
    """Update an existing migrator with a new changelog."""
    old_rules_path = Path(args.existing)
    new_changelog_path = Path(args.new_changelog)

    if not old_rules_path.exists():
        print(f"❌ Existing rules file not found: {old_rules_path}")
        sys.exit(1)

    print(f"📖 Loading existing migration rules: {old_rules_path}")
    parser = ChangelogParser()
    try:
        old_changelogs = parser.parse(old_rules_path.read_text(encoding="utf-8"), fmt="json")
    except Exception as e:
        print(f"❌ Failed to parse existing rules:\n{e}")
        sys.exit(1)

    print(f"   {len(old_changelogs)} existing version(s)")

    print(f"\n📖 Reading new changelog: {new_changelog_path}")
    try:
        new_changelogs = parser.parse(new_changelog_path.read_text(encoding="utf-8"), fmt="json")
    except Exception as e:
        print(f"❌ Failed to parse new changelog:\n{e}")
        sys.exit(1)

    merged = parser.merge_changelogs(old_changelogs, new_changelogs)
    print(f"   {len(merged)} new version(s) detected")

    if not merged:
        print("   No new versions found. Nothing to update.")
        return

    all_changelogs = old_changelogs + merged
    
    # Try to load library name from old data if possible
    try:
        old_data = json.loads(old_rules_path.read_text(encoding="utf-8"))
        library_name = old_data.get("library", args.library or "unknown")
    except:
        library_name = args.library or "unknown"
        
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

    if migration_rules_path and migration_rules_path.exists():
        parser = ChangelogParser()
        try:
            changelogs = parser.parse(migration_rules_path.read_text(encoding="utf-8"), fmt="json")
        except Exception as e:
            print(f"❌ Invalid rules file:\n{e}")
            sys.exit(1)
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

    parser = ChangelogParser()
    changelogs = parser.parse(rules_path.read_text(encoding="utf-8"), fmt="json")

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

    try:
        content = rules_path.read_text(encoding="utf-8")
        mf = MigrationFile.model_validate_json(content)
        library = mf.library
        versions = mf.versions
    except Exception as e:
        # Fallback if bare list
        parser = ChangelogParser()
        versions = parser.parse(rules_path.read_text(encoding="utf-8"), fmt="json")
        library = "Unknown"

    print(f"\n📚 Migration rules for: {library}")
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
            print(f"    • [{ct}]{rename_str} {desc}")


def cmd_interactive(args):
    """Interactive rule builder - build rules manually."""
    print("\n🔧 Interactive Rule Builder")
    print("=" * 40)
    print("Build migration rules step by step.\n")

    rules = []
    version = input("Version (e.g. 2.0.0): ").strip()
    rule_counter = 1

    while True:
        print("\nChange types:")
        for i, ct in enumerate(ChangeType, 1):
            if ct.value == "custom_transform":
                continue
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

        # Prompt for relevant fields based on type
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
            
        elif change_type in (ChangeType.REMOVE_FUNCTION, ChangeType.REMOVE_CLASS):
            rule_data["old_name"] = input("Symbol name: ").strip()

        try:
            rule = MigrationRule(**rule_data)
            rules.append(rule)
            print(f"✓ Rule added: {rule.change_type.value} with ID {rule.id}")
            rule_counter += 1
        except Exception as e:
            print(f"❌ Invalid rule: {e}")

    if rules:
        output = args.output or f"rules_{version}.json"
        vc = VersionChangelog(version=version, rules=rules)
        mf = MigrationFile(library=input("\nLibrary name: ").strip(), versions=[vc])
        Path(output).write_text(mf.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")
        print(f"\n✅ Saved {len(rules)} rule(s) to {output}")
    else:
        print("No rules created.")


def cmd_export_schema(args):
    """Export JSON schema for migration rules."""
    schema = MigrationFile.model_json_schema()
    output_path = Path("migration-schema.json")
    output_path.write_text(json.dumps(schema, indent=2))
    print(f"✅ Schema exported to {output_path}")


def cmd_validate_rules(args):
    """Validate a migration rules JSON file."""
    rules_path = Path(args.file)
    if not rules_path.exists():
        print(f"❌ File not found: {rules_path}")
        sys.exit(1)

    print(f"🔍 Validating {rules_path}...")
    try:
        content = rules_path.read_text(encoding="utf-8")
        data = json.loads(content)
        
        if isinstance(data, list):
            # Backward compatibility check
            for item in data:
                VersionChangelog(**item)
        else:
            MigrationFile(**data)
            
        print("✅ Validation successful! The rules are valid.")
    except ValidationError as e:
        print("❌ Validation Failed:")
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            print(f"  - {loc}: {msg}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Validation Failed with unexpected error:\n{e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="MigratorGen - Generate code migrators from changelogs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p = subparsers.add_parser("create", help="Create migrator from changelog")
    p.add_argument("--changelog", required=True, help="Path to changelog file")
    p.add_argument("--library", required=True, help="Library name")
    p.add_argument("--output", default="./generated_migrator", help="Output directory")

    # update
    p = subparsers.add_parser("update", help="Update existing migrator")
    p.add_argument("--existing", required=True, help="Path to existing migration_rules.json")
    p.add_argument("--new-changelog", required=True, help="Path to new changelog")
    p.add_argument("--output", help="Output directory (default: same as existing)")
    p.add_argument("--library", help="Library name override")

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
    
    # export-schema
    p = subparsers.add_parser("export-schema", help="Export JSON schema for rules")
    
    # validate-rules
    p = subparsers.add_parser("validate-rules", help="Validate a rules file")
    p.add_argument("file", help="JSON rules file to validate")

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
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()