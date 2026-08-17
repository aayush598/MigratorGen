"""preview — show unified diff of migration changes."""

from __future__ import annotations

from pathlib import Path

from ..cli.context import CLIContext
from ..cli.output import OutputFormatter


def cmd_preview(ctx: CLIContext, out: OutputFormatter) -> None:
    args = ctx.args
    source_path = Path(args.file)
    if not source_path.exists():
        out.err(f"File not found: {source_path}")

    rules_path = Path(args.rules)
    if not rules_path.exists():
        out.err(f"Rules file not found: {rules_path}")

    client = ctx.client
    source_code = source_path.read_text(encoding="utf-8")

    versions = client.parse_changelog(str(rules_path)).versions
    from_version = getattr(args, "from_version", None)
    to_version = getattr(args, "to_version", None)
    if from_version and from_version != "latest":
        versions = [v for v in versions if v.version >= from_version]
    rules = [r for v in versions for r in v.rules]

    preview = client.preview_migration(source_code, rules)

    if ctx.json_mode:
        out.print_json(preview.model_dump())
    else:
        diff = preview.diff or "(no diff)"
        out.syntax(diff, lang="diff")
