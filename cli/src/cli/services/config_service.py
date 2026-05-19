"""Config service — load and validate CLI configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a TOML config file and return the [migrator_gen] section."""
    path = Path(path)
    if not path.exists():
        return {}

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return {}

    try:
        with open(path, "rb") as fh:
            config = tomllib.load(fh)
        return dict(config.get("migrator_gen", config))
    except (ValueError, OSError):
        return {}
