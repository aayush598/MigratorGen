"""Validation helpers and constants."""

from __future__ import annotations

import re

STDLIB_MODULES: set[str] = {
    "sys", "os", "re", "json", "math", "time", "datetime",
    "pathlib", "typing", "dataclasses", "collections", "functools",
    "itertools", "abc", "enum", "hashlib", "uuid", "io", "base64",
    "textwrap", "string", "random", "statistics", "bisect",
}

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def is_valid_version(version: str) -> bool:
    return bool(_VERSION_RE.match(version))
