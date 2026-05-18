"""
Pydantic models for MigratorGen SDK.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    RENAME_FUNCTION = "rename_function"
    RENAME_CLASS = "rename_class"
    RENAME_ATTRIBUTE = "rename_attribute"
    RENAME_IMPORT = "rename_import"
    ADD_ARGUMENT = "add_argument"
    REMOVE_ARGUMENT = "remove_argument"
    CHANGE_ARGUMENT_DEFAULT = "change_argument_default"
    REORDER_ARGUMENTS = "reorder_arguments"
    DEPRECATE_FUNCTION = "deprecate_function"
    REMOVE_FUNCTION = "remove_function"
    REMOVE_CLASS = "remove_class"
    REPLACE_WITH_PROPERTY = "replace_with_property"
    MOVE_TO_MODULE = "move_to_module"
    ADD_DECORATOR = "add_decorator"
    REMOVE_DECORATOR = "remove_decorator"
    RENAME_ARGUMENT = "rename_argument"
    SYNC_TO_ASYNC = "sync_to_async"
    WRAP_IN_CONTEXT_MANAGER = "wrap_in_context_manager"
    CLASS_SPLIT = "class_split"
    MODULE_SPLIT = "module_split"
    CHANGE_RETURN_TYPE = "change_return_type"
    ENUM_MIGRATION = "enum_migration"
    DATACLASS_FIELD_CHANGE = "dataclass_field_change"


class Rule(BaseModel):
    id: str = Field(..., description="Unique rule identifier")
    change_type: ChangeType = Field(..., description="Type of migration change")
    version_introduced: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: str = Field(..., description="Human-readable description")
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
    safety: str = Field(default="safe", pattern="^(safe|review_required|risky)$")
    confidence_hint: str = Field(default="high", pattern="^(high|medium|low)$")

    model_config = {"use_enum_values": True}


class MigrateRequest(BaseModel):
    source_code: str = Field(..., description="Source code to migrate")
    rules: List[Rule] = Field(..., description="Migration rules to apply")
    source_version: str = Field(..., description="Source version")
    target_version: str = Field(default="latest")
    dry_run: bool = Field(default=False)


class MigrateResponse(BaseModel):
    original_code: str = Field(...)
    transformed_code: str = Field(...)
    changes: List[str] = Field(default_factory=list)
    rules_applied: List[str] = Field(default_factory=list)
    average_confidence: float = Field(default=0.0)
    was_modified: bool = Field(default=False)
    errors: List[str] = Field(default_factory=list)
    rule_results: List[Dict[str, Any]] = Field(default_factory=list)
    duration_ms: Optional[float] = None
    job_id: Optional[str] = None


class ValidationMessage(BaseModel):
    rule_id: str
    message: str
    field: Optional[str] = None
    severity: str = Field(default="error")


class ValidationReport(BaseModel):
    valid: bool = Field(default=True)
    errors: List[ValidationMessage] = Field(default_factory=list)
    warnings: List[ValidationMessage] = Field(default_factory=list)
    info: List[ValidationMessage] = Field(default_factory=list)
    error_count: int = Field(default=0)
    warning_count: int = Field(default=0)
    info_count: int = Field(default=0)


class MigrationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MigrationJob(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    status: MigrationStatus = Field(...)
    source_version: str
    target_version: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    confidence_score: Optional[float] = None
    rules_applied_count: int = Field(default=0)
    bytes_processed: int = Field(default=0)


class Version(BaseModel):
    version: str = Field(...)
    release_date: Optional[str] = None
    rule_count: int = Field(default=0)
    notes: Optional[str] = None


class Library(BaseModel):
    name: str
    description: str
    rule_count: int = Field(default=0)
    versions: List[str] = Field(default_factory=list)


class HealthStatus(BaseModel):
    status: str = Field(default="healthy")
    version: str = Field(default="0.1.0")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    redis: Optional[str] = None
    database: Optional[str] = None
    worker: Optional[str] = None


class DiffPreview(BaseModel):
    diff: str = Field(..., description="Unified diff output")
    change_count: int = Field(default=0)
    rule_details: List[Dict[str, Any]] = Field(default_factory=list)
    average_confidence: float = Field(default=0.0)