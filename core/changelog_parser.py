"""
Changelog Parser - Parses structured JSON changelogs
into structured MigrationRule objects that can be used by the migration engine.
"""

import ast
import re
import json
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
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
    
    tags: List[str] = Field(default_factory=list)
    safety: Literal["safe", "review_required", "risky"] = "safe"

    @field_validator("default_value")
    @classmethod
    def validate_python_expression(cls, v):
        if v is not None:
            try:
                ast.parse(v, mode='eval')
            except Exception as e:
                raise ValueError(f"Invalid Python expression in default_value: {v}")
        return v

    @model_validator(mode="after")
    def validate_semantics(self):
        ct = self.change_type
        missing = []
        
        if ct == ChangeType.RENAME_FUNCTION:
            if not self.old_name: missing.append("old_name")
            if not self.new_name: missing.append("new_name")
        elif ct == ChangeType.RENAME_CLASS:
            if not self.old_name: missing.append("old_name")
            if not self.new_name: missing.append("new_name")
        elif ct == ChangeType.RENAME_ATTRIBUTE:
            if not self.old_name: missing.append("old_name")
            if not self.new_name: missing.append("new_name")
        elif ct == ChangeType.RENAME_IMPORT:
            if not self.old_module: missing.append("old_module")
            if not self.new_module: missing.append("new_module")
            if not self.old_name: missing.append("old_name")
            if not self.new_name: missing.append("new_name")
        elif ct == ChangeType.ADD_ARGUMENT:
            if not self.function_name: missing.append("function_name")
            if not self.argument_name: missing.append("argument_name")
        elif ct == ChangeType.REMOVE_ARGUMENT:
            if not self.function_name: missing.append("function_name")
            if not self.argument_name: missing.append("argument_name")
        elif ct == ChangeType.CHANGE_ARGUMENT_DEFAULT:
            if not self.argument_name: missing.append("argument_name")
            if self.default_value is None: missing.append("default_value")
        elif ct == ChangeType.REORDER_ARGUMENTS:
            if not self.function_name: missing.append("function_name")
            if not self.new_order: missing.append("new_order")
        elif ct == ChangeType.DEPRECATE_FUNCTION:
            if not self.old_name: missing.append("old_name")
        elif ct == ChangeType.MOVE_TO_MODULE:
            if not self.old_name: missing.append("old_name")
            if not self.source_module: missing.append("source_module")
            if not self.target_module: missing.append("target_module")
        elif ct == ChangeType.ADD_DECORATOR:
            if not self.function_name: missing.append("function_name")
            if not self.decorator_name: missing.append("decorator_name")
        elif ct == ChangeType.REMOVE_DECORATOR:
            if not self.function_name: missing.append("function_name")
            if not self.decorator_name: missing.append("decorator_name")
        elif ct == ChangeType.REPLACE_WITH_PROPERTY:
            if not self.old_name: missing.append("old_name")
            if not self.new_name: missing.append("new_name")
            
        if missing:
            raise ValueError(f"Rule {self.id}:\n{ct.value} requires:\n- " + "\n- ".join(missing))
            
        return self

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MigrationRule":
        return cls(**data)


class VersionChangelog(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    release_date: Optional[str] = None
    rules: List[MigrationRule] = Field(default_factory=list)
    raw_notes: str = ""
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)


class MigrationFile(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    library: str
    schema_version: Optional[str] = None
    generated: Optional[str] = None
    versions: List[VersionChangelog] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_rules(self):
        seen_ids = set()
        seen_renames = {}
        for vc in self.versions:
            for rule in vc.rules:
                if rule.id in seen_ids:
                    raise ValueError(f"Duplicate rule ID found: {rule.id}")
                seen_ids.add(rule.id)
                
                # Check for conflicting renames
                if rule.change_type in (ChangeType.RENAME_FUNCTION, ChangeType.RENAME_CLASS, ChangeType.RENAME_ATTRIBUTE):
                    key = (rule.change_type, rule.old_name)
                    if key in seen_renames and seen_renames[key] != rule.new_name:
                        raise ValueError(f"Conflicting rename rule for {rule.old_name}: already renamed to {seen_renames[key]}, but found rename to {rule.new_name}")
                    seen_renames[key] = rule.new_name
                    
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
            return mf.versions
            
        mf = MigrationFile(**data)
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