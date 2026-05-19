from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .constants import ChangeType, MigrationStatus


class RuleWhenCondition(BaseModel):
    import_context: list[str] | None = None
    imported_from: str | None = None
    inside_class: str | None = None
    inside_function: str | None = None
    has_decorator: str | None = None
    has_annotation: str | None = None
    module_pattern: str | None = None


class Rule(BaseModel):
    id: str = Field(..., description="Unique rule identifier")
    change_type: ChangeType = Field(..., description="Kind of migration change")
    version_introduced: str = Field(default="0.0.0", pattern=r"^[\w.]+$")
    description: str = Field(..., description="Human-readable summary")
    old_name: str | None = None
    new_name: str | None = None
    function_name: str | None = None
    argument_name: str | None = None
    new_argument_name: str | None = None
    default_value: str | None = None
    new_argument_value: str | None = None
    new_order: list[str] | None = None
    old_module: str | None = None
    new_module: str | None = None
    source_module: str | None = None
    target_module: str | None = None
    decorator_name: str | None = None
    replacement: str | None = None
    safety: str = Field(default="safe", pattern=r"^(safe|review_required|risky)$")
    confidence_hint: str = Field(default="high", pattern=r"^(high|medium|low)$")
    when: RuleWhenCondition | None = None
    priority: int = Field(default=0, ge=0)
    depends_on: list[str] | None = None
    conflicts_with: list[str] | None = None
    reversible: bool = True
    idempotent_safe: bool = True

    model_config = {"use_enum_values": True, "populate_by_name": True}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        return cls(**data)


class VersionChangelog(BaseModel):
    version: str
    release_date: str | None = None
    rules: list[Rule] = Field(default_factory=list)


class MigrationFile(BaseModel):
    library: str
    schema_version: str = "1.0"
    versions: list[VersionChangelog] = Field(default_factory=list)


class LibraryInfo(BaseModel):
    name: str
    description: str = ""
    rule_count: int = 0
    versions: list[str] = Field(default_factory=list)


class RuleResultSummary(BaseModel):
    rule_id: str = ""
    rule_description: str = ""
    success: bool = False
    confidence: float = 0.0
    safety: str = "safe"
    changes_made: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    skipped_reason: str | None = None


class MigrateResponse(BaseModel):
    original_code: str = ""
    transformed_code: str = ""
    changes: list[str] = Field(default_factory=list)
    rules_applied: list[str] = Field(default_factory=list)
    average_confidence: float = 0.0
    was_modified: bool = False
    errors: list[str] = Field(default_factory=list)
    rule_results: list[RuleResultSummary] = Field(default_factory=list)
    duration_ms: float | None = None


class DiffPreview(BaseModel):
    original_code: str = ""
    transformed_code: str = ""
    diff: str = ""
    changes: list[str] = Field(default_factory=list)
    change_count: int = 0
    average_confidence: float = 0.0
    rule_results: list[RuleResultSummary] = Field(default_factory=list)


class ValidationReport(BaseModel):
    valid: bool = Field(default=True)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    info: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def info_count(self) -> int:
        return len(self.info)


class MigrationJob(BaseModel):
    job_id: str
    status: MigrationStatus
    source_version: str = ""
    target_version: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error_message: str | None = None
    result: MigrateResponse | None = None
    rule_count: int = 0
    files_processed: int = 0


class MigrationReport(BaseModel):
    source_version: str = ""
    target_version: str = ""
    files_processed: int = 0
    files_modified: int = 0
    files_failed: int = 0
    files_skipped: int = 0
    total_changes: int = 0
    average_confidence: float = 0.0
    transactions_rolled_back: int = 0
    errors: list[str] = Field(default_factory=list)

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


class HealthStatus(BaseModel):
    status: str = "healthy"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


@dataclass
class MigrationStep:
    source: str
    target: str
    rules: list[Rule] = field(default_factory=list)


@dataclass
class ResolvedPath:
    source_version: str = ""
    target_version: str = ""
    steps: list[MigrationStep] = field(default_factory=list)

    @property
    def rule_count(self) -> int:
        return sum(len(s.rules) for s in self.steps)

    @property
    def all_rules(self) -> list[Rule]:
        return [r for s in self.steps for r in s.rules]
