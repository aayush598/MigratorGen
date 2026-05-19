from __future__ import annotations

from typing import Any


class SDKError(Exception):
    def __init__(self, message: str, *, details: dict | None = None) -> None:
        self.details = details or {}
        super().__init__(message)


class ConfigurationError(SDKError):
    pass


class APIError(SDKError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 0,
        response: Any | None = None,
        details: dict | None = None,
    ) -> None:
        self.status_code = status_code
        self.response = response
        super().__init__(message, details=details)


class AuthenticationError(APIError):
    def __init__(self, message: str = "Invalid or missing API key", **kwargs: Any) -> None:
        super().__init__(message, status_code=401, **kwargs)


class RateLimitError(APIError):
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
    def __init__(self, message: str = "Validation failed", **kwargs: Any) -> None:
        super().__init__(message, status_code=422, **kwargs)


class NotFoundError(APIError):
    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        super().__init__(message, status_code=404, **kwargs)


class ConflictError(APIError):
    def __init__(self, message: str = "Resource conflict", **kwargs: Any) -> None:
        super().__init__(message, status_code=409, **kwargs)


class TimeoutError(SDKError):
    pass


class MigrationError(SDKError):
    pass


class MigrationParseError(MigrationError):
    pass


class MigrationValidationError(MigrationError):
    pass


class MigrationEngineError(MigrationError):
    pass


class EngineError(SDKError):
    pass
