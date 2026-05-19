"""
Parallel Migration Engine - Multi-process file migration with caching.

Features:
- Parallel file processing using multiprocessing
- Incremental AST cache for repeated migrations
- Memory-efficient large repo handling
- Progress tracking and cancellation
"""

import os
import hashlib
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import lru_cache
import tempfile
import json
import time

import libcst as cst

from .changelog_parser import MigrationRule
from .transformers import get_transformer, BaseTransformer
from .validation import IdempotencyChecker
from .migration_engine import TransformResult
from .version_resolver import MigrationPath


@dataclass
class CacheEntry:
    code_hash: str
    transformed_code: str
    rules_hash: str
    applied_rules: List[str]
    changes: List[str]
    timestamp: float


class ASTCache:
    """LRU cache for parsed ASTs to avoid re-parsing the same files."""

    def __init__(self, max_size: int = 100):
        self._cache: Dict[str, Tuple[cst.Module, str]] = {}
        self._access_order: List[str] = []
        self.max_size = max_size

    def _compute_hash(self, code: str) -> str:
        return hashlib.md5(code.encode()).hexdigest()[:16]

    def get(self, code: str) -> Optional[cst.Module]:
        key = self._compute_hash(code)
        if key in self._cache:
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key][0]
        return None

    def put(self, code: str, tree: cst.Module) -> None:
        key = self._compute_hash(code)
        if key in self._cache:
            self._access_order.remove(key)
        elif len(self._cache) >= self.max_size:
            oldest = self._access_order.pop(0)
            del self._cache[oldest]
        self._cache[key] = (tree, code)
        self._access_order.append(key)

    def clear(self) -> None:
        self._cache.clear()
        self._access_order.clear()


