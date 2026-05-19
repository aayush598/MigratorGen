"""Single entry point for the migrator_gen SDK.

Auto-detects local vs remote mode based on configuration.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

from . import models as m
from .config import SDKConfig
from .exceptions import SDKError

log = logging.getLogger(__name__)


class MigrationClient:
    """Convenient access to the MigratorGen migration platform.

    The client auto-detects the execution mode:

    * ``"local"`` — imports the ``core`` package directly
    * ``"remote"`` — talks to the MigratorGen API via HTTP
    * ``"auto"`` (default) — tries local first, falls back to remote

    Usage::

        from migrator_gen import MigrationClient, Rule, ChangeType

        client = MigrationClient()
        result = client.migrate_code(
            "def old_func(): pass",
            [Rule(id="R1", change_type=ChangeType.RENAME_FUNCTION, ...)],
        )
        print(result.transformed_code)
    """

    def __init__(
        self,
        *,
        mode: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        config_path: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self._config = SDKConfig.build(
            mode=mode,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            config_path=config_path,
            **kwargs,
        )

        self._engine: Optional[Any] = None
        self._client_mode: str = self._config.mode

        self._initialise()

        log.info(
            "MigrationClient initialised (mode=%s, base_url=%s)",
            self._client_mode,
            self._config.base_url,
        )

    # ── Initialisation ───────────────────────────────────────────────────

    def _initialise(self) -> None:
        if self._client_mode == "local":
            self._init_local()
        elif self._client_mode == "remote":
            self._init_remote()
        else:
            # auto — try local, fall back to remote
            if self._can_import_core():
                log.debug("Auto-detected local mode")
                self._client_mode = "local"
                self._init_local()
            elif self._config.base_url:
                log.debug("Auto-detected remote mode")
                self._client_mode = "remote"
                self._init_remote()
            else:
                raise SDKError(
                    "Could not auto-detect execution mode. "
                    "Install `libcst` for local mode or provide `base_url` for remote mode."
                )

    def _can_import_core(self) -> bool:
        try:
            import core  # noqa: F401
            return True
        except ImportError:
            return False

    def _init_local(self) -> None:
        from ._local import LocalEngine
        self._engine = LocalEngine(self._config)

    def _init_remote(self) -> None:
        from ._remote import RemoteClient
        self._engine = RemoteClient(self._config)

    @property
    def config(self) -> SDKConfig:
        return self._config

    @property
    def mode(self) -> str:
        return self._client_mode

    # ── Public API ────────────────────────────────────────────────────────

    def migrate_code(
        self,
        source_code: str,
        rules: List[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        """Apply migration rules to source code.

        Args:
            source_code: Python source code to transform.
            rules: Migration rules to apply.
            source_version: Current version label.
            target_version: Target version label.
            dry_run: If True, return preview without applying changes.

        Returns:
            A :class:`MigrateResponse` with the result.
        """
        return self._engine.migrate_code(
            source_code, rules,
            source_version=source_version,
            target_version=target_version,
            dry_run=dry_run,
        )

    def preview_migration(
        self,
        source_code: str,
        rules: List[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
    ) -> m.DiffPreview:
        """Preview code changes without applying them.

        Returns a :class:`DiffPreview` with a unified diff.
        """
        return self._engine.preview_migration(
            source_code, rules,
            source_version=source_version,
            target_version=target_version,
        )

    def validate_rules(self, rules_file_path: str) -> m.ValidationReport:
        """Validate a rules file at the given path.

        Returns:
            A :class:`ValidationReport` with errors, warnings, and info.
        """
        return self._engine.validate_rules(rules_file_path)

    def parse_changelog(self, file_path: str) -> m.MigrationFile:
        """Parse a changelog or migration-pack file.

        Returns:
            A :class:`MigrationFile` with the parsed versions and rules.
        """
        return self._engine.parse_changelog(file_path)

    def suggest_migrations(
        self,
        file_path: str,
        destination_library: str,
    ) -> m.AnalyzeResult:
        """Analyse a source file and suggest relevant migrations.

        Args:
            file_path: Path to the Python source file.
            destination_library: Target library to migrate toward.

        Returns:
            An :class:`AnalyzeResult` with imports, functions, classes
            and suggested migration strategies.
        """
        return self._engine.suggest_migrations(file_path, destination_library)

    def list_libraries(self) -> Dict[str, Dict[str, Any]]:
        """List all available migration libraries.

        Returns:
            A dict keyed by library name with ``name``, ``version``,
            and ``rule_count`` fields.
        """
        return self._engine.list_libraries()

    def generate_rules_from_diff(
        self,
        old_code: str,
        new_code: str,
        module: str = "",
    ) -> List[m.Rule]:
        """Generate migration rules by comparing old and new code.

        Args:
            old_code: Original source code.
            new_code: Updated source code.
            module: Optional module name prefix.

        Returns:
            A list of :class:`Rule` objects derived from the comparison.
        """
        return self._engine.generate_rules_from_diff(old_code, new_code, module)

    def generate_rules_from_changelog(
        self,
        changelog_text: str,
        library_name: str = "unknown",
    ) -> m.VersionChangelog:
        """Generate migration rules from changelog text.

        Returns:
            A :class:`VersionChangelog` with parsed rules for
            the given library version.
        """
        return self._engine.generate_rules_from_changelog(changelog_text, library_name)

    def resolve_path(
        self,
        source_version: str,
        target_version: str,
        library_name: str,
    ) -> m.ResolvedPath:
        """Resolve the migration path between two library versions.

        Returns:
            A :class:`ResolvedPath` with intermediate steps.
        """
        return self._engine.resolve_path(source_version, target_version, library_name)

    def migrate_file(
        self,
        file_path: str,
        rules: List[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        """Apply migration rules to a file on disk.

        In non-dry-run mode the original file is backed up with a
        ``.bak`` suffix before being overwritten.
        """
        return self._engine.migrate_file(
            file_path, rules,
            source_version=source_version,
            target_version=target_version,
            dry_run=dry_run,
        )

    def generate_migrator_package(
        self,
        library_name: str,
        output_dir: str = ".",
    ) -> str:
        """Generate a migration package for the given library.

        Returns:
            The path to the generated package directory.
        """
        return self._engine.generate_migrator_package(library_name, output_dir)

    def health_check(self) -> m.HealthStatus:
        """Check platform health (local or remote)."""
        return self._engine.health_check()

    def __enter__(self) -> MigrationClient:
        return self

    def __exit__(self, *args: Any) -> None:
        if hasattr(self._engine, "close"):
            self._engine.close()
