"""create / update / export-schema / interactive — manage migrator packages."""

from __future__ import annotations

import json
from pathlib import Path

from migrator_gen import ChangeType, MigrationFile, Rule, VersionChangelog

from ..cli.context import CLIContext
from ..cli.output import OutputFormatter


def cmd_create(ctx: CLIContext, out: OutputFormatter) -> None:
    args = ctx.args
    changelog_path = Path(args.changelog)
    output_dir = Path(args.output)

    if not changelog_path.exists():
        out.err(f"Changelog file not found: {changelog_path}")

    client = ctx.client
    mf = client.parse_changelog(str(changelog_path))
    total_rules = sum(len(v.rules) for v in mf.versions)

    out.info(f"Library: {mf.library}, {len(mf.versions)} version(s), {total_rules} rule(s)")
    out_path = client.generate_migrator_package(mf.library, str(output_dir))

    if ctx.json_mode:
        out.print_json(
            {
                "library": mf.library,
                "versions": len(mf.versions),
                "rules": total_rules,
                "output": out_path,
            }
        )
    else:
        out.ok(f"Migrator created at: {out_path}")


def cmd_update(ctx: CLIContext, out: OutputFormatter) -> None:
    args = ctx.args
    old_rules_path = Path(args.existing)
    new_changelog_path = Path(args.new_changelog)

    for p, label in [(old_rules_path, "Existing rules"), (new_changelog_path, "New changelog")]:
        if not p.exists():
            out.err(f"{label} not found: {p}")

    client = ctx.client

    old_mf = client.parse_changelog(str(old_rules_path))
    new_mf = client.parse_changelog(str(new_changelog_path))

    existing_versions = {vc.version for vc in old_mf.versions}
    merged = [vc for vc in new_mf.versions if vc.version not in existing_versions]

    if not merged:
        out.info("No new versions found. Nothing to update.")
        if ctx.json_mode:
            out.print_json({"status": "no_changes"})
        return

    all_versions = old_mf.versions + merged
    library = args.library or old_mf.library or "unknown"
    output_dir = Path(args.output) if args.output else old_rules_path.parent

    merged_mf = MigrationFile(library=library, versions=all_versions)
    output_dir.mkdir(parents=True, exist_ok=True)
    merged_path = output_dir / "migration_rules.json"
    merged_path.write_text(merged_mf.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")

    out_path = client.generate_migrator_package(library, str(output_dir))

    if ctx.json_mode:
        out.print_json({"new_versions": len(merged), "output": str(out_path)})
    else:
        out.ok(f"Migrator updated — added {len(merged)} version(s)")
        out.info(f"Output: {out_path}")


def cmd_export_schema(ctx: CLIContext, out: OutputFormatter) -> None:
    args = ctx.args
    schema = MigrationFile.model_json_schema()
    output_path = Path(args.output)
    output_path.write_text(json.dumps(schema, indent=2))
    out.ok(f"Schema exported to {output_path}")


def cmd_interactive(ctx: CLIContext, out: OutputFormatter) -> None:
    out.info("Interactive Rule Builder")
    print("=" * 40)

    rules: list[Rule] = []
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

        data: dict = {
            "id": f"RULE-{counter:03d}",
            "change_type": change_type.value,
            "version_introduced": version,
            "description": input("Description: ").strip(),
        }

        rename_types = {
            ChangeType.RENAME_FUNCTION,
            ChangeType.RENAME_CLASS,
            ChangeType.RENAME_ATTRIBUTE,
            ChangeType.REPLACE_WITH_PROPERTY,
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
            out.ok(f"Rule added: {rule.change_type} ({rule.id})")
            counter += 1
        except Exception as e:
            out.err(f"Invalid rule: {e}")

    if not rules:
        print("No rules created.")
        return

    output = Path(ctx.args.output or f"rules_{version}.json")
    lib = input("\nLibrary name: ").strip()
    mf = MigrationFile(
        library=lib,
        versions=[VersionChangelog(version=version, rules=rules)],
    )
    output.write_text(mf.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")
    out.ok(f"Saved {len(rules)} rule(s) to {output}")
