"""Celery tasks for migration operations."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from celery import shared_task
from celery.result import AsyncResult

from core.changelog_parser import MigrationRule
from core.migration_engine import TransactionalMigrationEngine
from core.validation import IdempotencyChecker

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="services.tasks.migration_tasks.migrate_code_task",
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
    """
    Migrate source code in a background task.

    Args:
        code: Source code to migrate
        rules_data: List of rule dictionaries
        source_version: Source library version
        target_version: Target library version
        job_id: Optional job identifier

    Returns:
        Migration result dictionary
    """
    try:
        rules = [MigrationRule.from_dict(r) for r in rules_data]
        engine = TransactionalMigrationEngine()
        result = engine.migrate_code(code, rules)

        return {
            "job_id": job_id,
            "status": "completed",
            "transformed_code": result.transformed_code,
            "was_modified": result.was_modified,
            "changes": result.changes,
            "confidence": result.overall_confidence,
        }
    except Exception as exc:
        logger.exception("Migration task failed", job_id=job_id)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="services.tasks.migration_tasks.cleanup_old_jobs",
)
def cleanup_old_jobs(self) -> Dict[str, Any]:
    """
    Periodic task to clean up old migration jobs.
    """
    logger.info("Cleanup old jobs task executed")
    return {"cleaned": 0}


def get_task_result(task_id: str) -> Optional[Dict[str, Any]]:
    """Get result of a Celery task."""
    result = AsyncResult(task_id)
    if result.ready():
        return result.result
    return None