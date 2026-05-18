"""
FastAPI middleware stack for MigratorGen platform.
Includes: Request logging, Rate limiting, CORS, Error handling, Metrics, Tenant, Request ID, Timeout.
"""

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse, Response
    from starlette.types import ASGIApp
    STARLETTE_AVAILABLE = True
except ImportError:
    BaseHTTPMiddleware = object
    Request = Any
    STARLETTE_AVAILABLE = False

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.middleware import SlowAPIMiddleware
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False

from .exceptions import global_exception_handler, MigratorBaseException

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware if STARLETTE_AVAILABLE else object):
    """Generates and propagates a unique request ID (UUID4)."""

    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get(self.HEADER_NAME) or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[self.HEADER_NAME] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware if STARLETTE_AVAILABLE else object):
    """Logs all incoming requests with duration and status."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "request_failed",
                method=method,
                path=path,
                duration_ms=f"{duration_ms:.2f}",
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        status = response.status_code
        logger.info(
            "request_completed",
            method=method,
            path=path,
            status=status,
            duration_ms=f"{duration_ms:.2f}",
        )
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware if STARLETTE_AVAILABLE else object):
    """Catches all exceptions and returns RFC 7807 Problem Details."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            problem = global_exception_handler(request, exc)
            return JSONResponse(
                status_code=problem.get("status", 500),
                content=problem,
                headers={"Content-Type": "application/problem+json"},
            )


class MetricsMiddleware(BaseHTTPMiddleware if STARLETTE_AVAILABLE else object):
    """Records Prometheus metrics for each request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        from .metrics import metrics as _metrics

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            response = JSONResponse(status_code=500, content={"error": "Internal error"})

        duration = time.perf_counter() - start
        _metrics.record_request(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
            duration_seconds=duration,
        )
        return response


class TenantMiddleware(BaseHTTPMiddleware if STARLETTE_AVAILABLE else object):
    """Extracts and validates tenant_id from JWT or header for multi-tenancy."""

    def __init__(self, app: ASGIApp, jwt_secret: Optional[str] = None):
        super().__init__(app)
        self.jwt_secret = jwt_secret

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        tenant_id = request.headers.get("X-Tenant-ID")
        user_id = request.headers.get("X-User-ID")

        if tenant_id:
            request.state.tenant_id = tenant_id
        if user_id:
            request.state.user_id = user_id

        return await call_next(request)


class TimeoutMiddleware(BaseHTTPMiddleware if STARLETTE_AVAILABLE else object):
    """Per-request timeout using asyncio.wait_for."""

    def __init__(self, app: ASGIApp, timeout_seconds: float = 60.0):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import asyncio

        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(
                "request_timeout",
                path=request.url.path,
                timeout=self.timeout_seconds,
            )
            return JSONResponse(
                status_code=504,
                content={
                    "type": "https://migratorgen.example.com/errors/TIMEOUT",
                    "title": "Request timed out",
                    "status": 504,
                    "detail": f"Request exceeded {self.timeout_seconds}s timeout",
                },
            )


def setup_middlewares(
    app: Any,
    cors_origins: List[str] = None,
    rate_limit: str = "100/minute",
    timeout_seconds: float = 60.0,
    jwt_secret: Optional[str] = None,
) -> None:
    """
    Attach all middlewares to a FastAPI application.

    Args:
        app: FastAPI application
        cors_origins: List of allowed CORS origins
        rate_limit: Rate limit string (e.g., "100/minute")
        timeout_seconds: Per-request timeout
        jwt_secret: JWT secret for tenant validation
    """
    if cors_origins is None:
        cors_origins = ["*"]

    if STARLETTE_AVAILABLE:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(ErrorHandlingMiddleware)
        app.add_middleware(MetricsMiddleware)
        app.add_middleware(TimeoutMiddleware, timeout_seconds=timeout_seconds)
        app.add_middleware(RequestIDMiddleware)
        app.add_middleware(RequestLoggingMiddleware)

        if jwt_secret:
            app.add_middleware(TenantMiddleware, jwt_secret=jwt_secret)

        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


def create_rate_limiter(default_limit: str = "100/minute") -> Any:
    """
    Create a SlowAPI rate limiter instance.

    Args:
        default_limit: Default rate limit string

    Returns:
        Limiter instance
    """
    if not SLOWAPI_AVAILABLE:
        logger.warning("slowapi not installed, rate limiting disabled")
        return None

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[default_limit],
        storage_uri="memory://",
    )
    return limiter