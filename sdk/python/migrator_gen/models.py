"""Pydantic models for the migrator_gen SDK.

All SDK methods return instances of these classes.  They are
designed to be JSON-serializable and round-trip safely through
the REST API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════


class ChangeType(str, Enum):
    """Every kind of migration change the engine supports."""

    RENAME_FUNCTION = "rename_function"
    RENAME_CLASS = "rename_class"
    RENAME_ATTRIBUTE = "rename_attribute"
    RENAME_IMPORT = "rename_import"
    RENAME_MODULE = "rename_module"
    RENAME_PARAMETER = "rename_parameter"
    RENAME_ARGUMENT = "rename_argument"
    ADD_ARGUMENT = "add_argument"
    REMOVE_ARGUMENT = "remove_argument"
    CHANGE_ARGUMENT_DEFAULT = "change_argument_default"
    CHANGE_TYPE_ANNOTATION = "change_type_annotation"
    REORDER_ARGUMENTS = "reorder_arguments"
    DEPRECATE_FUNCTION = "deprecate_function"
    DEPRECATE_CLASS = "deprecate_class"
    DEPRECATE_MODULE = "deprecate_module"
    DEPRECATE_PARAMETER = "deprecate_parameter"
    REMOVE_FUNCTION = "remove_function"
    REMOVE_CLASS = "remove_class"
    REPLACE_WITH_PROPERTY = "replace_with_property"
    MOVE_TO_MODULE = "move_to_module"
    MOVE_TO_SUBMODULE = "move_to_submodule"
    MOVE_CLASS_TO_MODULE = "move_class_to_module"
    ADD_DECORATOR = "add_decorator"
    REMOVE_DECORATOR = "remove_decorator"
    CHANGE_DECORATOR = "change_decorator"
    SYNC_TO_ASYNC = "sync_to_async"
    ASYNC_TO_SYNC = "async_to_sync"
    WRAP_IN_CONTEXT_MANAGER = "wrap_in_context_manager"
    WRAP_IN_SYNC_CONTEXT_MANAGER = "wrap_in_sync_context_manager"
    CLASS_SPLIT = "class_split"
    MODULE_SPLIT = "module_split"
    MERGE_CLASSES = "merge_classes"
    MERGE_MODULES = "merge_modules"
    CHANGE_RETURN_TYPE = "change_return_type"
    ENUM_MIGRATION = "enum_migration"
    CHANGE_ENUM_BASE = "change_enum_base"
    DATACLASS_FIELD_ADD = "dataclass_field_add"
    DATACLASS_FIELD_REMOVE = "dataclass_field_remove"
    DATACLASS_FIELD_RENAME = "dataclass_field_rename"
    DATACLASS_FIELD_CHANGE = "dataclass_field_change"


class SafetyLevel(str, Enum):
    """Risk assessment for a rule or result."""

    SAFE = "safe"
    REVIEW_REQUIRED = "review_required"
    RISKY = "risky"


class MigrationStatus(str, Enum):
    """Lifecycle state of an asynchronous migration job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


# ═══════════════════════════════════════════════════════════════════
# Rule definitions
# ═══════════════════════════════════════════════════════════════════


class RuleWhenCondition(BaseModel):
    """Optional context in which a rule should fire."""

    import_context: Optional[List[str]] = None
    imported_from: Optional[str] = None
    inside_class: Optional[str] = None
    inside_function: Optional[str] = None
    has_decorator: Optional[str] = None
    has_annotation: Optional[str] = None
    module_pattern: Optional[str] = None


class Rule(BaseModel):
    """A single migration rule.

    Rules are the atomic unit of migration — each one describes
    one specific code transformation (rename a function, add an
    argument, move a class to a different module, etc.).
    """

    id: str = Field(..., description="Unique rule identifier")
    change_type: ChangeType = Field(..., description="Kind of migration change")
    version_introduced: str = Field(default="X.Y.Z", pattern=r"^[\w.]+$")
    description: str = Field(..., description="Human-readable summary of what this rule does")
    old_name: Optional[str] = None
    new_name: Optional[str] = None
    function_name: Optional[str] = None
    argument_name: Optional[str] = None
    new_argument_name: Optional[str] = None
    default_value: Optional[str] = None
    new_argument_value: Optional[str] = None
    new_order: Optional[List[str]] = None
    old_module: Optional[str] = None
    new_module: Optional[str] = None
    source_module: Optional[str] = None
    target_module: Optional[str] = None
    decorator_name: Optional[str] = None
    replacement: Optional[str] = None
    safety: str = Field(default="safe", pattern=r"^(safe|review_required|risky)$")
    confidence_hint: str = Field(default="high", pattern=r"^(high|medium|low)$")
    when: Optional[RuleWhenCondition] = None
    priority: int = Field(default=0, ge=0)

    model_config = {"use_enum_values": True, "populate_by_name": True}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict, dropping ``None`` fields."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Rule:
        """Deserialize from a plain dict (lenient)."""
        return cls(**data)


class VersionChangelog(BaseModel):
    """Rules belonging to a single library version."""

    version: str
    release_date: Optional[str] = None
    rules: List[Rule] = Field(default_factory=list)


class MigrationFile(BaseModel):
    """A complete migration-pack file representing a library."""

    library: str
    schema_version: str = "1.0"
    versions: List[VersionChangelog] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════


class RuleValidationMessage(BaseModel):
    """A single validation message (error, warning, or info)."""

    rule_id: str
    message: str
    field: Optional[str] = None
    severity: str = Field(default="error")


