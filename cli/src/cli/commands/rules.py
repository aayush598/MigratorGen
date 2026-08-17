"""rules / validate-rules / diff-rules — inspect and compare rule sets."""

from __future__ import annotations

from pathlib import Path

from migrator_gen import MigrationFile

from ..cli.context import CLIContext
from ..cli.output import OutputFormatter


def cmd_rules(ctx: CLIContext, out: OutputFormatter) -> None:
    args = ctx.args
    rules_path = Path(args.rules)
    if not rules_path.exists():
        out.err(f"Rules file not found: {rules_path}")

    client = ctx.client
    mf = client.parse_changelog(str(rules_path))

    if ctx.json_mode:
        out.print_json(mf.model_dump())
        return

    out.info(f"Library: {mf.library}")
    for vc in mf.versions:
        date = vc.release_date or ""
        out.info(f"v{vc.version}  {f'({date})' if date else ''}  — {len(vc.rules)} rule(s)")

        rows = []
        for rule in vc.rules:
            ct = rule.change_type.value if hasattr(rule.change_type, "value") else rule.change_type
            old = rule.old_name or ""
            new = rule.new_name or ""
            action = f"{old} → {new}" if old and new else rule.description
            rows.append([rule.id, ct, action, rule.safety])

        out.table(
            title=f"v{vc.version} rules",
            columns=["ID", "Type", "Action", "Safety"],
            rows=rows,
        )


def cmd_validate_rules(ctx: CLIContext, out: OutputFormatter) -> None:
    args = ctx.args
    path = Path(args.file)
    if not path.exists():
        out.err(f"File not found: {path}")

    client = ctx.client

    out.info(f"Validating {path} ...")
    mf = client.parse_changelog(str(path))
    report = client.validate_rules(str(path))

    if ctx.json_mode:
        out.print_json(report.model_dump())
        return

    if report.valid:
        out.ok("All rules are valid.")
    else:
        out.warn(f"{len(report.errors)} error(s):")
        for e in report.errors:
            print(f"  • [{e.rule_id}] {e.message}")

    if report.warnings:
        print(f"\n[WARNINGS] {len(report.warnings)}:")
        for w in report.warnings:
            print(f"  • [{w.rule_id}] {w.message}")

    if not report.valid:
        raise SystemExit(1)


def cmd_diff_rules(ctx: CLIContext, out: OutputFormatter) -> None:
    args = ctx.args
    old_path, new_path = Path(args.old), Path(args.new)
    for p, label in [(old_path, "Old"), (new_path, "New")]:
        if not p.exists():
            out.err(f"{label} rules file not found: {p}")

    old_rules = _rules_by_id(ctx, old_path)
    new_rules = _rules_by_id(ctx, new_path)

    added = set(new_rules) - set(old_rules)
    removed = set(old_rules) - set(new_rules)
    modified = []

    for rid in set(new_rules) & set(old_rules):
        o, n = old_rules[rid], new_rules[rid]
        changes = []
        for field in [
            "old_name", "new_name", "function_name", "argument_name",
            "old_module", "new_module", "safety", "priority",
        ]:
            ov = getattr(o, field, None)
            nv = getattr(n, field, None)
            if ov != nv:
                changes.append(f"  {field}: {ov} -> {nv}")
        if changes:
            modified.append((rid, changes))

    if ctx.json_mode:
        out.print_json({
            "added": list(added),
            "removed": list(removed),
            "modified": [{"id": rid, "changes": ch} for rid, ch in modified],
        })
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
        out.info("No differences found.")


def _rules_by_id(ctx: CLIContext, path: Path) -> dict[str, "Rule"]:
    mf = ctx.client.parse_changelog(str(path))
    return {r.id: r for v in mf.versions for r in v.rules}
