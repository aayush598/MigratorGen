from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..config import SDKConfig
from ..core import models as m

log = logging.getLogger(__name__)


class SyncMigrationClient:
    def __init__(
        self,
        *,
        mode: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        config_path: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._config = SDKConfig.build(
            mode=mode,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            config_path=Path(config_path) if config_path else None,
            **kwargs,
        )
        self._client_mode: str = self._config.mode
        self._engine: Any = None
        self._initialise()
        log.info(
            "SyncMigrationClient initialised (mode=%s, base_url=%s)",
            self._client_mode,
            self._config.base_url,
        )

    def _initialise(self) -> None:
        if self._client_mode == "local":
            self._init_local()
        elif self._client_mode == "remote":
            self._init_remote()
        else:
            # mode="auto": default to local. Remote requires explicit mode="remote".
            log.debug("Auto-detected local mode")
            self._client_mode = "local"
            self._init_local()

    def _init_local(self) -> None:
        from ..services import LocalMigrationService

        self._engine = LocalMigrationService(self._config)

    def _init_remote(self) -> None:
        from ..services import SyncRemoteService

        self._engine = SyncRemoteService(self._config)

    @property
    def config(self) -> SDKConfig:
        return self._config

    @property
    def mode(self) -> str:
        return self._client_mode

    def migrate_code(
        self,
        source_code: str,
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        return self._engine.migrate_code(
            source_code,
            rules,
            source_version=source_version,
            target_version=target_version,
            dry_run=dry_run,
        )

    def preview_migration(
        self,
        source_code: str,
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
    ) -> m.DiffPreview:
        return self._engine.preview_migration(
            source_code, rules, source_version=source_version, target_version=target_version
        )

    def validate_rules(self, rules_file_path: str) -> m.ValidationReport:
        return self._engine.validate_rules(rules_file_path)

    def parse_changelog(self, file_path: str) -> m.MigrationFile:
        return self._engine.parse_changelog(file_path)

    def suggest_migrations(self, file_path: str, destination_library: str) -> Any:
        return self._engine.suggest_migrations(file_path, destination_library)

    def list_libraries(self) -> dict[str, dict[str, Any]]:
        return self._engine.list_libraries()

    def generate_rules_from_diff(
        self, old_code: str, new_code: str, module: str = ""
    ) -> list[m.Rule]:
        return self._engine.generate_rules_from_diff(old_code, new_code, module)

    def generate_rules_from_changelog(
        self, changelog_text: str, library_name: str = "unknown"
    ) -> m.VersionChangelog:
        return self._engine.generate_rules_from_changelog(changelog_text, library_name)

    def resolve_path(
        self, source_version: str, target_version: str, library_name: str
    ) -> m.ResolvedPath:
        return self._engine.resolve_path(source_version, target_version, library_name)

    def migrate_file(
        self,
        file_path: str,
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        return self._engine.migrate_file(
            file_path,
            rules,
            source_version=source_version,
            target_version=target_version,
            dry_run=dry_run,
        )

    def generate_migrator_package(self, library_name: str, output_dir: str = ".") -> str:
        return self._engine.generate_migrator_package(library_name, output_dir)

    def health_check(self) -> m.HealthStatus:
        return self._engine.health_check()

    def close(self) -> None:
        if hasattr(self._engine, "close"):
            self._engine.close()

    def __enter__(self) -> SyncMigrationClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
