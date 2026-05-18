"""
Changelog Parser - Parses structured JSON changelogs
into structured MigrationRule objects that can be used by the migration engine.
"""

import ast
import re
import json
from enum import Enum
from typing import List, Optional, Dict, Any, Literal, Union, Tuple
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


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
    CHANGE_RETURN_TYPE = "change_return_type"
    REPLACE_WITH_PROPERTY = "replace_with_property"
    MOVE_TO_MODULE = "move_to_module"
    WRAP_IN_CONTEXT_MANAGER = "wrap_in_context_manager"
    ADD_DECORATOR = "add_decorator"
    REMOVE_DECORATOR = "remove_decorator"
    RENAME_ARGUMENT = "rename_argument"
    SYNC_TO_ASYNC = "sync_to_async"
    CLASS_SPLIT = "class_split"
    MODULE_SPLIT = "module_split"
    ENUM_MIGRATION = "enum_migration"
    DATACLASS_FIELD_CHANGE = "dataclass_field_change"


class RuleWhenCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    imported_from: Optional[str] = None
    not_imported_from: Optional[str] = None
    inside_class: Optional[Union[str, List[str]]] = None
    outside_class: Optional[bool] = None
    inside_function: Optional[Union[str, List[str]]] = None
    python_version: Optional[str] = None
    min_python_version: Optional[str] = None
    max_python_version: Optional[str] = None
    has_decorator: Optional[str] = None
    lacks_decorator: Optional[str] = None
    returns_type: Optional[str] = None
    called_from_module: Optional[str] = None
    called_as_method: Optional[bool] = None
    custom_condition: Optional[str] = None


class MigrationRule(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str = Field(..., min_length=1)
    change_type: ChangeType
    version_introduced: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    description: str

    old_name: Optional[str] = None
    new_name: Optional[str] = None
    function_name: Optional[str] = None
    argument_name: Optional[str] = None
    new_argument_name: Optional[str] = None
    default_value: Optional[str] = None
    argument_position: Optional[int] = None
    new_argument_value: Optional[str] = None
    new_order: Optional[List[str]] = None
    old_module: Optional[str] = None
    new_module: Optional[str] = None
    replacement: Optional[str] = None
    removal_version: Optional[str] = None
    decorator_name: Optional[str] = None
    source_module: Optional[str] = None
    target_module: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

    when: Optional[RuleWhenCondition] = None
    priority: int = Field(default=100, ge=0, le=1000)
    depends_on: List[str] = Field(default_factory=list)
    conflicts_with: List[str] = Field(default_factory=list)
    run_after: List[str] = Field(default_factory=list)
    reversible: bool = True
    idempotent_safe: bool = True
    inverse_rule_id: Optional[str] = None

    confidence_hint: Literal["high", "medium", "low"] = "high"
    tags: List[str] = Field(default_factory=list)
    safety: Literal["safe", "review_required", "risky"] = "safe"

    @model_validator(mode="after")
    def check_required_fields(self):
        if self.change_type == ChangeType.RENAME_FUNCTION:
            if not self.old_name or not self.new_name:
                raise ValueError("Missing required field for rename_function: old_name and new_name are required")
        if self.change_type == ChangeType.ADD_ARGUMENT:
            if not self.function_name or not self.argument_name:
                raise ValueError("Missing required field for add_argument: function_name and argument_name are required")
        if self.change_type == ChangeType.CHANGE_ARGUMENT_DEFAULT:
            if not self.argument_name or not self.default_value:
                raise ValueError("Missing required field for change_argument_default: argument_name and default_value are required")
        if self.default_value:
            try:
                ast.parse(self.default_value, mode="eval")
            except SyntaxError as e:
                raise ValueError(f"Invalid Python expression in default_value: {self.default_value}") from e
        return self

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump(exclude_none=True)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MigrationRule":
        if "when" in data and data["when"] is not None:
            data["when"] = RuleWhenCondition(**data["when"])
        return cls(**data)


class VersionChangelog(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    release_date: Optional[str] = None
    rules: List[MigrationRule] = Field(default_factory=list)
    raw_notes: str = ""
    notes: Optional[str] = None

    @model_validator(mode="after")
    def check_conflicting_renames(self):
        seen_renames: Dict[str, str] = {}
        for rule in self.rules:
            if rule.change_type in (ChangeType.RENAME_FUNCTION, ChangeType.RENAME_CLASS, ChangeType.RENAME_ATTRIBUTE):
                if rule.old_name not in seen_renames:
                    seen_renames[rule.old_name] = rule.id
                else:
                    raise ValueError(f"Conflicting rename rule: {rule.old_name} appears twice with different targets: '{seen_renames[rule.old_name]}' vs '{rule.id}'")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)


class MigrationFile(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    library: str
    schema_version: Optional[str] = None
    generated: Optional[str] = None
    versions: List[VersionChangelog] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_duplicate_ids(self):
        all_rules = [r for vc in self.versions for r in vc.rules]
        seen_ids: Dict[str, str] = {}
        for rule in all_rules:
            if rule.id in seen_ids:
                raise ValueError(f"Duplicate rule ID: {rule.id} (first seen in {seen_ids[rule.id]})")
            seen_ids[rule.id] = rule.id
        return self


class ChangelogParser:
    """
    Parses changelog files (JSON) into structured MigrationFile/MigrationRule objects.
    """

    def parse_json(self, content: str) -> List[VersionChangelog]:
        """Parse a structured JSON changelog."""
        data = json.loads(content)

        if isinstance(data, list):
            versions = [VersionChangelog(**v) for v in data]
            mf = MigrationFile(library="unknown", versions=versions)
        else:
            mf = MigrationFile(**data)

        rules = []
        for vc in mf.versions:
            rules.extend(vc.rules)

        from .validation import RuleValidator
        report = RuleValidator().validate_rules(rules)
        if not report.valid:
            errors_str = "\n".join([f"- [Rule {e.rule_id}]: {e.message}" for e in report.errors])
            raise ValueError(f"Rule Capability Validation Failed:\n{errors_str}")

        return mf.versions

    def parse(self, content: str, fmt: str = "auto") -> List[VersionChangelog]:
        """Auto-detect format and parse changelog."""
        if fmt == "json" or (fmt == "auto" and content.strip().startswith(("{", "["))):
            return self.parse_json(content)
        else:
            raise ValueError(f"Unsupported format or could not auto-detect JSON: {fmt}")

    def merge_changelogs(
        self, old: List[VersionChangelog], new: List[VersionChangelog]
    ) -> List[VersionChangelog]:
        """
        Merge two sets of changelogs. New entries take precedence.
        Used to detect what changed between two changelog files.
        """
        old_versions = {vc.version: vc for vc in old}
        new_versions = {vc.version: vc for vc in new}

        added_versions = set(new_versions.keys()) - set(old_versions.keys())
        added = [new_versions[v] for v in added_versions]
        return sorted(added, key=lambda x: _version_key(x.version))


def _version_key(version: str):
    """Convert version string to tuple for sorting."""
    parts = re.findall(r"\d+", version)
    return tuple(int(p) for p in parts)