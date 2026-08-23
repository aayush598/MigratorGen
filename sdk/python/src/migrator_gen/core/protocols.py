from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol

from .models import (
    DiffPreview,
    HealthStatus,
    MigrateResponse,
    MigrationFile,
    ResolvedPath,
    Rule,
    ValidationReport,
    VersionChangelog,
)


class Engine(Protocol):
    def migrate_code(
        self,
        source_code: str,
        rules: list[Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> MigrateResponse: ...

    def preview_migration(
        self,
        source_code: str,
        rules: list[Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
    ) -> DiffPreview: ...

    def validate_rules(self, rules_file_path: str) -> ValidationReport: ...

    def parse_changelog(self, file_path: str) -> MigrationFile: ...

    def suggest_migrations(self, file_path: str, destination_library: str) -> Any: ...

    def list_libraries(self) -> dict[str, dict[str, Any]]: ...

    def generate_rules_from_diff(
        self, old_code: str, new_code: str, module: str = ""
    ) -> list[Rule]: ...

    def generate_rules_from_changelog(
        self, changelog_text: str, library_name: str = "unknown"
    ) -> VersionChangelog: ...

    def resolve_path(
        self, source_version: str, target_version: str, library_name: str
    ) -> ResolvedPath: ...

    def migrate_file(
        self,
        file_path: str,
        rules: list[Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> MigrateResponse: ...

    def generate_migrator_package(self, library_name: str, output_dir: str = ".") -> str: ...

    def health_check(self) -> HealthStatus: ...


class AsyncEngine(Protocol):
    async def migrate_code(
        self,
        source_code: str,
        rules: list[Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> MigrateResponse: ...

    async def preview_migration(
        self,
        source_code: str,
        rules: list[Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
    ) -> DiffPreview: ...

    async def validate_rules(self, rules_file_path: str) -> ValidationReport: ...

    async def parse_changelog(self, file_path: str) -> MigrationFile: ...

    async def suggest_migrations(self, file_path: str, destination_library: str) -> Any: ...

    async def list_libraries(self) -> dict[str, dict[str, Any]]: ...

    async def generate_rules_from_diff(
        self, old_code: str, new_code: str, module: str = ""
    ) -> list[Rule]: ...

    async def generate_rules_from_changelog(
        self, changelog_text: str, library_name: str = "unknown"
    ) -> VersionChangelog: ...

    async def resolve_path(
        self, source_version: str, target_version: str, library_name: str
    ) -> ResolvedPath: ...

    async def migrate_file(
        self,
        file_path: str,
        rules: list[Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> MigrateResponse: ...

    async def generate_migrator_package(self, library_name: str, output_dir: str = ".") -> str: ...

    async def health_check(self) -> HealthStatus: ...

    async def close(self) -> None: ...


class AbstractEngine(ABC):
    @abstractmethod
    def migrate_code(
        self,
        source_code: str,
        rules: list[Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> MigrateResponse: ...

    @abstractmethod
    def preview_migration(
        self,
        source_code: str,
        rules: list[Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
    ) -> DiffPreview: ...

    @abstractmethod
    def health_check(self) -> HealthStatus: ...


class AbstractAsyncEngine(ABC):
    @abstractmethod
    async def migrate_code(
        self,
        source_code: str,
        rules: list[Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> MigrateResponse: ...

    @abstractmethod
    async def preview_migration(
        self,
        source_code: str,
        rules: list[Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
    ) -> DiffPreview: ...

    @abstractmethod
    async def health_check(self) -> HealthStatus: ...

    @abstractmethod
    async def close(self) -> None: ...
