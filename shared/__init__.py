"""Shared library for MigratorGen platform."""

from .logging import setup_logging, get_logger, MigratorLogger
from .exceptions import (
    MigratorBaseException,
    ValidationError,
    RuleValidationError,
    ParsingError,
    MigrationError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    RateLimitError,
    AuthenticationError,
    DependencyError,
    TimeoutError,
    ConflictError,
    NotFoundError,
    global_exception_handler,
    init_sentry,
)
from .metrics import setup_metrics, track_migration_start, track_migration_end, MetricsCollector
from .cache import CacheManager
from .database import get_session, init_db, MigrationJob, MigrationSession
from .utils import generate_request_id, utc_now, safe_filename, format_bytes, format_duration, retry_with_backoff

__version__ = "0.1.0"
__all__ = [
    "setup_logging",
    "get_logger",
    "MigratorLogger",
    "MigratorBaseException",
    "ValidationError",
    "RuleValidationError",
    "ParsingError",
    "MigrationError",
    "FileTooLargeError",
    "UnsupportedFileTypeError",
    "RateLimitError",
    "AuthenticationError",
    "DependencyError",
    "TimeoutError",
    "ConflictError",
    "NotFoundError",
    "global_exception_handler",
    "init_sentry",
    "setup_metrics",
    "track_migration_start",
    "track_migration_end",
    "MetricsCollector",
    "CacheManager",
    "get_session",
    "init_db",
    "MigrationJob",
    "MigrationSession",
    "generate_request_id",
    "utc_now",
    "safe_filename",
    "format_bytes",
    "format_duration",
    "retry_with_backoff",
]