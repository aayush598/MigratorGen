"""migrator_gen.core — SDK domain models, engine protocols, and core migration engine.

The migration engine modules (changelog_parser, transformers, etc.) are
lazy-loaded to avoid importing libcst until it is actually needed.
"""

from __future__ import annotations

from .constants import ChangeType, EngineMode, MigrationStatus, SafetyLevel
from .models import (
    DiffPreview,
    HealthStatus,
    LibraryInfo,
    MigrateResponse,
    MigrationFile,
    MigrationJob,
    MigrationReport,
    MigrationStep,
    ResolvedPath,
    Rule,
    RuleResultSummary,
    RuleWhenCondition,
    ValidationReport,
    VersionChangelog,
)
from .protocols import AbstractAsyncEngine, AbstractEngine, AsyncEngine, Engine

__all__ = [
    "ChangeType",
    "EngineMode",
    "MigrationStatus",
    "SafetyLevel",
    "Rule",
    "RuleWhenCondition",
    "VersionChangelog",
    "MigrationFile",
    "LibraryInfo",
    "RuleResultSummary",
    "MigrateResponse",
    "DiffPreview",
    "ValidationReport",
    "MigrationJob",
    "MigrationReport",
    "MigrationStep",
    "ResolvedPath",
    "HealthStatus",
    "Engine",
    "AsyncEngine",
    "AbstractEngine",
    "AbstractAsyncEngine",
]


def __getattr__(name: str):
    """Lazy-load engine sub-modules on attribute access.

    This allows the ``core`` package to expose engine classes like
    ``ChangelogParser``, ``TransactionalMigrationEngine``,
    ``get_transformer``, etc. without eagerly importing libcst.
    """
    import importlib

    module_map = {
        "ChangelogParser": ".changelog_parser",
        "VersionChangelog": ".changelog_parser",
        "MigrationRule": ".changelog_parser",
        "RuleWhenCondition": ".changelog_parser",
        "MigrationFile": ".changelog_parser",
        "VersionResolver": ".version_resolver",
        "MigrationPath": ".version_resolver",
        "get_transformer": ".transformers",
        "TRANSFORMER_MAP": ".transformers",
        "BaseTransformer": ".transformers",
        "MigrationEngine": ".migration_engine",
        "TransactionalMigrationEngine": ".migration_engine",
        "MigrationReport": ".migration_engine",
        "TransformResult": ".migration_engine",
        "RuleApplicationResult": ".migration_engine",
        "TransactionContext": ".migration_engine",
        "ChangeRecord": ".migration_engine",
        "MigratorGenerator": ".migrator_generator",
        "RuleValidator": ".validation",
        "ValidationReport": ".validation",
        "ValidationMessage": ".validation",
        "RuleDependencyGraph": ".validation",
        "IdempotencyChecker": ".validation",
        "SymbolResolver": ".symbol_resolver",
        "ImportGraph": ".symbol_resolver",
        "Symbol": ".symbol_resolver",
        "SymbolKind": ".symbol_resolver",
        "ScopeAwareTransformer": ".symbol_resolver",
        "ConfidenceScorer": ".symbol_resolver",
        "GitDiffAnalyzer": ".diff_analyzer",
        "ChangelogToRulesConverter": ".diff_analyzer",
        "generate_from_git_diff": ".diff_analyzer",
        "generate_from_changelog": ".diff_analyzer",
        "export_rules": ".diff_analyzer",
    }

    if name in module_map:
        mod = importlib.import_module(module_map[name], __package__)
        return getattr(mod, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
