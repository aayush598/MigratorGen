"""CLI context — shared state across commands."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from migrator_gen import SyncMigrationClient


class CLIContext:
    """Holds parsed args, config, and shared services for the CLI session."""

    def __init__(self, args: Any) -> None:
        self.args = args
        self.json_mode: bool = getattr(args, "json", False)
        self.config_path: str | None = getattr(args, "config", None)
        self._client: SyncMigrationClient | None = None

    @property
    def client(self) -> SyncMigrationClient:
        if self._client is None:
            kwargs: dict[str, Any] = {"mode": "local"}
            if self.config_path:
                kwargs["config_path"] = self.config_path
            self._client = SyncMigrationClient(**kwargs)
        return self._client

    def close(self) -> None:
        if self._client:
            self._client.close()
