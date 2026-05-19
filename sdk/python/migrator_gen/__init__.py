"""migrator_gen — Python SDK for the MigratorGen migration platform.

Installation
------------
.. code-block:: bash

    pip install migrator-gen            # basic (pydantic only)
    pip install "migrator-gen[local]"   # + libcst (local transforms)
    pip install "migrator-gen[remote]"  # + httpx (remote API client)
    pip install "migrator-gen[all]"     # everything


Quick Start
-----------
.. code-block:: python

    from migrator_gen import MigrationClient, Rule, ChangeType

    # Auto-detects local (core) or remote (API) mode
    client = MigrationClient()

    rules = [
        Rule(
            id="R001",
            change_type=ChangeType.RENAME_FUNCTION,
            version_introduced="2.0.0",
            description="Rename old_func to new_func",
            old_name="old_func",
            new_name="new_func",
        )
    ]

    result = client.migrate_code("def old_func(): pass", rules)
    print(result.transformed_code)  # def new_func(): pass
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("migrator-gen")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

from .client import MigrationClient
from .config import SDKConfig
from .exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    ConflictError,
    EngineError,
    MigrationError,
    MigrationEngineError,
    MigrationParseError,
    MigrationValidationError,
    NotFoundError,
    RateLimitError,
    SDKError,
    TimeoutError,
    ValidationError,
)
from .models import (
    AnalyzeResult,
    AnalyzedClass,
    AnalyzedFunction,
    AnalyzedImport,
    ChangeType,
    DiffPreview,
    HealthStatus,
    LibraryInfo,
    MigrateRequest,
    MigrateResponse,
    MigrationFile,
    MigrationJob,
    MigrationPath,
    MigrationReport,
    MigrationStatus,
    ResolvedPath,
    MigrationStep,
    Rule,
    RuleResultSummary,
    RuleValidationMessage,
    SafetyLevel,
    ValidationReport,
    VersionChangelog,
)

__all__ = [
    "MigrationClient",
    "SDKConfig",
    "Rule",
    "VersionChangelog",
    "MigrationFile",
    "MigrationPath",
    "MigrationReport",
    "MigrationStatus",
    "MigrationJob",
    "MigrationStep",
    "ResolvedPath",
    "MigrateRequest",
    "MigrateResponse",
    "RuleResultSummary",
    "ValidationReport",
    "RuleValidationMessage",
    "DiffPreview",
    "AnalyzeResult",
    "AnalyzedImport",
    "AnalyzedFunction",
    "AnalyzedClass",
    "HealthStatus",
    "LibraryInfo",
    "ChangeType",
    "SafetyLevel",
    "SDKError",
    "ConfigurationError",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "MigrationError",
    "MigrationParseError",
    "MigrationValidationError",
    "MigrationEngineError",
    "EngineError",
    "TimeoutError",
]
