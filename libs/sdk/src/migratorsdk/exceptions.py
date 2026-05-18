"""
Exception hierarchy for MigratorGen SDK.
"""


class SDKError(Exception):
    """Base exception for SDK errors."""
    pass


class APIError(SDKError):
    """Base exception for API errors."""
    def __init__(self, message: str, status_code: int = 0, response: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class AuthenticationError(APIError):
    """Authentication failed."""
    pass


class RateLimitError(APIError):
    """Rate limit exceeded."""
    pass


class ValidationError(APIError):
    """Validation error in request."""
    pass


class MigrationError(APIError):
    """Migration processing error."""
    pass


class TimeoutError(SDKError):
    """Request timed out."""
    pass


class NotFoundError(APIError):
    """Resource not found."""
    pass


class ConflictError(APIError):
    """Resource conflict."""
    pass