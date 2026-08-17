"""Celery tasks for migration operations — uses SDK in local mode."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from celery import shared_task

from migrator_gen import MigrationClient, Rule

logger = logging.getLogger(__name__)

_client = MigrationClient(mode="local")


@shared_task(
    bind=True,
    name="backend.worker.src.tasks.migration_tasks.migrate_code_task",
    max_retries=3,
    default_retry_delay=5,
)
def migrate_code_task(
    self,
    code: str,
    rules_data: List[Dict[str, Any]],
    source_version: str,
    target_version: str,
    job_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Migrate source code in a background Celery task."""
    start = time.perf_counter()
    try:
        rules = [Rule.from_dict(r) for r in rules_data]
        result = _client.migrate_code(
            code, rules,
            source_version=source_version,
            target_version=target_version,
        )
        duration_ms = int((time.perf_counter() - start) * 1000)

        logger.info(
            "migration_task_completed",
            job_id=job_id,
            tenant_id=tenant_id,
            was_modified=result.was_modified,
            changes=len(result.changes),
            duration_ms=duration_ms,
        )

        return {
            "success": True,
            "job_id": job_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "original_code": code,
            "transformed_code": result.transformed_code,
            "changes": result.changes,
            "rules_applied": result.rules_applied,
            "was_modified": result.was_modified,
            "confidence": result.average_confidence,
            "errors": result.errors,
            "source_version": source_version,
            "target_version": target_version,
            "duration_ms": duration_ms,
        }
    except Exception as exc:
        logger.exception("migration_task_failed", job_id=job_id, error=str(exc))
        self.retry(exc=exc)


@shared_task(
    bind=True,
    name="backend.worker.src.tasks.migration_tasks.migrate_directory_task",
    max_retries=2,
    default_retry_delay=10,
)
def migrate_directory_task(
    self,
    directory_path: str,
    rules_data: List[Dict[str, Any]],
    source_version: str,
    target_version: str,
    job_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Migrate all Python files in a directory."""
    from pathlib import Path

    start = time.perf_counter()
    directory = Path(directory_path)
    if not directory.exists():
        return {"success": False, "error": f"Directory not found: {directory_path}"}

    rules = [Rule.from_dict(r) for r in rules_data]
    results = []
    files_modified = 0
    files_failed = 0

    for f in directory.rglob("*.py"):
        try:
            code = f.read_text(encoding="utf-8")
            result = _client.migrate_code(code, rules, source_version=source_version, target_version=target_version)
            results.append({
                "file": str(f),
                "was_modified": result.was_modified,
                "changes": result.changes,
                "errors": result.errors,
            })
            if result.was_modified:
                files_modified += 1
        except Exception as exc:
            files_failed += 1
            results.append({"file": str(f), "was_modified": False, "changes": [], "errors": [str(exc)]})

    duration_ms = int((time.perf_counter() - start) * 1000)

    logger.info(
        "directory_migration_completed",
        job_id=job_id,
        tenant_id=tenant_id,
        files_modified=files_modified,
        files_failed=files_failed,
        duration_ms=duration_ms,
    )

    return {
        "success": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "files": results,
        "files_modified": files_modified,
        "files_failed": files_failed,
        "total_files": len(results),
        "duration_ms": duration_ms,
        "source_version": source_version,
        "target_version": target_version,
    }


@shared_task(
    name="backend.worker.src.tasks.migration_tasks.cleanup_old_jobs",
)
def cleanup_old_jobs():
    """Periodic cleanup of stale migration jobs (runs daily).

    Deletes jobs older than 90 days that are in completed/failed/cancelled state.
    """
    logger.info("cleanup_old_jobs_started")
    deleted_count = 0

    try:
        import asyncio
        from shared.database import get_session, MigrationJob
        from sqlalchemy import delete

        async def _cleanup():
            nonlocal deleted_count
            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            async with get_session() as session:
                result = await session.execute(
                    delete(MigrationJob).where(
                        MigrationJob.status.in_(["completed", "failed", "cancelled"]),
                        MigrationJob.created_at < cutoff,
                    )
                )
                deleted_count = result.rowcount

        asyncio.run(_cleanup())
    except Exception as exc:
        logger.exception("cleanup_old_jobs_failed", error=str(exc))

    logger.info("cleanup_old_jobs_completed", deleted=deleted_count)
    return {"deleted": deleted_count}
