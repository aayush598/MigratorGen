"""migrate / run — apply migration to a file or directory."""

from __future__ import annotations

import json
from pathlib import Path

from ..cli.context import CLIContext
from ..cli.output import OutputFormatter


def cmd_migrate(ctx: CLIContext, out: OutputFormatter) -> None:
    args = ctx.args
    source_path = Path(args.path)
    if not source_path.exists():
        out.err(f"Source path not found: {source_path}")

    rules_path = Path(args.rules)
    if not rules_path.exists():
        out.err(f"Rules file not found: {rules_path}")

    client = ctx.client

    out.info(f"Loading rules from {rules_path} ...")
    versions = client.parse_changelog(str(rules_path)).versions
    from_version = getattr(args, "from_version", None)
    to_version = getattr(args, "to_version", None)
    if from_version and from_version != "latest":
        versions = [v for v in versions if v.version >= from_version]
    rules = [r for v in versions for r in v.rules]
    out.info(f"Loaded {len(rules)} rule(s) across {len(versions)} version(s)")

    if ctx.json_mode:
        results = []
        files = [source_path] if source_path.is_file() else list(source_path.rglob("*.py"))
        for f in files:
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
        out.print_json({"files": results, "dry_run": args.dry_run})
        return

    if source_path.is_file():
        _migrate_single_file(client, source_path, rules, args.dry_run, out)
    else:
        _migrate_directory(client, source_path, rules, args.dry_run, out)


def _migrate_single_file(client, path: Path, rules, dry_run: bool, out: OutputFormatter) -> None:
    code = path.read_text(encoding="utf-8")
    result = client.migrate_code(code, rules, dry_run=dry_run)

    if not result.was_modified:
        out.info("No changes needed.")
        return

    if not dry_run:
        backup = path.with_suffix(path.suffix + ".bak")
        path.rename(backup)
        path.write_text(result.transformed_code, encoding="utf-8")
        out.ok(f"Modified: {path} (backup: {backup})")
    else:
        out.info(f"Would modify: {path}")

    for c in result.changes:
        print(f"   • {c}")

    if result.errors:
        for e in result.errors:
            out.warn(e)


def _migrate_directory(client, directory: Path, rules, dry_run: bool, out: OutputFormatter) -> None:
    files_modified = 0
    files_failed = 0

    for f in directory.rglob("*.py"):
        try:
            code = f.read_text(encoding="utf-8")
            res = client.migrate_code(code, rules, dry_run=dry_run)
            if res.was_modified:
                files_modified += 1
                if not dry_run:
                    backup = f.with_suffix(f.suffix + ".bak")
                    f.rename(backup)
                    f.write_text(res.transformed_code, encoding="utf-8")
            if res.errors:
                files_failed += 1
        except Exception as exc:
            files_failed += 1
            out.warn(f"Failed {f}: {exc}")

    out.info(f"Processed: modified={files_modified}, failed={files_failed}")

    if dry_run:
        out.info("Dry run — no files were modified.")
