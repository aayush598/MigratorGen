"""Configuration loader — layered: defaults → env → TOML → programmatic."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..exceptions import ConfigError
from .settings import MCPSettings


def load_settings(config_path: str | Path | None = None) -> MCPSettings:
    """Load settings from layered sources: defaults ← env ← TOML file."""
    kwargs: dict[str, Any] = {}

    # 1. Env vars
    env_map = {
        "MCP_HOST": "host",
        "MCP_PORT": "port",
        "MCP_TRANSPORT": "transport",
        "MCP_LOG_LEVEL": "log_level",
    }
    for env_key, settings_key in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            kwargs[settings_key] = _coerce(settings_key, val)

    # 2. TOML file
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(f"Config file not found: {config_path}")
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                raise ConfigError("tomllib/tomli required to load TOML config")
        raw = path.read_bytes()
        data = tomllib.loads(raw.decode("utf-8"))
        mcp_section = data.get("mcp", {})
        if isinstance(mcp_section, dict):
            kwargs.update(mcp_section)

    return MCPSettings(**kwargs)


def merge_settings(base: MCPSettings, overrides: dict[str, Any]) -> MCPSettings:
    """Merge programmatic overrides into a base config."""
    return base.model_copy(update=overrides)


def _coerce(key: str, val: str) -> Any:
    if key in ("port", "max_tool_timeout"):
        return int(val)
    return val
