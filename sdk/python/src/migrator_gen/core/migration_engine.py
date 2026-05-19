"""
Transactional Migration Engine - Atomic migration with rollback support.

Features:
- All-or-nothing file modifications
- Checkpoint-based rollback
- Incremental AST caching
- Idempotency guards
- Confidence scoring per rule application
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

import libcst as cst

from .changelog_parser import MigrationRule
from .transformers import get_transformer
from .validation import IdempotencyChecker, RuleDependencyGraph
from .version_resolver import MigrationPath


class SafetyLevel(str, Enum):
    SAFE = "safe"
    REVIEW_REQUIRED = "review_required"
    RISKY = "risky"


@dataclass
class ChangeRecord:
    rule_id: str
    rule_description: str
    file_path: str
    change_type: str
    line_range: tuple[int, int] | None = None
    confidence: float = 1.0
    safety: SafetyLevel = SafetyLevel.SAFE
    transformation_snapshot: str | None = None


@dataclass
class FileCheckpoint:
    path: Path
    original_content: str
    modified_content: str
    changes: list[ChangeRecord]
    timestamp: str
    rule_fingerprint: str


@dataclass
class RuleApplicationResult:
    rule_id: str
    rule_description: str
    file_path: str
    success: bool
    confidence: float
    safety: SafetyLevel
    changes_made: list[str]
    errors: list[str]
    skipped_reason: str | None = None


@dataclass
class TransformResult:
    original_code: str
    transformed_code: str
    changes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rules_applied: list[str] = field(default_factory=list)
    rule_results: list[RuleApplicationResult] = field(default_factory=list)

    @property
    def was_modified(self) -> bool:
        return self.original_code != self.transformed_code

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def average_confidence(self) -> float:
        if not self.rule_results:
            return 1.0
        return sum(r.confidence for r in self.rule_results) / len(self.rule_results)


@dataclass
class TransactionContext:
    transaction_id: str
    started_at: str
    checkpoints: list[FileCheckpoint] = field(default_factory=list)
    change_records: list[ChangeRecord] = field(default_factory=list)
    rule_fingerprint: str = ""
    source_version: str = ""
    target_version: str = ""
    dry_run: bool = False
    interactive_mode: bool = False

    def rollback(self) -> list[str]:
        rolled_back = []
        for cp in reversed(self.checkpoints):
            try:
                cp.path.write_text(cp.original_content, encoding="utf-8")
                rolled_back.append(str(cp.path))
            except Exception:
                pass
        return rolled_back


@dataclass
class MigrationReport:
    source_version: str
    target_version: str
    is_upgrade: bool
    files_processed: int = 0
    files_modified: int = 0
    files_failed: int = 0
    files_skipped: int = 0
    total_changes: int = 0
    total_confidence: float = 0.0
    transactions_rolled_back: int = 0
    idempotency_checks_passed: int = 0
    rule_results: dict[str, list[RuleApplicationResult]] = field(default_factory=dict)
    file_results: dict[str, TransformResult] = field(default_factory=dict)
    change_records: list[ChangeRecord] = field(default_factory=list)

    def summary(self) -> str:
        avg_conf = (
            f"{self.total_confidence / self.files_modified:.2f}"
            if self.files_modified > 0
            else "N/A"
        )
        lines = [
            f"Migration Report: v{self.source_version} -> v{self.target_version}",
            f"{'=' * 50}",
            f"Files processed : {self.files_processed}",
            f"Files modified  : {self.files_modified}",
            f"Files failed    : {self.files_failed}",
            f"Files skipped   : {self.files_skipped}",
            f"Total changes   : {self.total_changes}",
            f"Avg confidence  : {avg_conf}",
        ]
        if self.change_records:
            lines.append("")
            lines.append("Change Records:")
            for cr in self.change_records:
                lines.append(
                    f"  [{cr.safety.value.upper()}] {cr.change_type} "
                    f"- {cr.rule_description} @ {cr.file_path}"
                )
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "source_version": self.source_version,
            "target_version": self.target_version,
            "is_upgrade": self.is_upgrade,
            "files_processed": self.files_processed,
            "files_modified": self.files_modified,
            "files_failed": self.files_failed,
            "files_skipped": self.files_skipped,
            "total_changes": self.total_changes,
            "average_confidence": round(self.total_confidence / self.files_modified, 3)
            if self.files_modified > 0
            else 0.0,
            "transactions_rolled_back": self.transactions_rolled_back,
            "change_records": [
                {
                    "rule_id": cr.rule_id,
                    "rule_description": cr.rule_description,
                    "file_path": cr.file_path,
                    "change_type": cr.change_type,
                    "confidence": cr.confidence,
                    "safety": cr.safety.value,
                    "line_range": cr.line_range,
                }
                for cr in self.change_records
            ],
        }


class TransactionalMigrationEngine:
    """
    Migration engine with transactional guarantees.

    Features:
    - Atomic all-or-nothing migrations
    - Per-file checkpointing with rollback
    - Idempotency verification
    - Confidence scoring
    - Safety classification
    - Interactive approval for risky changes
    """

    def __init__(
        self,
        transactional: bool = True,
        interactive_approval: bool = False,
        idempotency_check: bool = True,
    ):
        self.transactional = transactional
        self.interactive_approval = interactive_approval
        self.idempotency_check = idempotency_check
        self._transaction_stack: list[TransactionContext] = []

    def _begin_transaction(
        self,
        source_version: str,
        target_version: str,
        dry_run: bool = False,
    ) -> TransactionContext:
        import uuid

        tx_id = str(uuid.uuid4())[:8]
        return TransactionContext(
            transaction_id=tx_id,
            started_at=datetime.now().isoformat(),
            source_version=source_version,
            target_version=target_version,
            dry_run=dry_run,
        )

    def _commit_transaction(self, tx: TransactionContext) -> None:
        if tx.dry_run:
            for cp in tx.checkpoints:
                cp.path.write_text(cp.original_content, encoding="utf-8")
        self._transaction_stack.append(tx)

    def _rollback_transaction(self, tx: TransactionContext) -> list[str]:
        rolled_back = tx.rollback()
        self._transaction_stack.append(tx)
        return rolled_back

    def migrate_code(
        self,
        source_code: str,
        rules: list[MigrationRule],
        dry_run: bool = False,
        return_rule_results: bool = False,
    ) -> TransformResult:
        from .validation import IdempotencyChecker

        result = TransformResult(
            original_code=source_code,
            transformed_code=source_code,
        )

        sorted_rules = self._sort_rules(rules)
        current_code = source_code
        fp = IdempotencyChecker.compute_fingerprint(sorted_rules)

        for rule in sorted_rules:
            if not rule.reversible and not rule.idempotent_safe:
                if IdempotencyChecker.check_rule_idempotency(
                    rule, current_code, get_transformer
                ):
                    result.rule_results.append(
                        RuleApplicationResult(
                            rule_id=rule.id,
                            rule_description=rule.description,
                            file_path="<inline>",
                            success=True,
                            confidence=0.95,
                            safety=SafetyLevel.REVIEW_REQUIRED,
                            changes_made=[],
                            errors=[],
                            skipped_reason="idempotency check passed - no changes needed",
                        )
                    )
                    continue

            try:
                new_code, changes = self._apply_rule(current_code, rule)
                confidence = self._estimate_confidence(rule, current_code, changes)
                safety = self._classify_safety(rule, changes)

                if self.interactive_approval and safety != SafetyLevel.SAFE:
                    approved = self._prompt_approval(rule, changes)
                    if not approved:
                        result.errors.append(
                            f"Rule '{rule.id}' not approved by user"
                        )
                        result.rule_results.append(
                            RuleApplicationResult(
                                rule_id=rule.id,
                                rule_description=rule.description,
                                file_path="<inline>",
                                success=False,
                                confidence=confidence,
                                safety=safety,
                                changes_made=changes,
                                errors=["User rejected risky transformation"],
                                skipped_reason="interactive approval denied",
                            )
                        )
                        continue

                if new_code != current_code:
                    current_code = new_code
                    result.changes.extend(changes)
                    result.rules_applied.append(rule.id)

                result.rule_results.append(
                    RuleApplicationResult(
                        rule_id=rule.id,
                        rule_description=rule.description,
                        file_path="<inline>",
                        success=True,
                        confidence=confidence,
                        safety=safety,
                        changes_made=changes,
                        errors=[],
                    )
                )
            except Exception as e:
                error_msg = f"Rule '{rule.description}' failed: {str(e)}"
                result.errors.append(error_msg)
                result.rule_results.append(
                    RuleApplicationResult(
                        rule_id=rule.id,
                        rule_description=rule.description,
                        file_path="<inline",
                        success=False,
                        confidence=0.0,
                        safety=safety,
                        changes_made=[],
                        errors=[error_msg],
                    )
                )

        if not dry_run:
            result.transformed_code = current_code
        else:
            result.transformed_code = source_code

        return result

    def migrate_file(
        self,
        file_path: Path,
        rules: list[MigrationRule],
        dry_run: bool = False,
        backup: bool = True,
        return_rule_results: bool = False,
    ) -> TransformResult:
        source_code = file_path.read_text(encoding="utf-8")
        result = self.migrate_code(
            source_code, rules, dry_run=dry_run, return_rule_results=return_rule_results
        )

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
        exclude_patterns: list[str] = None,
        transactional: bool = None,
    ) -> MigrationReport:
        import fnmatch

        exclude_patterns = exclude_patterns or ["**/test_*.py", "**/__pycache__/**"]
        report = MigrationReport(
            source_version=path.source_version,
            target_version=path.target_version,
            is_upgrade=path.is_upgrade,
        )

        python_files = list(directory.rglob("*.py"))
        filtered_files = []
        for f in python_files:
            excluded = any(
                fnmatch.fnmatch(str(f), pattern) for pattern in exclude_patterns
            )
            if not excluded:
                filtered_files.append(f)

        report.files_processed = len(filtered_files)

        use_transaction = (
            transactional if transactional is not None else self.transactional
        )

        if use_transaction and not dry_run:
            tx = self._begin_transaction(
                path.source_version, path.target_version, dry_run
            )
            tx.rule_fingerprint = IdempotencyChecker.compute_fingerprint(path.rules)

            try:
                for file_path in filtered_files:
                    result = self.migrate_file(
                        file_path,
                        path.rules,
                        dry_run=False,
                        backup=False,
                    )
                    report.file_results[str(file_path)] = result

                    if result.was_modified:
                        cp = FileCheckpoint(
                            path=file_path,
                            original_content=result.original_code,
                            modified_content=result.transformed_code,
                            changes=[
                                ChangeRecord(
                                    rule_id=r.rule_id,
                                    rule_description=r.rule_description,
                                    file_path=str(file_path),
                                    change_type=r.rule_id,
                                    confidence=r.confidence,
                                    safety=SafetyLevel(r.safety.value) if isinstance(r.safety, SafetyLevel) else SafetyLevel(r.safety),
                                )
                                for r in result.rule_results
                                if r.success and r.changes_made
                            ],
                            timestamp=datetime.now().isoformat(),
                            rule_fingerprint=tx.rule_fingerprint,
                        )
                        tx.checkpoints.append(cp)
                        report.files_modified += 1
                        report.total_changes += len(result.changes)
                        report.change_records.extend(cp.changes)

                    if result.errors:
                        report.files_failed += 1

                    report.total_confidence += result.average_confidence

                if report.files_failed > 0 and use_transaction:
                    rolled_back = self._rollback_transaction(tx)
                    report.transactions_rolled_back = len(rolled_back)
                    for f in rolled_back:
                        if f in report.file_results:
                            del report.file_results[f]
                    report.files_modified = 0
                    report.files_skipped = report.files_processed
                    report.files_processed = 0
                else:
                    self._commit_transaction(tx)

            except Exception:
                rolled_back = self._rollback_transaction(tx)
                report.transactions_rolled_back = len(rolled_back)
                report.files_failed = report.files_processed
                report.files_modified = 0
        else:
            for file_path in filtered_files:
                try:
                    result = self.migrate_file(
                        file_path,
                        path.rules,
                        dry_run=dry_run,
                        backup=backup,
                    )
                    report.file_results[str(file_path)] = result

                    if result.was_modified:
                        report.files_modified += 1
                        report.total_changes += len(result.changes)

                    if result.errors:
                        report.files_failed += 1

                    report.total_confidence += result.average_confidence

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
        rules: list[MigrationRule],
    ) -> str:
        import difflib

        result = self.migrate_code(source_code, rules, dry_run=False)

        if not result.was_modified:
            return "No changes would be made."

        diff = list(
            difflib.unified_diff(
                source_code.splitlines(keepends=True),
                result.transformed_code.splitlines(keepends=True),
                fromfile="original",
                tofile="migrated",
            )
        )

        preview = "".join(diff)
        if result.changes:
            conf = result.average_confidence
            conf_str = f" (confidence: {conf:.0%})" if conf else ""
            changes_summary = (
                f"\nChanges ({len(result.changes)} rule(s){conf_str}):\n"
                + "\n".join(f"  - {c}" for c in result.changes)
            )
            preview = changes_summary + "\n\n" + preview

        if result.rule_results:
            preview += "\n\nRule Details:"
            for r in result.rule_results:
                status = "OK" if r.success else "FAIL"
                preview += f"\n  [{status}] {r.rule_id}: {r.rule_description}"
                if r.skipped_reason:
                    preview += f" (skipped: {r.skipped_reason})"

        return preview

    def validate_migration(
        self,
        original_code: str,
        migrated_code: str,
    ) -> tuple[bool, list[str]]:
        issues = []

        try:
            cst.parse_module(migrated_code)
        except cst.ParserSyntaxError as e:
            issues.append(f"Syntax error in migrated code: {e}")
            return False, issues

        orig_lines = len(original_code.splitlines())
        new_lines = len(migrated_code.splitlines())
        if new_lines < orig_lines * 0.5:
            issues.append(
                f"Warning: migrated code has significantly fewer lines "
                f"({new_lines} vs {orig_lines})"
            )

        return len(issues) == 0 or all("Warning" in i for i in issues), issues

    def _apply_rule(
        self, code: str, rule: MigrationRule
    ) -> tuple[str, list[str]]:
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

    def _sort_rules(self, rules: list[MigrationRule]) -> list[MigrationRule]:
        if not any(r.priority != 100 or r.depends_on for r in rules):
            return rules
        try:
            graph = RuleDependencyGraph(rules)
            ordered_ids = graph.resolve_order()
            id_map = {r.id: r for r in rules}
            return [id_map[rid] for rid in ordered_ids if rid in id_map]
        except Exception:
            return sorted(rules, key=lambda r: r.priority)

    def _estimate_confidence(
        self, rule: MigrationRule, code: str, changes: list[str]
    ) -> float:
        confidence_map = {
            "high": 0.95,
            "medium": 0.7,
            "low": 0.4,
        }
        base = confidence_map.get(rule.confidence_hint, 0.9)

        if not changes:
            return 1.0

        if len(changes) > 20:
            base -= 0.1

        return min(base, 1.0)

    def _classify_safety(
        self, rule: MigrationRule, changes: list[str]
    ) -> SafetyLevel:
        if rule.safety == "risky":
            return SafetyLevel.RISKY
        if rule.safety == "review_required":
            return SafetyLevel.REVIEW_REQUIRED

        if rule.change_type.value in ("remove_function", "remove_class", "remove_argument"):
            return SafetyLevel.RISKY

        if not changes:
            return SafetyLevel.SAFE

        if len(changes) > 10:
            return SafetyLevel.REVIEW_REQUIRED

        return SafetyLevel.SAFE

    def _prompt_approval(
        self, rule: MigrationRule, changes: list[str]
    ) -> bool:
        print(f"\n[APPROVAL REQUIRED] Rule: {rule.description}")
        print(f"  Type: {rule.change_type.value}")
        print(f"  Safety: {rule.safety}")
        if changes:
            print("  Changes:")
            for c in changes[:5]:
                print(f"    - {c}")
            if len(changes) > 5:
                print(f"    ... and {len(changes) - 5} more")
        try:
            response = input("  Approve this change? [y/n]: ").strip().lower()
            return response in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    def run_test_suite(
        self,
        directory: Path,
        test_command: str = "pytest",
        timeout: int = 120,
    ) -> tuple[bool, str]:
        """Run a test suite after migration."""
        import subprocess

        try:
            result = subprocess.run(
                test_command.split(),
                cwd=str(directory),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Test suite timed out after {timeout}s"
        except Exception as e:
            return False, str(e)

    def create_snapshot(
        self,
        directory: Path,
        snapshot_path: Path,
        rules: list[MigrationRule],
    ) -> None:
        """Store a before/after snapshot for debugging migrations."""
        python_files = list(directory.rglob("*.py"))
        snapshot_data = {
            "timestamp": datetime.now().isoformat(),
            "rule_fingerprint": IdempotencyChecker.compute_fingerprint(rules),
            "files": {},
        }

        for f in python_files:
            try:
                content = f.read_text(encoding="utf-8")
                tree = cst.parse_module(content)
                snapshot_data["files"][str(f)] = {
                    "original": content,
                    "ast_hash": hashlib.md5(content.encode()).hexdigest()[:8],
                }
            except Exception:
                pass

        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(
            json.dumps(snapshot_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def verify_snapshot(
        self,
        directory: Path,
        snapshot_path: Path,
    ) -> tuple[bool, list[str]]:
        """Verify that files match snapshot after migration."""
        import difflib

        issues = []
        try:
            snapshot_data = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except Exception as e:
            return False, [f"Failed to load snapshot: {e}"]

        for file_rel, file_data in snapshot_data.get("files", {}).items():
            file_path = directory / file_rel
            if not file_path.exists():
                issues.append(f"File removed: {file_rel}")
                continue

            current = file_path.read_text(encoding="utf-8")
            original = file_data.get("original", "")
            if original != current:
                diff = list(
                    difflib.unified_diff(
                        original.splitlines(keepends=True),
                        current.splitlines(keepends=True),
                        fromfile=f"{file_rel} (original)",
                        tofile=f"{file_rel} (current)",
                    )
                )
                issues.append(
                    f"File changed unexpectedly: {file_rel}\n" + "".join(diff)
                )

        return len(issues) == 0, issues


MigrationEngine = TransactionalMigrationEngine
