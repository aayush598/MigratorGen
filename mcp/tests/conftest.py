"""Test configuration for MCP tests."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_rules_file(tmp_path: Path) -> Path:
    """Create a temporary rules file for testing."""
    import json

    path = tmp_path / "rules.json"
    data = {
        "library": "demo",
        "versions": [
            {
                "version": "2.0.0",
                "release_date": "2025-01-01",
                "rules": [
                    {
                        "id": "W-001",
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
    path.write_text(json.dumps(data, indent=2))
    return path


@pytest.fixture
def sample_source_file(tmp_path: Path) -> Path:
    """Create a temporary Python source file for testing."""
    path = tmp_path / "source.py"
    path.write_text("from demo import connect\nc = connect()\n")
    return path
