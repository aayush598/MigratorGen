"""
Python SDK for MigratorGen API.
Provides a type-safe client for programmatic migration access.
"""

from .client import MigratorClient
from .models import (
    Rule,
    MigrateRequest,
    MigrateResponse,
    MigrationJob,
    MigrationStatus,
    ValidationReport,
    ValidationMessage,
    Version,
    ChangeType,
)
from .exceptions import (
    SDKError,
    APIError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    MigrationError,
    TimeoutError,
)

__version__ = "0.1.0"
__all__ = [
    "MigratorClient",
    "Rule",
    "MigrateRequest",
    "MigrateResponse",
    "MigrationJob",
    "MigrationStatus",
    "ValidationReport",
    "ValidationMessage",
    "Version",
    "ChangeType",
    "SDKError",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "MigrationError",
    "TimeoutError",
]