"""Configuration management with layered sources: defaults → env → file → kwargs.

Resolution order (last wins):
1. Hard-coded defaults
2. ``MIGRATOR_*`` environment variables
3. TOML / YAML config file (``~/.config/migrator-gen/config.toml``)
4. Programmatic overrides passed to :class:`SDKConfig.build`
"""

from __future__ import annotations

import os
import dataclasses
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Optional


_ENV_PREFIX = "MIGRATOR_"
_DEFAULT_CONFIG_PATHS = [
    Path.home() / ".config" / "migrator_gen" / "config.toml",
    Path.home() / ".migrator-gen.toml",
    Path.cwd() / ".migrator-gen.toml",
]


def _env(name: str, default: str = "") -> str:
    return os.getenv(f"{_ENV_PREFIX}{name}", default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(f"{_ENV_PREFIX}{name}", str(default)))
    except (ValueError, TypeError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(f"{_ENV_PREFIX}{name}")
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


def _load_toml(path: Path) -> dict:
    """Load a TOML config file, returns empty dict on failure."""
    try:
        import tomllib  # Python >= 3.11
    except ImportError:
        try:
            import tomli as tomllib  # third-party fallback
        except ImportError:
            return {}
    try:
        with open(path, "rb") as fh:
            return dict(tomllib.load(fh).get("migrator_gen", {}))
    except (FileNotFoundError, PermissionError, ValueError):
        return {}


@dataclass(frozen=True)
class SDKConfig:
    """Immutable SDK configuration.

    Every field can be set via the corresponding ``MIGRATOR_*``
    environment variable or a TOML config file placed at one of the
    standard locations (``~/.config/migrator-gen/config.toml``,
    ``~/.migrator-gen.toml``, or ``.migrator-gen.toml`` in the current
    directory).

    Example config file (``.migrator-gen.toml``)::

        [migrator-gen]
        base_url = "https://api.migrator-gen.example.com"
        api_key = "sk-..."
        timeout = 60
        log_level = "DEBUG"
    """

    # ── Connection ─────────────────────────────────────────────────────────
    base_url: str = field(default_factory=lambda: _env("BASE_URL", "http://localhost:8000"))
    api_key: Optional[str] = field(default_factory=lambda: os.getenv(f"{_ENV_PREFIX}API_KEY") or None)
    timeout: int = field(default_factory=lambda: _env_int("TIMEOUT", 30))
    max_retries: int = field(default_factory=lambda: _env_int("MAX_RETRIES", 3))

    # ── Execution mode ─────────────────────────────────────────────────────
    mode: str = field(default_factory=lambda: _env("MODE", "auto"))

    # ── Local-engine options ───────────────────────────────────────────────
    transactional: bool = field(default_factory=lambda: _env_bool("TRANSACTIONAL", True))
    interactive_approval: bool = field(default_factory=lambda: _env_bool("INTERACTIVE", False))
    idempotency_check: bool = field(default_factory=lambda: _env_bool("IDEMPOTENCY_CHECK", True))

    # ── Paths ──────────────────────────────────────────────────────────────
    migration_packs_dir: Path = field(
        default_factory=lambda: Path(_env("MIGRATION_PACKS_DIR", "migration-packs")),
    )

    # ── Logging ────────────────────────────────────────────────────────────
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    log_format: str = field(default_factory=lambda: _env("LOG_FORMAT", "pretty"))

    # ── Feature flags ──────────────────────────────────────────────────────
    enable_metrics: bool = field(default_factory=lambda: _env_bool("ENABLE_METRICS", False))
    enable_cache: bool = field(default_factory=lambda: _env_bool("ENABLE_CACHE", False))

    # ── Constructors ───────────────────────────────────────────────────────

    @classmethod
    def build(
        cls,
        *,
        mode: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        config_path: Optional[Path] = None,
        **overrides: Any,
    ) -> SDKConfig:
        """Build config by layering defaults → env → file → explicit kwargs.

        Args:
            mode: Execution mode (``"auto"``, ``"local"``, ``"remote"``).
            base_url: API base URL (required for remote mode).
            api_key: API key for remote mode.
            timeout: Request timeout in seconds.
            max_retries: Max retries for transient failures.
            config_path: Explicit path to a TOML config file.  If omitted
                the standard search paths are tried.
            **overrides: Any other :class:`SDKConfig` field.
        """
        cfg = cls()

        # Layer 1: file
        paths = [config_path] if config_path else _DEFAULT_CONFIG_PATHS
        for p in paths:
            if p and p.exists():
                file_cfg = _load_toml(p)
                if file_cfg:
                    cfg = replace(cfg, **{k: v for k, v in file_cfg.items() if hasattr(cfg, k)})
                break

        # Layer 2: explicit kwargs
        explicit: dict = {}
        if mode is not None:
            explicit["mode"] = mode
        if base_url is not None:
            explicit["base_url"] = base_url
        if api_key is not None:
            explicit["api_key"] = api_key
        if timeout is not None:
            explicit["timeout"] = timeout
        if max_retries is not None:
            explicit["max_retries"] = max_retries
        explicit.update(overrides)

        if explicit:
            cfg = replace(cfg, **{k: v for k, v in explicit.items() if hasattr(cfg, k)})

        return cfg

    @classmethod
    def local_defaults(cls) -> SDKConfig:
        """Convenience constructor for purely local execution."""
        return cls.build(mode="local", base_url="")

    def to_dict(self) -> Dict[str, Any]:
        """Flatten to a JSON-compatible dict (``Path`` → ``str``)."""
        result: Dict[str, Any] = {}
        for f in dataclasses.fields(self):  # type: ignore[arg-type]
            val = getattr(self, f.name)
            if isinstance(val, Path):
                val = str(val)
            if val is not None:
                result[f.name] = val
        return result

    def to_env(self) -> Dict[str, str]:
        """Export as environment-variable dict for subprocesses."""
        return {f"{_ENV_PREFIX}{k.upper()}": str(v) for k, v in self.to_dict().items()}



