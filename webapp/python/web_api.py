"""Web API entry point for the MigratorGen engine running under Pyodide.

Exposes simple functions that JavaScript calls via pyodide.runPython.
All functions accept/return JSON strings to avoid proxy conversion issues.
"""

from __future__ import annotations

import json
import re
import time

from migrator_gen.utils import serialization
from migrator_gen.core.changelog_parser import ChangeType, MigrationRule, VersionChangelog
from migrator_gen.core.migration_engine import TransactionalMigrationEngine
from migrator_gen.core.validation import validate_rules_from_file

_ENGINE = None


def _engine() -> TransactionalMigrationEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = TransactionalMigrationEngine(
            transactional=True,
            interactive_approval=False,
            idempotency_check=False,
        )
    return _ENGINE


_RULE_FIELDS = (
    "id",
    "change_type",
    "version_introduced",
    "description",
    "old_name",
    "new_name",
    "function_name",
    "argument_name",
    "new_argument_name",
    "default_value",
    "argument_position",
    "new_argument_value",
    "new_order",
    "old_module",
    "new_module",
    "source_module",
    "target_module",
    "decorator_name",
    "replacement",
    "removal_version",
    "safety",
    "confidence_hint",
    "when",
    "priority",
    "reversible",
    "depends_on",
    "conflicts_with",
    "run_after",
    "inverse_rule_id",
    "idempotent_safe",
    "tags",
)


def _to_core_rule(raw: dict, default_version: str = "1.0.0", index: int = 0) -> MigrationRule:
    cleaned: dict = {}
    for f in _RULE_FIELDS:
        value = raw.get(f)
        if value is None or value == "":
            continue
        cleaned[f] = value
    if isinstance(cleaned.get("change_type"), str):
        cleaned["change_type"] = ChangeType(cleaned["change_type"])
    if not cleaned.get("id"):
        prefix = str(raw.get("id") or "RULE").upper()[:12] or "RULE"
        cleaned["id"] = f"{prefix}-{index + 1:03d}"
        if not raw.get("id"):
            cleaned["id"] = f"RULE-{index + 1:03d}"
    if not cleaned.get("version_introduced") or not re.match(
        r"^\d+\.\d+\.\d+$", str(cleaned["version_introduced"])
    ):
        cleaned["version_introduced"] = default_version
    return MigrationRule(**cleaned)


def _parse_rules(rules_json: str, default_version: str = "1.0.0") -> list[MigrationRule]:
    rules = json.loads(rules_json)
    if not isinstance(rules, list):
        raise ValueError("rules must be a JSON array")
    fallback = default_version if re.match(r"^\d+\.\d+\.\d+$", default_version) else "1.0.0"
    return [_to_core_rule(r, fallback, i) for i, r in enumerate(rules)]


def preview(source_code: str, rules_json: str, target_version: str = "latest") -> str:
    start = time.monotonic()
    core_rules = _parse_rules(rules_json, target_version)
    result = _engine().migrate_code(source_code, core_rules, return_rule_results=True)
    transformed = getattr(result, "transformed_code", "") or ""
    diff = serialization.compute_diff(source_code, transformed)
    changes = list(result.changes) if hasattr(result, "changes") else []
    rule_results = [
        {
            "rule_id": rr.rule_id,
            "success": bool(rr.success),
            "confidence": float(rr.confidence),
            "changes_made": list(rr.changes_made or []),
            "errors": list(rr.errors or []),
        }
        for rr in getattr(result, "rule_results", [])
    ]
    confidences = [r["confidence"] for r in rule_results if r["success"] and r["changes_made"]]
    payload = {
        "original_code": source_code,
        "transformed_code": transformed,
        "diff": diff,
        "changes": [str(c) for c in changes],
        "change_count": len(changes),
        "average_confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
        "rule_results": rule_results,
        "duration_ms": round((time.monotonic() - start) * 1000, 1),
        "target_version": target_version,
    }
    return json.dumps(payload)


def migrate(source_code: str, rules_json: str, target_version: str = "latest") -> str:
    start = time.monotonic()
    core_rules = _parse_rules(rules_json, target_version)
    result = _engine().migrate_code(source_code, core_rules, return_rule_results=True)
    transformed = getattr(result, "transformed_code", "") or ""
    changes = list(result.changes) if hasattr(result, "changes") else []
    errors = list(getattr(result, "errors", []))
    rule_results = [
        {
            "rule_id": rr.rule_id,
            "success": bool(rr.success),
            "confidence": float(rr.confidence),
            "changes_made": list(rr.changes_made or []),
            "errors": list(rr.errors or []),
        }
        for rr in getattr(result, "rule_results", [])
    ]
    applied = [r["rule_id"] for r in rule_results if r["success"] and r["changes_made"]]
    payload = {
        "original_code": source_code,
        "transformed_code": transformed,
        "changes": [str(c) for c in changes],
        "change_count": len(changes),
        "rules_applied": applied,
        "average_confidence": round(
            sum(r["confidence"] for r in rule_results if r["rule_id"] in applied) / len(applied), 2
        )
        if applied
        else 0.0,
        "was_modified": len(changes) > 0 and transformed != source_code,
        "errors": [str(e) for e in errors],
        "rule_results": rule_results,
        "duration_ms": round((time.monotonic() - start) * 1000, 1),
        "target_version": target_version,
    }
    return json.dumps(payload)


def validate(rules_content_json: str) -> str:
    import tempfile
    import os

    content = json.loads(rules_content_json)
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(content, f)
        report = validate_rules_from_file(path)
        data = report.model_dump() if hasattr(report, "model_dump") else dict(report)
    finally:
        os.unlink(path)

    def _items(key: str, severity: str) -> list[dict]:
        out = []
        for msg in data.get(key, []) or []:
            if isinstance(msg, dict):
                out.append(
                    {
                        "rule_id": msg.get("rule_id", ""),
                        "message": msg.get("message", ""),
                        "severity": severity,
                    }
                )
            else:
                out.append({"rule_id": "", "message": str(msg), "severity": severity})
        return out

    errors = _items("errors", "error")
    warnings = _items("warnings", "warning")
    info = _items("info", "info")
    return json.dumps(
        {
            "valid": data.get("valid", len(errors) == 0),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "info_count": len(info),
            "errors": errors,
            "warnings": warnings,
            "info": info,
        }
    )


def resolve_path(source_version: str, target_version: str, changelog_json: str) -> str:
    from migrator_gen.core.version_resolver import VersionResolver

    raw = json.loads(changelog_json)
    changelogs = []
    for v in raw.get("versions", []):
        rules = [_to_core_rule(r) for r in v.get("rules", [])]
        changelogs.append(
            VersionChangelog(
                version=v.get("version", "0.0.0"),
                release_date=v.get("release_date") or "",
                rules=rules,
            )
        )
    resolver = VersionResolver(changelogs=changelogs)
    path = resolver.resolve_path(source_version, target_version)
    return json.dumps(
        {
            "source_version": path.source_version,
            "target_version": path.target_version,
            "is_upgrade": bool(path.is_upgrade),
            "steps": [{"source": s[0], "target": s[1], "rule_count": 0} for s in path.steps],
            "rule_count": len(path.rules),
        }
    )


def health() -> str:
    return json.dumps({"status": "healthy", "engine": "pyodide", "version": "web-1.0.0"})


CHANGE_TYPES = [c.value for c in ChangeType]
