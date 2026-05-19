"""Config loader — merged from file, env, and defaults."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .settings import CLISettings


def load_settings(config_path: str | None = None) -> CLISettings:
    """Load CLISettings, optionally overlaid with a TOML config file."""
    base = CLISettings()

    if config_path:
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return base

        path = Path(config_path)
        if path.exists():
            try:
                with open(path, "rb") as fh:
                    cfg = tomllib.load(fh)
                migrator_cli = cfg.get("migrator_gen", {})
                if isinstance(migrator_cli, dict):
                    for k, v in migrator_cli.items():
                        if hasattr(base, k):
                            setattr(base, k, v)
            except (ValueError, OSError):
                pass

    return base
