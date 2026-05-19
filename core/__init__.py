"""MigratorGen Core — code migration platform using LibCST

All public API symbols are exposed via lazy imports so the package
can be imported without triggering heavy dependency loads.
"""

from __future__ import annotations

from typing import TYPE_CHECKING


def __getattr__(name: str):
    """Lazy-load sub-modules on attribute access."""
    import importlib

    module_map = {
        "ChangelogParser": ".changelog_parser",
        "VersionChangelog": ".changelog_parser",
        "MigrationRule": ".changelog_parser",
        "ChangeType": ".changelog_parser",
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
