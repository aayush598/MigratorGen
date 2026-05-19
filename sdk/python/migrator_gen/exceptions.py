"""Exception hierarchy for the migrator_gen SDK.

All public exceptions inherit from :exc:`SDKError`, making it easy
to catch any SDK issue with a single ``except SDKError`` clause.

.. code-block:: python

    from migrator_gen import SDKError, MigrationError

    try:
        result = client.migrate_code(...)
    except MigrationError:
        # migration-specific failure
    except SDKError:
        # any other SDK error (config, network, etc.)
"""

from __future__ import annotations

from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════
# Base
# ═══════════════════════════════════════════════════════════════════


class SDKError(Exception):
    """Base exception for all SDK errors.

    All other exceptions in this module inherit from this class.
    """

    def __init__(self, message: str, *, details: Optional[dict] = None) -> None:
        self.details = details or {}
        super().__init__(message)


# ═══════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════


class ConfigurationError(SDKError):
    """Invalid or missing configuration."""


# ═══════════════════════════════════════════════════════════════════
# Network / API
# ═══════════════════════════════════════════════════════════════════


class APIError(SDKError):
    """Communication error with the MigratorGen API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 0,
        response: Optional[Any] = None,
        details: Optional[dict] = None,
    ) -> None:
        self.status_code = status_code
        self.response = response
        super().__init__(message, details=details)


class AuthenticationError(APIError):
    """API key authentication failed (HTTP 401)."""

    def __init__(self, message: str = "Invalid or missing API key", **kwargs: Any) -> None:
        super().__init__(message, status_code=401, **kwargs)


class RateLimitError(APIError):
    """Request rate limit exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: float = 60.0,
        **kwargs: Any,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, status_code=429, **kwargs)


class ValidationError(APIError):
    """Request payload failed server-side validation (HTTP 422)."""


class NotFoundError(APIError):
    """Requested resource was not found (HTTP 404)."""


class ConflictError(APIError):
    """Resource conflict (HTTP 409)."""


class TimeoutError(SDKError):
    """Operation exceeded the configured timeout."""


# ═══════════════════════════════════════════════════════════════════
# Migration
# ═══════════════════════════════════════════════════════════════════


class MigrationError(SDKError):
    """Base for all migration-related errors."""


class MigrationParseError(MigrationError):
    """Failed to parse a changelog or rules file."""


class MigrationValidationError(MigrationError):
    """Migration rules failed validation checks."""


class MigrationEngineError(MigrationError):
    """Internal engine failure during transformation."""


# ═══════════════════════════════════════════════════════════════════
# Local engine
# ═══════════════════════════════════════════════════════════════════


class EngineError(SDKError):
    """Local engine initialisation error (usually missing dependency)."""
