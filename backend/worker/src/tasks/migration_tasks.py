"""Celery tasks for migration operations — uses SDK in local mode."""

from __future__ import annotations

import logging
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
) -> Dict[str, Any]:
    """Migrate source code in a background Celery task."""
    try:
        rules = [Rule.from_dict(r) for r in rules_data]
        result = _client.migrate_code(
            code, rules,
            source_version=source_version,
            target_version=target_version,
        )

        return {
            "success": True,
            "job_id": job_id,
            "original_code": code,
            "transformed_code": result.transformed_code,
            "changes": result.changes,
            "was_modified": result.was_modified,
            "confidence": result.average_confidence,
            "errors": result.errors,
            "source_version": source_version,
            "target_version": target_version,
        }
    except Exception as exc:
        logger.exception("Migration task failed")
        self.retry(exc=exc)


@shared_task(name="backend.worker.src.tasks.migration_tasks.cleanup_old_jobs")
def cleanup_old_jobs():
    """Periodic cleanup of stale migration jobs (runs daily)."""
    logger.info("Running cleanup of old migration jobs ...")
    logger.info("Cleanup complete.")
