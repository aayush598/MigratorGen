"""
Prometheus metrics for MigratorGen platform.
Provides request, migration, cache, and infrastructure metrics.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Dict, Generator, Optional

try:
    from prometheus_client import Counter, Histogram, Gauge, REGISTRY, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = Gauge = None  # type: ignore
    REGISTRY = None  # type: ignore
    CONTENT_TYPE_LATEST = "text/plain"
    def generate_latest(*args, **kwargs):  # type: ignore
        return b""

def _make_counter(name: str, documentation: str, labelnames: list[str]) -> Any:
    if PROMETHEUS_AVAILABLE and Counter:
        return Counter(name, documentation, labelnames)
    return None


def _make_histogram(name: str, documentation: str, labelnames: list[str], buckets: tuple = None) -> Any:
    if PROMETHEUS_AVAILABLE and Histogram:
        return Histogram(name, documentation, labelnames, buckets=buckets or ())
    return None


def _make_gauge(name: str, documentation: str, labelnames: list[str] = None) -> Any:
    if PROMETHEUS_AVAILABLE and Gauge:
        return Gauge(name, documentation, labelnames or [])
    return None


# Request metrics
HTTP_REQUESTS_TOTAL = _make_counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = _make_histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Migration metrics
MIGRATIONS_TOTAL = _make_counter(
    "migrations_total",
    "Total migration operations",
    ["status", "change_type"],
)

MIGRATIONS_ACTIVE = _make_gauge(
    "migrations_active",
    "Currently active migration operations",
)

MIGRATIONS_BYTES_PROCESSED = _make_counter(
    "migrations_bytes_processed_total",
    "Total bytes processed by migrations",
    [],
)

FILE_MIGRATION_DURATION_SECONDS = _make_histogram(
    "file_migration_duration_seconds",
    "Time to migrate a single file",
    [],
    (0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

# Rules metrics
RULES_APPLIED_TOTAL = _make_counter(
    "rules_applied_total",
    "Total rules applied",
    ["change_type", "confidence"],
)

# Cache metrics
CACHE_HIT_RATIO = _make_gauge(
    "cache_hit_ratio",
    "Cache hit ratio (0-1)",
)

CACHE_OPERATIONS = _make_counter(
    "cache_operations_total",
    "Total cache operations",
    ["operation", "result"],
)

# Worker/Queue metrics
WORKER_QUEUE_DEPTH = _make_gauge(
    "worker_queue_depth",
    "Number of pending migration jobs in queue",
)

CELERY_TASKS_TOTAL = _make_counter(
    "celery_tasks_total",
    "Total Celery task executions",
    ["task_name", "status"],
)

# LLM metrics
LLM_REQUESTS_TOTAL = _make_counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["provider", "status"],
)

LLM_REQUEST_DURATION_SECONDS = _make_histogram(
    "llm_request_duration_seconds",
    "LLM API request duration",
    ["provider"],
    (0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

# Infrastructure metrics
REDIS_CONNECTIONS = _make_gauge(
    "redis_connections",
    "Number of Redis connections",
)

POSTGRES_CONNECTIONS_ACTIVE = _make_gauge(
    "postgres_connections_active",
    "Number of active PostgreSQL connections",
)

PROCESS_MEMORY_MB = _make_gauge(
    "process_memory_mb",
    "Process memory usage in MB",
    ["service"],
)

PROCESS_CPU_PERCENT = _make_gauge(
    "process_cpu_percent",
    "Process CPU usage percentage",
    ["service"],
)


class MetricsCollector:
    """Central metrics collector for MigratorGen."""

    def __init__(self, service_name: str = "migrator-gen"):
        self.service_name = service_name
        self._active_migrations: int = 0
        self._cache_hits: int = 0
        self._cache_misses: int = 0

    def record_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration_seconds: float,
    ) -> None:
        """Record an HTTP request metric."""
        if HTTP_REQUESTS_TOTAL:
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=normalize_endpoint(endpoint),
                status=str(status),
            ).inc()
        if HTTP_REQUEST_DURATION_SECONDS:
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=normalize_endpoint(endpoint),
            ).observe(duration_seconds)

    def record_migration_start(self, change_type: str) -> None:
        """Record start of a migration operation."""
        self._active_migrations += 1
        if MIGRATIONS_ACTIVE:
            MIGRATIONS_ACTIVE.set(self._active_migrations)
        if MIGRATIONS_TOTAL:
            MIGRATIONS_TOTAL.labels(status="started", change_type=change_type).inc()

    def record_migration_complete(
        self,
        status: str,
        change_type: str,
        bytes_processed: int = 0,
    ) -> None:
        """Record completion of a migration operation."""
        self._active_migrations = max(0, self._active_migrations - 1)
        if MIGRATIONS_ACTIVE:
            MIGRATIONS_ACTIVE.set(self._active_migrations)
        if MIGRATIONS_TOTAL:
            MIGRATIONS_TOTAL.labels(status=status, change_type=change_type).inc()
        if bytes_processed > 0 and MIGRATIONS_BYTES_PROCESSED:
            MIGRATIONS_BYTES_PROCESSED.inc(bytes_processed)

    def record_rule_applied(self, change_type: str, confidence: str) -> None:
        """Record a rule application."""
        if RULES_APPLIED_TOTAL:
            RULES_APPLIED_TOTAL.labels(change_type=change_type, confidence=confidence).inc()

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self._cache_hits += 1
        if CACHE_OPERATIONS:
            CACHE_OPERATIONS.labels(operation="get", result="hit").inc()
        self._update_cache_ratio()

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self._cache_misses += 1
        if CACHE_OPERATIONS:
            CACHE_OPERATIONS.labels(operation="get", result="miss").inc()
        self._update_cache_ratio()

    def _update_cache_ratio(self) -> None:
        """Update cache hit ratio gauge."""
        total = self._cache_hits + self._cache_misses
        if total > 0 and CACHE_HIT_RATIO:
            CACHE_HIT_RATIO.set(self._cache_hits / total)

    def record_llm_request(
        self,
        provider: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        """Record an LLM API request."""
        if LLM_REQUESTS_TOTAL:
            LLM_REQUESTS_TOTAL.labels(provider=provider, status=status).inc()
        if LLM_REQUEST_DURATION_SECONDS:
            LLM_REQUEST_DURATION_SECONDS.labels(provider=provider).observe(duration_seconds)

    def record_celery_task(self, task_name: str, status: str) -> None:
        """Record a Celery task execution."""
        if CELERY_TASKS_TOTAL:
            CELERY_TASKS_TOTAL.labels(task_name=task_name, status=status).inc()

    @contextmanager
    def track_migration(self, change_type: str) -> Generator[None, None, None]:
        """Context manager to track migration duration."""
        self.record_migration_start(change_type)
        import time
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            if FILE_MIGRATION_DURATION_SECONDS:
                FILE_MIGRATION_DURATION_SECONDS.observe(duration)
            self.record_migration_complete("completed", change_type)

    def update_queue_depth(self, depth: int) -> None:
        """Update the worker queue depth gauge."""
        if WORKER_QUEUE_DEPTH:
            WORKER_QUEUE_DEPTH.set(depth)


def normalize_endpoint(endpoint: str) -> str:
    """Normalize endpoint paths for metric labels."""
    import re
    endpoint = re.sub(
        r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        '/{id}', endpoint, flags=re.IGNORECASE,
    )
    endpoint = re.sub(r'/\d+', '/{id}', endpoint)
    return endpoint


def setup_metrics(app: Any) -> None:
    """Attach metrics endpoint to a FastAPI application."""
    if not PROMETHEUS_AVAILABLE:
        return
    from fastapi import FastAPI
    from fastapi.responses import Response

    @app.get("/metrics")
    async def metrics():
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )


def track_migration_start(rule_id: str) -> None:
    """Legacy helper - records migration start."""
    metrics.record_migration_start("unknown")


def track_migration_end(rule_id: str, status: str = "completed") -> None:
    """Legacy helper - records migration end."""
    metrics.record_migration_complete(status, "unknown")


metrics = MetricsCollector()