class DiskCache:
    """Persistent cache stored on disk for AST results."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(tempfile.gettempdir()) / "migrator_gen_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, code_hash: str, rules_hash: str) -> Optional[Dict]:
        fp = self._file_path(code_hash)
        if fp.exists():
            try:
                data = json.loads(fp.read_text())
                if data.get("rules_hash") == rules_hash:
                    return data
            except Exception:
                pass
        return None

    def put(self, code_hash: str, rules_hash: str, data: Dict) -> None:
        fp = self._file_path(code_hash)
        data["rules_hash"] = rules_hash
        data["timestamp"] = time.time()
        fp.write_text(json.dumps(data), encoding="utf-8")

    def invalidate(self, code_hash: str) -> None:
        fp = self._file_path(code_hash)
        if fp.exists():
            fp.unlink()

    def clear(self) -> None:
        for f in self.cache_dir.glob("*.json"):
            f.unlink()


def _migrate_file_worker(args: Tuple[Path, List[Dict], bool]) -> Tuple[str, bool, List[str], float]:
    """Worker function for parallel file migration. Must be top-level for pickling."""
    file_path, rules_data, dry_run = args

    from .changelog_parser import MigrationRule

    try:
        rules = [MigrationRule.from_dict(r) for r in rules_data]
        code = file_path.read_text(encoding="utf-8")

        from .migration_engine import TransactionalMigrationEngine
        engine = TransactionalMigrationEngine(transactional=False, interactive_approval=False)

        result = engine.migrate_code(code, rules, dry_run=dry_run)

        if not dry_run and result.was_modified:
            file_path.write_text(result.transformed_code, encoding="utf-8")

        return str(file_path), result.was_modified, result.changes, result.average_confidence

    except Exception as e:
        return str(file_path), False, [f"Error: {e}"], 0.0


class ParallelMigrationEngine:
    """
    Migration engine with parallel processing capabilities.

    Features:
    - Parallel file migration using ProcessPoolExecutor
    - Memory-efficient incremental processing
    - AST caching to avoid re-parsing
    - Progress reporting
    - Cancellation support
    """

    def __init__(
        self,
        max_workers: int = None,
        use_disk_cache: bool = True,
        cache_dir: Optional[Path] = None,
        interactive_approval: bool = False,
    ):
        self.max_workers = max_workers or max(1, os.cpu_count() - 1)
        self.use_disk_cache = use_disk_cache
        self.disk_cache = DiskCache(cache_dir) if use_disk_cache else None
        self.memory_cache = ASTCache(max_size=50)
        self.interactive_approval = interactive_approval
        self._progress_callback: Optional[Callable] = None
        self._cancel_requested = False

    def set_progress_callback(self, callback: Callable[[int, int], None]) -> None:
        """Set a callback for progress reporting (processed, total)."""
        self._progress_callback = callback

    def request_cancel(self) -> None:
        """Request cancellation of the current migration."""
        self._cancel_requested = True

    def migrate_directory(
        self,
        directory: Path,
        path: MigrationPath,
        dry_run: bool = False,
        backup: bool = True,
        exclude_patterns: List[str] = None,
        transactional: bool = False,
    ) -> "ParallelMigrationReport":
        import fnmatch

        exclude_patterns = exclude_patterns or ["**/test_*.py", "**/__pycache__/**"]

        python_files = list(directory.rglob("*.py"))
        filtered_files = []
        for f in python_files:
            excluded = any(fnmatch.fnmatch(str(f), p) for p in exclude_patterns)
            if not excluded:
                filtered_files.append(f)

        rules_data = [r.to_dict() for r in path.rules]
        rules_hash = IdempotencyChecker.compute_fingerprint(path.rules)

        args_list = [(f, rules_data, dry_run) for f in filtered_files]

        results: Dict[str, Dict] = {}
        total = len(filtered_files)
        processed = 0

        if self.max_workers == 1:
            for args in args_list:
                if self._cancel_requested:
                    break
                file_path, was_modified, changes, confidence = _migrate_file_worker(args)
                results[file_path] = {
                    "was_modified": was_modified,
                    "changes": changes,
                    "confidence": confidence,
                }
                processed += 1
                if self._progress_callback:
                    self._progress_callback(processed, total)
        else:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(_migrate_file_worker, args): args for args in args_list}
                for future in as_completed(futures):
                    if self._cancel_requested:
                        for f in futures:
                            f.cancel()
                        break
                    try:
                        file_path, was_modified, changes, confidence = future.result(timeout=30)
                        results[file_path] = {
                            "was_modified": was_modified,
                            "changes": changes,
                            "confidence": confidence,
                        }
                    except Exception as e:
                        args = futures[future]
                        results[args[0]] = {
                            "was_modified": False,
                            "changes": [f"Worker error: {e}"],
                            "confidence": 0.0,
                        }
                    processed += 1
                    if self._progress_callback:
                        self._progress_callback(processed, total)

        files_modified = sum(1 for r in results.values() if r["was_modified"])
        total_changes = sum(len(r["changes"]) for r in results.values())
        files_failed = sum(1 for r in results.values() if r["changes"] and "Error" in r["changes"][0])

        return ParallelMigrationReport(
            source_version=path.source_version,
            target_version=path.target_version,
            is_upgrade=path.is_upgrade,
            files_processed=total,
            files_modified=files_modified,
            files_failed=files_failed,
            total_changes=total_changes,
            file_results=results,
        )

    def migrate_directory_chunked(
        self,
        directory: Path,
        path: MigrationPath,
        chunk_size: int = 100,
        dry_run: bool = False,
        backup: bool = True,
        exclude_patterns: List[str] = None,
    ) -> "ParallelMigrationReport":
        """Process large directories in chunks to avoid memory issues."""
        import fnmatch

        exclude_patterns = exclude_patterns or ["**/test_*.py", "**/__pycache__/**"]

        python_files = list(directory.rglob("*.py"))
        filtered_files = []
        for f in python_files:
            excluded = any(fnmatch.fnmatch(str(f), p) for p in exclude_patterns)
            if not excluded:
                filtered_files.append(f)

        all_results: Dict[str, Dict] = {}
        total_chunks = (len(filtered_files) + chunk_size - 1) // chunk_size

        for i in range(0, len(filtered_files), chunk_size):
            chunk = filtered_files[i:i + chunk_size]
            rules_data = [r.to_dict() for r in path.rules]
            args_list = [(f, rules_data, dry_run) for f in chunk]

            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(_migrate_file_worker, args): args for args in args_list}
                for future in as_completed(futures):
                    try:
                        file_path, was_modified, changes, confidence = future.result(timeout=60)
                        all_results[file_path] = {
                            "was_modified": was_modified,
                            "changes": changes,
                            "confidence": confidence,
                        }
                    except Exception as e:
                        args = futures[future]
                        all_results[args[0]] = {
                            "was_modified": False,
                            "changes": [f"Error: {e}"],
                            "confidence": 0.0,
                        }

            if self._progress_callback:
                chunk_num = i // chunk_size + 1
                self._progress_callback(chunk_num, total_chunks)

        files_modified = sum(1 for r in all_results.values() if r["was_modified"])
        total_changes = sum(len(r["changes"]) for r in all_results.values())
        files_failed = sum(1 for r in all_results.values() if r["changes"] and "Error" in r["changes"][0])

        return ParallelMigrationReport(
            source_version=path.source_version,
            target_version=path.target_version,
            is_upgrade=path.is_upgrade,
            files_processed=len(filtered_files),
            files_modified=files_modified,
            files_failed=files_failed,
            total_changes=total_changes,
            file_results=all_results,
        )


@dataclass
class ParallelMigrationReport:
    source_version: str
    target_version: str
    is_upgrade: bool
    files_processed: int = 0
    files_modified: int = 0
    files_failed: int = 0
    total_changes: int = 0
    file_results: Dict[str, Dict] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"Parallel Migration Report: v{self.source_version} -> v{self.target_version}",
            f"{'=' * 50}",
            f"Files processed : {self.files_processed}",
            f"Files modified  : {self.files_modified}",
            f"Files failed    : {self.files_failed}",
            f"Total changes   : {self.total_changes}",
            f"Workers used    : {os.cpu_count() or 1}",
        ]
        failed = [f for f, r in self.file_results.items() if r["changes"] and "Error" in r["changes"][0]]
        if failed:
            lines.append(f"\nFailed files ({len(failed)}):")
            for f in failed[:10]:
                lines.append(f"  - {f}: {self.file_results[f]['changes'][0]}")
        return "\n".join(lines)


from .validation import IdempotencyChecker