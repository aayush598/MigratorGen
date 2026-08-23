"""Handlers for all MCP tools — each maps to a migrator-gen SDK operation."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from migrator_gen import Rule, SyncMigrationClient
from migrator_gen.exceptions import SDKError

from ..exceptions import HandlerError
from ..utils.formatting import (
    format_breaking_changes,
    format_migration_result,
    format_rule_list,
    format_validation_report,
)

log = logging.getLogger("migrator-gen.mcp.handlers")


class ToolHandlers:
    """Collection of tool handler methods, each bound to a shared client."""

    def __init__(self, client: SyncMigrationClient) -> None:
        self._client = client

    def generate_rules(self, **kwargs: Any) -> str:
        mode = kwargs.get("mode", "changelog")
        try:
            if mode == "changelog":
                text = kwargs.get("changelog_text", "")
                lib = kwargs.get("library_name", "unknown")
                if not text:
                    return "No changelog text provided."
                result = self._client.generate_rules_from_changelog(text, lib)
                rules = result.rules
            elif mode == "diff":
                old_code = kwargs.get("old_code", "")
                new_code = kwargs.get("new_code", "")
                if not old_code or not new_code:
                    return "Both old_code and new_code are required for diff mode."
                rules = self._client.generate_rules_from_diff(old_code, new_code)
            else:
                return f"Unknown mode: {mode}. Use 'changelog' or 'diff'."
        except SDKError as e:
            raise HandlerError(str(e)) from e

        if not rules:
            return "No migration rules could be generated from the input."
        return format_rule_list(rules)

    def preview_migration(self, **kwargs: Any) -> str:
        source_code = kwargs.get("source_code", "")
        rules_data = kwargs.get("rules", [])
        source_version = kwargs.get("source_version", "1.0.0")
        target_version = kwargs.get("target_version", "latest")

        if not source_code:
            return "No source_code provided."
        rules = self._parse_rules(rules_data)
        if isinstance(rules, str):
            return rules

        try:
            preview = self._client.preview_migration(source_code, rules)
        except SDKError as e:
            raise HandlerError(str(e)) from e

        parts = [f"Preview: {source_version} -> {target_version}"]
        parts.append(
            f"Changes: {preview.change_count}, Confidence: {preview.average_confidence:.0%}"
        )
        parts.append(f"\n--- Diff ---\n{preview.diff}")
        return "\n".join(parts)

    def run_migration(self, **kwargs: Any) -> str:
        source_code = kwargs.get("source_code", "")
        rules_data = kwargs.get("rules", [])
        dry_run = kwargs.get("dry_run", False)

        if not source_code:
            return "No source_code provided."
        rules = self._parse_rules(rules_data)
        if isinstance(rules, str):
            return rules

        try:
            result = self._client.migrate_code(source_code, rules, dry_run=dry_run)
        except SDKError as e:
            raise HandlerError(str(e)) from e

        return format_migration_result(result, dry_run=dry_run)

    def validate_rules(self, **kwargs: Any) -> str:
        rules_file = kwargs.get("rules_file_path", "")

        if not rules_file or not Path(rules_file).exists():
            return f"File not found: {rules_file}"

        try:
            report = self._client.validate_rules(rules_file)
        except SDKError as e:
            raise HandlerError(str(e)) from e

        return format_validation_report(report)

    def analyze_code(self, **kwargs: Any) -> str:
        source_code = kwargs.get("source_code", "")
        if not source_code:
            return "No source_code provided."

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        try:
            tmp.write(source_code)
            tmp.close()
            analysis = self._client.suggest_migrations(tmp.name, "unknown")
        except SDKError as e:
            raise HandlerError(str(e)) from e
        except Exception as exc:
            raise HandlerError(f"Analysis error: {exc}") from exc
        finally:
            Path(tmp.name).unlink(missing_ok=True)

        lines = ["Analysis of source code:\n"]
        if analysis.imports:
            lines.append(f"Imports ({len(analysis.imports)}):")
            for imp in analysis.imports[:30]:
                tag = f"from {imp.module} import {imp.name}" if imp.module else f"import {imp.name}"
                lines.append(f"  {tag}")
        if analysis.functions:
            lines.append(f"\nFunctions ({len(analysis.functions)}):")
            for fn in analysis.functions[:20]:
                params = ", ".join(fn.params)
                lines.append(f"  def {fn.name}({params})")
        if analysis.classes:
            lines.append(f"\nClasses ({len(analysis.classes)}):")
            for cls in analysis.classes:
                lines.append(f"  class {cls.name}")

        return "\n".join(lines)

    def suggest_migrations(self, **kwargs: Any) -> str:
        file_path = kwargs.get("file_path", "")
        dest_lib = kwargs.get("destination_library", "")

        if not file_path or not Path(file_path).exists():
            return f"File not found: {file_path}"

        try:
            analysis = self._client.suggest_migrations(file_path, dest_lib)
        except SDKError as e:
            raise HandlerError(str(e)) from e

        if not analysis.suggested_migrations:
            return f"No known migrations detected for '{dest_lib}' in {file_path}."

        lines = [f"Detected {len(analysis.suggested_migrations)} potential migration(s):\n"]
        for s in analysis.suggested_migrations:
            lines.append(f"- {s}")
        return "\n".join(lines)

    def list_libraries(self, **kwargs: Any) -> str:
        try:
            libraries = self._client.list_libraries()
        except SDKError as e:
            raise HandlerError(str(e)) from e

        if not libraries:
            return "No migration packs found."

        lines = ["Libraries with migration packs:\n"]
        for name, info in libraries.items():
            lines.append(
                f"- **{name}**: {info.get('rule_count', 0)} rules (v{info.get('version', '?')})"
            )
        return "\n".join(lines)

    def explain_breaking_changes(self, **kwargs: Any) -> str:
        rules_data = kwargs.get("rules", [])
        rules = self._parse_rules(rules_data)
        if isinstance(rules, str):
            return rules

        risky: list[str] = []
        review: list[str] = []
        safe: list[str] = []

        for r in rules:
            ct = r.change_type.value if hasattr(r.change_type, "value") else r.change_type
            entry = f"- [{ct}] {r.description}"
            if r.old_name and r.new_name:
                entry += f" ({r.old_name} -> {r.new_name})"
            elif r.old_name:
                entry += f" (removing: {r.old_name})"

            safety = r.safety.value if hasattr(r.safety, "value") else r.safety
            if safety == "risky":
                risky.append(entry)
            elif safety == "review_required":
                review.append(entry)
            else:
                safe.append(entry)

        return format_breaking_changes(risky, review, safe)

    def resolve_path(self, **kwargs: Any) -> str:
        src = kwargs.get("source_version", "")
        tgt = kwargs.get("target_version", "")
        lib = kwargs.get("library_name", "")

        if not src or not tgt or not lib:
            return "Missing required parameters: source_version, target_version, library_name"

        try:
            path = self._client.resolve_path(src, tgt, lib)
        except SDKError as e:
            raise HandlerError(str(e)) from e

        from packaging.version import Version

        direction = "upgrade" if Version(tgt) > Version(src) else "downgrade"
        lines = [f"Migration path: {src} -> {tgt} ({direction})"]
        lines.append(f"Steps: {len(path.steps)}, Rules: {path.rule_count}\n")
        for s in path.steps:
            lines.append(f"  {s.source} -> {s.target}")
        return "\n".join(lines)

    def create_migrator(self, **kwargs: Any) -> str:
        lib = kwargs.get("library_name", "")
        out_dir = kwargs.get("output_dir", ".")

        if not lib:
            return "Missing required parameter: library_name"

        try:
            out_path = self._client.generate_migrator_package(lib, out_dir)
            return (
                f"Migrator package created for '{lib}'!\n"
                f"Output: {out_path}\n\n"
                f"Install: pip install -e {out_path}\n"
                f"Run: python -m {out_path.name} list-versions"
            )
        except SDKError as e:
            raise HandlerError(str(e)) from e

    def _parse_rules(self, data: list[dict[str, Any]]) -> list[Rule] | str:
        try:
            return [Rule.from_dict(r) for r in data]
        except Exception as e:
            return f"Error parsing rules: {e}"