class ValidationReport(BaseModel):
    """Result of validating a set of rules."""

    valid: bool = Field(default=True)
    errors: List[RuleValidationMessage] = Field(default_factory=list)
    warnings: List[RuleValidationMessage] = Field(default_factory=list)
    info: List[RuleValidationMessage] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def info_count(self) -> int:
        return len(self.info)


# ═══════════════════════════════════════════════════════════════════
# Migration requests / responses
# ═══════════════════════════════════════════════════════════════════


class MigrateRequest(BaseModel):
    """Payload for a code-migration request."""

    source_code: str = Field(..., description="Source code to migrate")
    rules: List[Rule] = Field(..., description="Migration rules to apply")
    source_version: str = Field(default="1.0.0")
    target_version: str = Field(default="latest")
    dry_run: bool = Field(default=False)


class RuleResultSummary(BaseModel):
    """Outcome of applying a single rule."""

    rule_id: str = ""
    rule_description: str = ""
    success: bool = False
    confidence: float = 0.0
    safety: str = "safe"
    changes_made: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    skipped_reason: Optional[str] = None


class MigrateResponse(BaseModel):
    """Result of a code-migration operation."""

    original_code: str = ""
    transformed_code: str = ""
    changes: List[str] = Field(default_factory=list)
    rules_applied: List[str] = Field(default_factory=list)
    average_confidence: float = 0.0
    was_modified: bool = False
    errors: List[str] = Field(default_factory=list)
    rule_results: List[RuleResultSummary] = Field(default_factory=list)
    duration_ms: Optional[float] = None


class MigrationPath(BaseModel):
    """A resolved path from one library version to another."""

    source_version: str
    target_version: str
    is_upgrade: bool = True
    steps: List[tuple] = Field(default_factory=list)
    rule_count: int = 0
    rules: List[Rule] = Field(default_factory=list)


class MigrationReport(BaseModel):
    """Summary of a directory-level migration."""

    source_version: str = ""
    target_version: str = ""
    is_upgrade: bool = True
    files_processed: int = 0
    files_modified: int = 0
    files_failed: int = 0
    files_skipped: int = 0
    total_changes: int = 0
    average_confidence: float = 0.0
    transactions_rolled_back: int = 0
    errors: List[str] = Field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Migration Report: {self.source_version} -> {self.target_version}",
            f"  Processed: {self.files_processed} files",
            f"  Modified:  {self.files_modified} files",
            f"  Failed:    {self.files_failed} files",
            f"  Skipped:   {self.files_skipped} files",
            f"  Changes:   {self.total_changes}",
        ]
        if self.transactions_rolled_back:
            lines.append(f"  Rollbacks: {self.transactions_rolled_back}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Async job models
# ═══════════════════════════════════════════════════════════════════


class MigrationJob(BaseModel):
    """An asynchronous migration job tracked by the system."""

    job_id: str
    status: MigrationStatus
    source_version: str = ""
    target_version: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[MigrateResponse] = None
    rule_count: int = 0
    files_processed: int = 0


# ═══════════════════════════════════════════════════════════════════
# Analysis models
# ═══════════════════════════════════════════════════════════════════


class AnalyzedImport(BaseModel):
    """A single import statement found in source code."""

    module: str
    name: str
    alias: Optional[str] = None


class AnalyzedFunction(BaseModel):
    """A function definition found in source code."""

    name: str
    line: int = 0
    params: List[str] = Field(default_factory=list)
    decorators: List[str] = Field(default_factory=list)


class AnalyzedClass(BaseModel):
    """A class definition found in source code."""

    name: str
    line: int = 0
    bases: List[str] = Field(default_factory=list)
    methods: List[AnalyzedFunction] = Field(default_factory=list)


class AnalyzeResult(BaseModel):
    """Result of analysing source code for migration needs."""

    imports: List[AnalyzedImport] = Field(default_factory=list)
    functions: List[AnalyzedFunction] = Field(default_factory=list)
    classes: List[AnalyzedClass] = Field(default_factory=list)
    suggested_migrations: List[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════════


class HealthStatus(BaseModel):
    """Health-check response."""

    status: str = "healthy"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════
# Registry / Library info
# ═══════════════════════════════════════════════════════════════════


class LibraryInfo(BaseModel):
    """Metadata about a library migration pack."""

    name: str
    description: str = ""
    rule_count: int = 0
    versions: List[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# Diff preview
# ═══════════════════════════════════════════════════════════════════


class DiffPreview(BaseModel):
    """Unified diff preview of a migration."""

    original_code: str = ""
    transformed_code: str = ""
    diff: str = ""
    changes: List[str] = Field(default_factory=list)
    change_count: int = 0
    average_confidence: float = 0.0
    rule_results: List[RuleResultSummary] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# Lightweight dataclass variants (no pydantic dependency needed)
# ═══════════════════════════════════════════════════════════════════


@dataclass
class MigrationStep:
    """A single version step in a migration path."""
    source: str
    target: str
    rules: List[Rule] = field(default_factory=list)


@dataclass
class ResolvedPath:
    """Fully-resolved migration path between two versions."""
    source_version: str = ""
    target_version: str = ""
    steps: List[MigrationStep] = field(default_factory=list)
    is_upgrade: bool = True

    @property
    def rule_count(self) -> int:
        return sum(len(s.rules) for s in self.steps)

    @property
    def all_rules(self) -> List[Rule]:
        return [r for s in self.steps for r in s.rules]
