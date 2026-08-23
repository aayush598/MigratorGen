"""Response formatting helpers for MCP tool handlers."""

from __future__ import annotations

import json
from typing import Any


def format_rule_list(rules: list[Any]) -> str:
    """Format a list of rules into a human-readable string with JSON payload."""
    lines = [f"Generated {len(rules)} migration rule(s):\n"]
    for r in rules:
        ct = r.change_type.value if hasattr(r.change_type, "value") else r.change_type
        lines.append(f"- [{ct}] {r.description}")
        if r.old_name and r.new_name:
            lines.append(f"  {r.old_name} -> {r.new_name}")

    rules_json = json.dumps([r.to_dict() for r in rules], indent=2)
    lines.append(f"\n[JSON_RULES]\n{rules_json}\n[/JSON_RULES]")
    return "\n".join(lines)


def format_breaking_changes(risky: list[str], review: list[str], safe: list[str]) -> str:
    """Format breaking changes analysis output."""
    lines = ["Breaking Changes Analysis:\n"]
    if risky:
        lines.append(f"[HIGH RISK] {len(risky)} change(s):")
        lines.extend(f"  {e}" for e in risky)
    if review:
        lines.append(f"\n[REVIEW NEEDED] {len(review)} change(s):")
        lines.extend(f"  {e}" for e in review)
    lines.append(f"\n[SAFE] {len(safe)} non-breaking change(s)")
    return "\n".join(lines)


def format_migration_result(result: Any, dry_run: bool = False) -> str:
    """Format a migration result for human-readable output."""
    if not result.was_modified:
        return "No changes were needed."

    lines = [f"Migration complete ({len(result.changes)} change(s))"]
    for c in result.changes:
        lines.append(f"+ {c}")

    if not dry_run:
        lines.append(f"\n--- Migrated Code ---\n{result.transformed_code}")

    return "\n".join(lines)


def format_validation_report(report: Any) -> str:
    """Format a validation report for human-readable output."""
    lines = [f"Validation {'PASSED' if report.valid else 'FAILED'}"]
    lines.append(
        f"Errors: {report.error_count}, Warnings: {report.warning_count}, Info: {report.info_count}"
    )
    for e in report.errors:
        lines.append(f"[ERROR] [{e.rule_id}] {e.message}")
    for w in report.warnings:
        lines.append(f"[WARNING] [{w.rule_id}] {w.message}")
    return "\n".join(lines)
