"""Migration service — wraps SDK SyncMigrationClient for CLI use."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from migrator_gen import (
    DiffPreview,
    MigrateResponse,
    MigrationFile,
    Rule,
    SyncMigrationClient,
    ValidationReport,
)


class MigrationService:
    """Thin wrapper around SyncMigrationClient tailored for CLI commands."""

    def __init__(self, config_path: str | None = None) -> None:
        kwargs: dict[str, Any] = {"mode": "local"}
        if config_path:
            kwargs["config_path"] = config_path
        self._client = SyncMigrationClient(**kwargs)

    @property
    def client(self) -> SyncMigrationClient:
        return self._client

    def parse_changelog(self, path: str | Path) -> MigrationFile:
        return self._client.parse_changelog(str(path))

    def migrate_code(
        self,
        code: str,
        rules: list[Rule],
        dry_run: bool = False,
    ) -> MigrateResponse:
        return self._client.migrate_code(code, rules, dry_run=dry_run)

    def preview_migration(
        self,
        code: str,
        rules: list[Rule],
    ) -> DiffPreview:
        return self._client.preview_migration(code, rules)

    def validate_rules(self, path: str | Path) -> ValidationReport:
        return self._client.validate_rules(str(path))

    def generate_migrator_package(
        self, library: str, output_dir: str
    ) -> str:
        return self._client.generate_migrator_package(library, output_dir)

    def close(self) -> None:
        self._client.close()
