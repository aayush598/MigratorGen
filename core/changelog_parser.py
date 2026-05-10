"""
Changelog Parser - Parses CHANGELOG.md or structured JSON changelogs
into structured MigrationRule objects that can be used by the migration engine.
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ChangeType(Enum):
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
    CUSTOM_TRANSFORM = "custom_transform"
    ADD_DECORATOR = "add_decorator"
    REMOVE_DECORATOR = "remove_decorator"


@dataclass
class MigrationRule:
    """A single migration rule extracted from a changelog."""
    change_type: ChangeType
    version_introduced: str
    description: str

    # For renames
    old_name: Optional[str] = None
    new_name: Optional[str] = None

    # For argument changes
    function_name: Optional[str] = None
    argument_name: Optional[str] = None
    new_argument_name: Optional[str] = None
    default_value: Optional[str] = None
    argument_position: Optional[int] = None
    new_argument_value: Optional[str] = None
    new_order: Optional[List[str]] = None

    # For import changes
    old_module: Optional[str] = None
    new_module: Optional[str] = None

    # For deprecation / removal
    replacement: Optional[str] = None
    removal_version: Optional[str] = None

    # For decorator changes
    decorator_name: Optional[str] = None

    # For move operations
    source_module: Optional[str] = None
    target_module: Optional[str] = None

    # Extra metadata
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_type": self.change_type.value,
            "version_introduced": self.version_introduced,
            "description": self.description,
            "old_name": self.old_name,
            "new_name": self.new_name,
            "function_name": self.function_name,
            "argument_name": self.argument_name,
            "new_argument_name": self.new_argument_name,
            "default_value": self.default_value,
            "argument_position": self.argument_position,
            "new_argument_value": self.new_argument_value,
            "new_order": self.new_order,
            "old_module": self.old_module,
            "new_module": self.new_module,
            "replacement": self.replacement,
            "removal_version": self.removal_version,
            "decorator_name": self.decorator_name,
            "source_module": self.source_module,
            "target_module": self.target_module,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MigrationRule":
        data = dict(data)
        data["change_type"] = ChangeType(data["change_type"])
        return cls(**data)


@dataclass
class VersionChangelog:
    """All migration rules for a specific version."""
    version: str
    release_date: Optional[str]
    rules: List[MigrationRule] = field(default_factory=list)
    raw_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "release_date": self.release_date,
            "rules": [r.to_dict() for r in self.rules],
            "raw_notes": self.raw_notes,
        }


class ChangelogParser:
    """
    Parses changelog files (JSON) into structured MigrationRule objects.

    Supports:
    1. Structured JSON changelog
    """

    def parse_json(self, content: str) -> List[VersionChangelog]:
        """Parse a structured JSON changelog."""
        data = json.loads(content)
        changelogs = []

        if isinstance(data, list):
            entries = data
        elif isinstance(data, dict) and "versions" in data:
            entries = data["versions"]
        else:
            entries = [data]

        for entry in entries:
            vc = VersionChangelog(
                version=entry["version"],
                release_date=entry.get("release_date"),
                raw_notes=entry.get("notes", ""),
            )
            for rule_data in entry.get("rules", []):
                rule = MigrationRule.from_dict(rule_data)
                vc.rules.append(rule)
            changelogs.append(vc)

        return changelogs

    def parse(self, content: str, fmt: str = "auto") -> List[VersionChangelog]:
        """Auto-detect format and parse changelog."""
        if fmt == "json" or (fmt == "auto" and content.strip().startswith("{")):
            return self.parse_json(content)
        elif fmt == "json_list" or (fmt == "auto" and content.strip().startswith("[")):
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