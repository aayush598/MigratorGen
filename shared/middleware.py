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
                "request_failed %s %s %.2fms",
                method, path, duration_ms,
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        status = response.status_code
        logger.info(
            "request_completed %s %s %d %.2fms",
            method, path, status, duration_ms,
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


class AuthenticationMiddleware(BaseHTTPMiddleware if STARLETTE_AVAILABLE else object):
    """Validates auth via service key (internal) or API key (CLI/MCP)."""

    EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/metrics"}

    def __init__(self, app: ASGIApp, service_key: Optional[str] = None, jwt_secret: Optional[str] = None):
        super().__init__(app)
        self.service_key = service_key
        self.jwt_secret = jwt_secret

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if path in self.EXEMPT_PATHS or path.startswith("/api/v1/auth"):
            request.state.tenant_id = None
            request.state.user_id = None
            request.state.role = None
            return await call_next(request)

        service_key = request.headers.get("X-Service-Key", "")

        if self.service_key and service_key == self.service_key:
            request.state.tenant_id = request.headers.get("X-Tenant-ID")
            request.state.user_id = request.headers.get("X-User-ID")
            request.state.role = request.headers.get("X-User-Role", "member")
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")

        if self.jwt_secret and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            from .auth import decode_token
            payload = decode_token(token, self.jwt_secret)
            if payload is None:
                return JSONResponse(
                    status_code=401,
                    content={
                        "type": "https://migrator-gen.example.com/errors/UNAUTHORIZED",
                        "title": "Invalid or expired token",
                        "status": 401,
                    },
                )
            request.state.tenant_id = payload.get("tenant_id")
            request.state.user_id = payload.get("sub")
            request.state.role = payload.get("role")
        else:
            api_key = request.headers.get("X-API-Key")
            if api_key:
                request.state.tenant_id = request.headers.get("X-Tenant-ID")
                request.state.user_id = None
                request.state.role = "member"
            else:
                request.state.tenant_id = None
                request.state.user_id = None
                request.state.role = None

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
                "request_timeout %s (limit %.1fs)",
                request.url.path, self.timeout_seconds,
            )
            return JSONResponse(
                status_code=504,
                content={
                    "type": "https://migrator-gen.example.com/errors/TIMEOUT",
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
    service_key: Optional[str] = None,
) -> None:
    """
    Attach all middlewares to a FastAPI application.

    Args:
        app: FastAPI application
        cors_origins: List of allowed CORS origins
        rate_limit: Rate limit string (e.g., "100/minute")
        timeout_seconds: Per-request timeout
        jwt_secret: JWT secret for tenant validation (legacy/CLI)
        service_key: Shared secret for internal service-to-service auth
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

        if jwt_secret or service_key:
            app.add_middleware(
                AuthenticationMiddleware,
                service_key=service_key,
                jwt_secret=jwt_secret,
            )

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