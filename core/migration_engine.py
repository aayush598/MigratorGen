"""
Migration Engine - Core engine that applies migration rules to source code
using LibCST transformers. Orchestrates the entire transformation pipeline.
"""

import libcst as cst
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from .changelog_parser import MigrationRule, ChangeType
from .transformers import get_transformer, BaseTransformer
from .version_resolver import MigrationPath


@dataclass
class TransformResult:
    """Result of transforming a single file."""
    original_code: str
    transformed_code: str
    changes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    rules_applied: List[str] = field(default_factory=list)

    @property
    def was_modified(self) -> bool:
        return self.original_code != self.transformed_code

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


@dataclass
class MigrationReport:
    """Summary report of an entire migration run."""
    source_version: str
    target_version: str
    files_processed: int = 0
    files_modified: int = 0
    files_failed: int = 0
    total_changes: int = 0
    file_results: Dict[str, TransformResult] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"Migration Report: v{self.source_version} -> v{self.target_version}",
            f"=" * 50,
            f"Files processed : {self.files_processed}",
            f"Files modified  : {self.files_modified}",
            f"Files failed    : {self.files_failed}",
            f"Total changes   : {self.total_changes}",
            "",
        ]
        for path, result in self.file_results.items():
            if result.was_modified or result.errors:
                lines.append(f"  {path}:")
                for change in result.changes:
                    lines.append(f"    ✓ {change}")
                for error in result.errors:
                    lines.append(f"    ✗ {error}")
        return "\n".join(lines)


class MigrationEngine:
    """
    Core migration engine.
    
    Takes a MigrationPath (list of ordered MigrationRules) and applies them
    to Python source code using LibCST transformers.
    
    Supports:
    - Single file migration
    - Directory migration (recursive)
    - Dry-run mode
    """

    def __init__(self):
        pass

    def migrate_code(
        self,
        source_code: str,
        rules: List[MigrationRule],
        dry_run: bool = False,
    ) -> TransformResult:
        """
        Apply a list of migration rules to source code.
        Rules are applied in order.
        """
        result = TransformResult(
            original_code=source_code,
            transformed_code=source_code,
        )

        current_code = source_code

        for rule in rules:
            try:
                new_code, changes = self._apply_rule(current_code, rule)
                if new_code != current_code:
                    current_code = new_code
                    result.changes.extend(changes)
                    result.rules_applied.append(rule.change_type.value)
            except Exception as e:
                error_msg = f"Rule '{rule.description}' failed: {str(e)}"
                result.errors.append(error_msg)

        if not dry_run:
            result.transformed_code = current_code
        else:
            result.transformed_code = source_code  # Don't apply in dry run

        return result

    def _apply_rule(
        self, code: str, rule: MigrationRule
    ) -> Tuple[str, List[str]]:
        """Apply a single rule to code. Returns (new_code, changes_list)."""



        transformer = get_transformer(rule)
        if transformer is None:
            return code, [f"[SKIP] No transformer for {rule.change_type.value}"]

        try:
            tree = cst.parse_module(code)
            new_tree = tree.visit(transformer)
            new_code = new_tree.code
            return new_code, transformer.changes_made
        except cst.ParserSyntaxError as e:
            raise ValueError(f"Syntax error in source: {e}")

    def migrate_file(
        self,
        file_path: Path,
        rules: List[MigrationRule],
        dry_run: bool = False,
        backup: bool = True,
    ) -> TransformResult:
        """Migrate a single Python file in place."""
        source_code = file_path.read_text(encoding="utf-8")
        result = self.migrate_code(source_code, rules, dry_run=dry_run)

        if not dry_run and result.was_modified:
            if backup:
                backup_path = file_path.with_suffix(".py.bak")
                backup_path.write_text(source_code, encoding="utf-8")
            file_path.write_text(result.transformed_code, encoding="utf-8")

        return result

    def migrate_directory(
        self,
        directory: Path,
        path: MigrationPath,
        dry_run: bool = False,
        backup: bool = True,
        exclude_patterns: List[str] = None,
    ) -> MigrationReport:
        """
        Recursively migrate all Python files in a directory.
        """
        exclude_patterns = exclude_patterns or ["**/test_*.py", "**/__pycache__/**"]
        report = MigrationReport(
            source_version=path.source_version,
            target_version=path.target_version,
        )

        python_files = list(directory.rglob("*.py"))

        # Filter excluded patterns
        import fnmatch
        filtered_files = []
        for f in python_files:
            excluded = any(
                fnmatch.fnmatch(str(f), pattern) for pattern in exclude_patterns
            )
            if not excluded:
                filtered_files.append(f)

        report.files_processed = len(filtered_files)

        for file_path in filtered_files:
            try:
                result = self.migrate_file(
                    file_path, path.rules, dry_run=dry_run, backup=backup
                )
                report.file_results[str(file_path)] = result

                if result.was_modified:
                    report.files_modified += 1
                    report.total_changes += len(result.changes)

                if result.errors:
                    report.files_failed += 1

            except Exception as e:
                report.files_failed += 1
                report.file_results[str(file_path)] = TransformResult(
                    original_code="",
                    transformed_code="",
                    errors=[str(e)],
                )

        return report

    def preview_migration(
        self,
        source_code: str,
        rules: List[MigrationRule],
    ) -> str:
        """
        Generate a colored diff preview of what would change.
        """
        import difflib

        result = self.migrate_code(source_code, rules, dry_run=False)

        if not result.was_modified:
            return "No changes would be made."

        diff = list(difflib.unified_diff(
            source_code.splitlines(keepends=True),
            result.transformed_code.splitlines(keepends=True),
            fromfile="original",
            tofile="migrated",
        ))

        preview = "".join(diff)
        if result.changes:
            changes_summary = "\nChanges:\n" + "\n".join(f"  - {c}" for c in result.changes)
            preview = changes_summary + "\n\n" + preview

        return preview

    def validate_migration(
        self,
        original_code: str,
        migrated_code: str,
    ) -> Tuple[bool, List[str]]:
        """
        Validate that the migrated code is syntactically valid.
        Returns (is_valid, list_of_issues)
        """
        issues = []

        try:
            cst.parse_module(migrated_code)
        except cst.ParserSyntaxError as e:
            issues.append(f"Syntax error in migrated code: {e}")
            return False, issues

        # Check that line count is reasonable (sanity check)
        orig_lines = len(original_code.splitlines())
        new_lines = len(migrated_code.splitlines())
        if new_lines < orig_lines * 0.5:
            issues.append(
                f"Warning: migrated code has significantly fewer lines "
                f"({new_lines} vs {orig_lines})"
            )

        return len(issues) == 0 or all("Warning" in i for i in issues), issues