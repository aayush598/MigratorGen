from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any


def compute_diff(original: str, transformed: str, context: int = 3) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            transformed.splitlines(keepends=True),
            fromfile="original",
            tofile="transformed",
            n=context,
        )
    )


def read_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_file(path: str | Path, content: str) -> None:
    Path(path).write_text(content, encoding="utf-8")


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
