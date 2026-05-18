"""
MigratorGen Core - Code migration platform using LibCST
"""

from .changelog_parser import (
    ChangelogParser,
    VersionChangelog,
    MigrationRule,
    ChangeType,
    RuleWhenCondition,
    MigrationFile,
)
from .version_resolver import VersionResolver, MigrationPath
from .transformers import get_transformer, TRANSFORMER_MAP, BaseTransformer
from .migration_engine import (
    MigrationEngine,
    TransactionalMigrationEngine,
    MigrationReport,
    TransformResult,
    RuleApplicationResult,
    TransactionContext,
    ChangeRecord,
)
from .migrator_generator import MigratorGenerator
from .validation import (
    RuleValidator,
    ValidationReport,
    ValidationMessage,
    RuleDependencyGraph,
    IdempotencyChecker,
)
from .symbol_resolver import (
    SymbolResolver,
    ImportGraph,
    Symbol,
    SymbolKind,
    ScopeAwareTransformer,
    ConfidenceScorer,
)
from .diff_analyzer import (
    GitDiffAnalyzer,
    ChangelogToRulesConverter,
    generate_from_git_diff,
    generate_from_changelog,
    export_rules,
)

__all__ = [
    "ChangelogParser",
    "VersionChangelog",
    "MigrationRule",
    "ChangeType",
    "RuleWhenCondition",
    "MigrationFile",
    "VersionResolver",
    "MigrationPath",
    "get_transformer",
    "TRANSFORMER_MAP",
    "BaseTransformer",
    "MigrationEngine",
    "TransactionalMigrationEngine",
    "MigrationReport",
    "TransformResult",
    "RuleApplicationResult",
    "TransactionContext",
    "ChangeRecord",
    "MigratorGenerator",
    "RuleValidator",
    "ValidationReport",
    "ValidationMessage",
    "RuleDependencyGraph",
    "IdempotencyChecker",
    "SymbolResolver",
    "ImportGraph",
    "Symbol",
    "SymbolKind",
    "ScopeAwareTransformer",
    "ConfidenceScorer",
    "GitDiffAnalyzer",
    "ChangelogToRulesConverter",
    "generate_from_git_diff",
    "generate_from_changelog",
    "export_rules",
]