"""
Structured logging for MigratorGen platform.
Uses structlog for JSON-formatted, context-rich logging.
"""

import logging
import sys
import uuid
from enum import IntEnum
from typing import Any, Dict, Optional

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


class LogLevel(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


def setup_logging(
    app_env: str = "development",
    log_level: str = "INFO",
    service_name: str = "migratorgen",
    json_format: bool = True,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        app_env: Environment name (development, staging, production)
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Name of the service for log context
        json_format: If True, output JSON; otherwise human-readable
    """
    log_level_value = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level_value,
    )

    if STRUCTLOG_AVAILABLE:
        # Configure structlog processors
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
        ]

        if json_format or app_env == "production":
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Fallback to basic logging if structlog unavailable
        logging.warning("structlog not installed, using basic logging")


class MigratorLogger:
    """
    Structured logger for MigratorGen with context support.
    """

    def __init__(self, name: str, service_name: str = "migratorgen"):
        self.name = name
        self.service_name = service_name
        self._logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}

    def bind(self, **kwargs) -> "MigratorLogger":
        """Bind additional context fields."""
        new_logger = MigratorLogger(self.name, self.service_name)
        new_logger._context = {**self._context, **kwargs}
        return new_logger

    def _log(self, level: int, msg: str, **kwargs) -> None:
        """Internal log method."""
        extra = {**self._context, **kwargs}
        record = self._logger.makeRecord(
            self.name, level, "(unknown)", 0, msg, (), None, None
        )
        record.service_name = self.service_name
        for k, v in extra.items():
            setattr(record, k, v)
        self._logger.handle(record)

    def debug(self, msg: str, **kwargs) -> None:
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs) -> None:
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs) -> None:
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs) -> None:
        self._log(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs) -> None:
        self._log(logging.CRITICAL, msg, **kwargs)

    def exception(self, msg: str, **kwargs) -> None:
        kwargs["exc_info"] = True
        self._log(logging.ERROR, msg, **kwargs)


def get_logger(name: str, service_name: str = "migratorgen") -> MigratorLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)
        service_name: Service identifier for context

    Returns:
        MigratorLogger instance
    """
    return MigratorLogger(name, service_name)


class RequestLogger:
    """Request-scoped logger with request ID tracking."""

    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id or str(uuid.uuid4())
        self._logger = get_logger("request")

    def log_request(
        self,
        method: str,
        path: str,
        status: int,
        duration_ms: float,
        **extra,
    ) -> None:
        """Log an HTTP request."""
        self._logger.info(
            "request_completed",
            request_id=self.request_id,
            method=method,
            path=path,
            status=status,
            duration_ms=duration_ms,
            **extra,
        )

    def log_migration(
        self,
        rule_id: str,
        change_type: str,
        confidence: float,
        **extra,
    ) -> None:
        """Log a migration rule application."""
        self._logger.info(
            "migration_applied",
            request_id=self.request_id,
            rule_id=rule_id,
            change_type=change_type,
            confidence=confidence,
            **extra,
        )