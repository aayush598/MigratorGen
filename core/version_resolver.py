"""
Version Resolver - Determines the correct sequence of migration rules
to apply when migrating from one version to another (any version to any version).
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass
from .changelog_parser import VersionChangelog, MigrationRule, _version_key


@dataclass
class MigrationPath:
    """Represents a migration path from source to target version."""
    source_version: str
    target_version: str
    steps: List[Tuple[str, str]]  # List of (from_version, to_version) steps
    rules: List[MigrationRule]   # Ordered list of all rules to apply
    is_upgrade: bool              # True = upgrade, False = downgrade


class VersionResolver:
    """
    Resolves migration paths between arbitrary versions.
    Supports both upgrades and downgrades.
    """

    def __init__(self, changelogs: List[VersionChangelog]):
        self.changelogs = sorted(changelogs, key=lambda x: _version_key(x.version))
        self._version_map = {vc.version: vc for vc in self.changelogs}

    @property
    def available_versions(self) -> List[str]:
        return [vc.version for vc in self.changelogs]

    def resolve_path(
        self,
        source_version: str,
        target_version: str,
    ) -> MigrationPath:
        """
        Resolve the complete migration path from source to target version.
        Handles:
        - Forward migration (upgrade): applies rules from each intermediate version
        - Backward migration (downgrade): reverses rules in reverse order
        """
        all_versions = self.available_versions

        if source_version not in all_versions and source_version != "0.0.0":
            # Try fuzzy match
            source_version = self._fuzzy_match(source_version, all_versions) or source_version

        if target_version not in all_versions:
            target_version = self._fuzzy_match(target_version, all_versions) or target_version

        src_key = _version_key(source_version)
        tgt_key = _version_key(target_version)

        is_upgrade = tgt_key > src_key

        if is_upgrade:
            # Collect rules from versions AFTER source up to and including target
            applicable = [
                vc for vc in self.changelogs
                if _version_key(vc.version) > src_key
                and _version_key(vc.version) <= tgt_key
            ]
            steps = [
                (self.changelogs[i - 1].version if i > 0 else source_version, vc.version)
                for i, vc in enumerate(applicable)
            ]
            rules = []
            for vc in applicable:
                rules.extend(vc.rules)
        else:
            # Downgrade: collect versions from target+1 to source (reversed)
            applicable = [
                vc for vc in self.changelogs
                if _version_key(vc.version) > tgt_key
                and _version_key(vc.version) <= src_key
            ]
            applicable = list(reversed(applicable))
            steps = [
                (vc.version, self.changelogs[i - 1].version if i > 0 else target_version)
                for i, vc in enumerate(applicable)
            ]
            rules = []
            for vc in applicable:
                # For downgrade, reverse the rules
                reversed_rules = self._reverse_rules(vc.rules)
                rules.extend(reversed_rules)

        return MigrationPath(
            source_version=source_version,
            target_version=target_version,
            steps=steps,
            rules=rules,
            is_upgrade=is_upgrade,
        )

    def _reverse_rules(self, rules: List[MigrationRule]) -> List[MigrationRule]:
        """
        Create inverse rules for downgrade migration.
        Not all rules can be reversed (e.g., removal), those are skipped with a warning.
        """
        from .changelog_parser import ChangeType
        reversed_rules = []

        for rule in reversed(rules):
            if rule.change_type == ChangeType.RENAME_FUNCTION:
                from copy import deepcopy
                r = deepcopy(rule)
                r.old_name, r.new_name = rule.new_name, rule.old_name
                r.description = f"[DOWNGRADE] {rule.description}"
                reversed_rules.append(r)

            elif rule.change_type == ChangeType.RENAME_CLASS:
                from copy import deepcopy
                r = deepcopy(rule)
                r.old_name, r.new_name = rule.new_name, rule.old_name
                r.description = f"[DOWNGRADE] {rule.description}"
                reversed_rules.append(r)

            elif rule.change_type == ChangeType.RENAME_IMPORT:
                from copy import deepcopy
                r = deepcopy(rule)
                r.old_name, r.new_name = rule.new_name, rule.old_name
                r.old_module, r.new_module = rule.new_module, rule.old_module
                r.description = f"[DOWNGRADE] {rule.description}"
                reversed_rules.append(r)

            elif rule.change_type == ChangeType.RENAME_ATTRIBUTE:
                from copy import deepcopy
                r = deepcopy(rule)
                r.old_name, r.new_name = rule.new_name, rule.old_name
                r.description = f"[DOWNGRADE] {rule.description}"
                reversed_rules.append(r)

            elif rule.change_type in (ChangeType.REMOVE_FUNCTION, ChangeType.REMOVE_CLASS):
                # Cannot reverse removal
                print(f"[WARNING] Cannot reverse rule: {rule.description} (removal cannot be undone)")

            else:
                # For complex rules, skip with warning
                print(f"[WARNING] Cannot automatically reverse rule: {rule.description}")

        return reversed_rules

    def _fuzzy_match(self, version: str, available: List[str]) -> Optional[str]:
        """Try to find the closest matching version."""
        # Try prefix match
        for v in available:
            if v.startswith(version) or version.startswith(v):
                return v
        return None

    def get_version_diff(
        self, source_version: str, target_version: str
    ) -> List[VersionChangelog]:
        """Get all VersionChangelog objects between two versions."""
        src_key = _version_key(source_version)
        tgt_key = _version_key(target_version)
        return [
            vc for vc in self.changelogs
            if _version_key(vc.version) > src_key
            and _version_key(vc.version) <= tgt_key
        ]