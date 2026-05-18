"""Celery application configuration."""

from __future__ import annotations

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("CELERY_CONFIG_MODULE", "backend.worker.src.celery_app")

celery_app = Celery(
    "migratorgen",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    result_expires=3600,
    task_routes={
        "backend.worker.src.tasks.migration_tasks.migrate_code_task": {"queue": "migration"},
        "backend.worker.src.tasks.migration_tasks.cleanup_old_jobs": {"queue": "maintenance"},
    },
    beat_schedule={
        "cleanup-old-jobs": {
            "task": "backend.worker.src.tasks.migration_tasks.cleanup_old_jobs",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)