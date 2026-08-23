from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from ..config import SDKConfig
from ..core import models as m

log = logging.getLogger(__name__)


class MigrationClient:
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

    async def __aenter__(self) -> MigrationClient:
        await self._initialize()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._engine and hasattr(self._engine, "close"):
            await self._call("close")

    async def _initialize(self) -> None:
        if self._client_mode == "local":
            self._init_local()
        elif self._client_mode == "remote":
            await self._init_remote()
        else:
            if self._config.base_url:
                log.debug("Auto-detected remote mode")
                self._client_mode = "remote"
                await self._init_remote()
            else:
                log.debug("Auto-detected local mode")
                self._client_mode = "local"
                self._init_local()

    def _init_local(self) -> None:
        from ..services import LocalMigrationService

        self._engine = LocalMigrationService(self._config)

    async def _init_remote(self) -> None:
        from ..services import AsyncRemoteService

        self._engine = AsyncRemoteService(self._config)

    @property
    def config(self) -> SDKConfig:
        return self._config

    @property
    def mode(self) -> str:
        return self._client_mode

    async def _call(self, name: str, *args: Any, **kwargs: Any) -> Any:
        method = getattr(self._engine, name)
        result = method(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def migrate_code(
        self,
        source_code: str,
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        return await self._call(
            "migrate_code",
            source_code,
            rules,
            source_version=source_version,
            target_version=target_version,
            dry_run=dry_run,
        )

    async def preview_migration(
        self,
        source_code: str,
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
    ) -> m.DiffPreview:
        return await self._call(
            "preview_migration",
            source_code,
            rules,
            source_version=source_version,
            target_version=target_version,
        )

    async def validate_rules(self, rules_file_path: str) -> m.ValidationReport:
        return await self._call("validate_rules", rules_file_path)

    async def parse_changelog(self, file_path: str) -> m.MigrationFile:
        return await self._call("parse_changelog", file_path)

    async def suggest_migrations(self, file_path: str, destination_library: str) -> Any:
        return await self._call("suggest_migrations", file_path, destination_library)

    async def list_libraries(self) -> dict[str, dict[str, Any]]:
        return await self._call("list_libraries")

    async def generate_rules_from_diff(
        self, old_code: str, new_code: str, module: str = ""
    ) -> list[m.Rule]:
        return await self._call("generate_rules_from_diff", old_code, new_code, module)

    async def generate_rules_from_changelog(
        self, changelog_text: str, library_name: str = "unknown"
    ) -> m.VersionChangelog:
        return await self._call("generate_rules_from_changelog", changelog_text, library_name)

    async def resolve_path(
        self, source_version: str, target_version: str, library_name: str
    ) -> m.ResolvedPath:
        return await self._call("resolve_path", source_version, target_version, library_name)

    async def migrate_file(
        self,
        file_path: str,
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        return await self._call(
            "migrate_file",
            file_path,
            rules,
            source_version=source_version,
            target_version=target_version,
            dry_run=dry_run,
        )

    async def generate_migrator_package(self, library_name: str, output_dir: str = ".") -> str:
        return await self._call("generate_migrator_package", library_name, output_dir)

    async def health_check(self) -> m.HealthStatus:
        return await self._call("health_check")
