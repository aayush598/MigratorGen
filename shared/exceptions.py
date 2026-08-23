"""
Comprehensive exception hierarchy for MigratorGen platform.
Includes RFC 7807 Problem Details, Sentry integration, and FastAPI exception handlers.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MigratorBaseException(Exception):
    """
    Base exception for all MigratorGen errors.

    Attributes:
        code: Machine-readable error code
        status_code: HTTP status code
        details: Additional error context
        cause: Original exception that caused this one
    """

    code: str = "MIGRATOR_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
        }

    def to_problem_details(
        self, type_url: str = "https://migrator-gen.example.com/errors"
    ) -> dict[str, Any]:
        """
        Convert to RFC 7807 Problem Details format.

        Args:
            type_url: URL with error type documentation

        Returns:
            RFC 7807 compliant dictionary
        """
        return {
            "type": f"{type_url}/{self.code}",
            "title": self.message,
            "status": self.status_code,
            "detail": self.message,
            "instance": f"/errors/{self.code}",
            "extensions": self.details,
        }


class ValidationError(MigratorBaseException):
    """Base validation error."""

    code = "VALIDATION_ERROR"
    status_code = 400


class RuleValidationError(ValidationError):
    """Error validating migration rules."""

    code = "RULE_VALIDATION_ERROR"


class ParsingError(MigratorBaseException):
    """Error parsing input (changelog, code, etc.)."""

    code = "PARSING_ERROR"
    status_code = 422


class MigrationError(MigratorBaseException):
    """General migration processing error."""

    code = "MIGRATION_ERROR"


class FileTooLargeError(MigratorBaseException):
    """Uploaded file exceeds size limit."""

    code = "FILE_TOO_LARGE"
    status_code = 413


class UnsupportedFileTypeError(MigratorBaseException):
    """File type not supported."""

    code = "UNSUPPORTED_FILE"
    status_code = 415


class RateLimitError(MigratorBaseException):
    """Rate limit exceeded."""

    code = "RATE_LIMIT"
    status_code = 429


class AuthenticationError(MigratorBaseException):
    """Authentication failed."""

    code = "AUTH_ERROR"
    status_code = 401


class DependencyError(MigratorBaseException):
    """Dependency resolution error."""

    code = "DEP_ERROR"


class TimeoutError(MigratorBaseException):
    """Operation timed out."""

    code = "TIMEOUT"
    status_code = 504


class ConflictError(MigratorBaseException):
    """Resource conflict (e.g., duplicate rule ID)."""

    code = "CONFLICT"
    status_code = 409


class NotFoundError(MigratorBaseException):
    """Resource not found."""

    code = "NOT_FOUND"
    status_code = 404


class SentryManager:
    """Manages Sentry integration for error tracking."""

    _instance: Optional["SentryManager"] = None
    _initialized: bool = False

    @classmethod
    def get_instance(cls) -> "SentryManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def init(
        self,
        dsn: str,
        environment: str,
        service_name: str,
        release: Optional[str] = None,
        sample_rate: float = 1.0,
    ) -> None:
        """
        Initialize Sentry SDK.

        Args:
            dsn: Sentry DSN URL
            environment: Environment name
            service_name: Service identifier
            release: Version/release string
            sample_rate: Trace sample rate (0.0-1.0)
        """
        if self._initialized:
            return

        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastAPIIntegration
            from sentry_sdk.integrations.starlette import StarletteIntegration

            sentry_sdk.init(
                dsn=dsn,
                environment=environment,
                release=release,
                traces_sample_rate=sample_rate,
                integrations=[
                    FastAPIIntegration(),
                    StarletteIntegration(),
                ],
                service_name=service_name,
                send_default_pii=False,
                ignore_errors=[
                    "KeyboardInterrupt",
                    "SystemExit",
                    "asyncio.CancelledError",
                ],
            )
            self._initialized = True
            logger.info("Sentry initialized", environment=environment)
        except ImportError:
            logger.warning("sentry-sdk not installed, skipping Sentry init")
        except Exception as e:
            logger.error("Failed to initialize Sentry", error=str(e))

    def capture_exception(
        self,
        exc: Exception,
        request_id: Optional[str] = None,
        **extra,
    ) -> Optional[str]:
        """
        Capture an exception with Sentry.

        Returns:
            Sentry event ID if captured
        """
        if not self._initialized:
            return None

        try:
            import sentry_sdk

            with sentry_sdk.configure_scope() as scope:
                if request_id:
                    scope.set_tag("request_id", request_id)
                for key, value in extra.items():
                    scope.set_extra(key, value)
            return sentry_sdk.capture_exception(exc)
        except Exception as e:
            logger.error("Failed to capture exception in Sentry", error=str(e))
            return None


def init_sentry(
    app: Any,
    dsn: str,
    environment: str,
    service_name: str = "migrator-gen",
    release: Optional[str] = None,
) -> None:
    """
    Initialize Sentry for a FastAPI application.

    Args:
        app: FastAPI application instance
        dsn: Sentry DSN URL
        environment: Environment name
        service_name: Service identifier
        release: Version string
    """
    SentryManager.get_instance().init(dsn, environment, service_name, release)


def global_exception_handler(request: Any, exc: Exception) -> dict[str, Any]:
    """
    FastAPI exception handler that returns RFC 7807 Problem Details.

    Args:
        request: The FastAPI request object
        exc: The exception to handle

    Returns:
        RFC 7807 compliant error response
    """
    if isinstance(exc, MigratorBaseException):
        return exc.to_problem_details()

    # Unknown exception
    logger.exception(
        "Unhandled exception",
        exc_type=type(exc).__name__,
        exc_message=str(exc),
        path=getattr(request, "url", None),
    )

    return {
        "type": "https://migrator-gen.example.com/errors/INTERNAL_ERROR",
        "title": "An unexpected error occurred",
        "status": 500,
        "detail": str(exc),
        "instance": getattr(request, "url", None) or "/",
        "extensions": {
            "error_type": type(exc).__name__,
        },
    }
