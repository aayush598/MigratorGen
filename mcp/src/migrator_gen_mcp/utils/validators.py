"""Input validation helpers for MCP tool handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..exceptions import ValidationError


def validate_rules_input(rules_data: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Validate and normalize rules input from tool arguments."""
    if not rules_data:
        raise ValidationError("Missing required field: rules")
    if not isinstance(rules_data, list):
        raise ValidationError("rules must be an array")
    if not rules_data:
        raise ValidationError("rules array is empty")
    for i, r in enumerate(rules_data):
        if not isinstance(r, dict):
            raise ValidationError(f"rules[{i}] must be an object")
        if "change_type" not in r:
            raise ValidationError(f"rules[{i}] missing required field: change_type")
    return rules_data


def validate_file_path(path_str: str | None) -> Path:
    """Validate a file path argument."""
    if not path_str:
        raise ValidationError("Missing required field: file_path")
    path = Path(path_str)
    if not path.exists():
        raise ValidationError(f"File not found: {path}")
    if not path.is_file():
        raise ValidationError(f"Not a file: {path}")
    return path


def validate_version(version: str | None, field_name: str = "version") -> str:
    """Validate a version string."""
    if not version:
        raise ValidationError(f"Missing required field: {field_name}")
    if not isinstance(version, str):
        raise ValidationError(f"{field_name} must be a string")
    import re

    if not re.match(r"^\d+\.\d+\.\d+$", version):
        raise ValidationError(f"Invalid version format: {version} (expected X.Y.Z)")
    return version
