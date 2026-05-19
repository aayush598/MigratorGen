"""Shared test fixtures."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_rules_file() -> Path:
    """Create a temporary migration_rules.json with sample rules."""
    data = {
        "library": "testlib",
        "versions": [
            {
                "version": "2.0.0",
                "release_date": "2025-01-01",
                "rules": [
                    {
                        "id": "T-001",
                        "change_type": "rename_function",
                        "description": "connect → create_connection",
                        "old_name": "connect",
                        "new_name": "create_connection",
                        "version_introduced": "2.0.0",
                    }
                ],
            }
        ],
    }
    f = tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False)
    json.dump(data, f)
    f.close()
    path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def sample_source_file() -> Path:
    """Create a temporary .py file to migrate."""
    f = tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False)
    f.write("from testlib import connect\nc = connect()\n")
    f.close()
    path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)
    backup = path.with_suffix(path.suffix + ".bak")
    backup.unlink(missing_ok=True)
