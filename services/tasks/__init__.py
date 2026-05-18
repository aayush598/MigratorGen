"""MigratorGen Celery tasks for background processing."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from celery import Task

logger = logging.getLogger(__name__)


class MigrationTask(Task):
    """Base task for migration operations."""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True
    max_retries = 3


def get_celery_app():
    """Get Celery app instance."""
    from services.tasks.celery_app import celery_app
    return celery_app