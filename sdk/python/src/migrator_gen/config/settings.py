from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

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
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return {}
    try:
        with open(path, "rb") as fh:
            config = tomllib.load(fh)
            return dict(config.get("migrator_gen", config))
    except (FileNotFoundError, PermissionError, ValueError):
        return {}


@dataclass(frozen=True)
class SDKConfig:
    base_url: str = field(default_factory=lambda: _env("BASE_URL", "http://localhost:8000"))
    api_key: str | None = field(default_factory=lambda: os.getenv(f"{_ENV_PREFIX}API_KEY") or None)
    timeout: int = field(default_factory=lambda: _env_int("TIMEOUT", 30))
    max_retries: int = field(default_factory=lambda: _env_int("MAX_RETRIES", 3))
    mode: str = field(default_factory=lambda: _env("MODE", "auto"))
    transactional: bool = field(default_factory=lambda: _env_bool("TRANSACTIONAL", True))
    interactive_approval: bool = field(default_factory=lambda: _env_bool("INTERACTIVE", False))
    idempotency_check: bool = field(default_factory=lambda: _env_bool("IDEMPOTENCY_CHECK", True))
    migration_packs_dir: Path = field(
        default_factory=lambda: Path(_env("MIGRATION_PACKS_DIR", "migration-packs")),
    )
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    log_format: str = field(default_factory=lambda: _env("LOG_FORMAT", "pretty"))
    enable_metrics: bool = field(default_factory=lambda: _env_bool("ENABLE_METRICS", False))
    enable_cache: bool = field(default_factory=lambda: _env_bool("ENABLE_CACHE", False))
    request_id: str | None = field(
        default_factory=lambda: os.getenv(f"{_ENV_PREFIX}REQUEST_ID") or None
    )

    @classmethod
    def build(
        cls,
        *,
        mode: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        config_path: Path | None = None,
        **overrides: Any,
    ) -> SDKConfig:
        cfg = cls()

        paths = [config_path] if config_path else _DEFAULT_CONFIG_PATHS
        for p in paths:
            if p and p.exists():
                file_cfg = _load_toml(p)
                if file_cfg:
                    filtered = {k: v for k, v in file_cfg.items() if hasattr(cfg, k)}
                    if filtered:
                        cfg = replace(cfg, **filtered)
                break

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
        return cls.build(mode="local", base_url="")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for f in __import__("dataclasses").fields(self):
            val = getattr(self, f.name)
            if isinstance(val, Path):
                val = str(val)
            if val is not None:
                result[f.name] = val
        return result

    def to_env(self) -> dict[str, str]:
        return {f"{_ENV_PREFIX}{k.upper()}": str(v) for k, v in self.to_dict().items()}
