"""
Python SDK client for MigratorGen API.
Provides programmatic access with automatic retry, rate limiting, and async support.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
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
from .models import (
    Rule,
    MigrateRequest,
    MigrateResponse,
    MigrationJob,
    MigrationStatus,
    ValidationReport,
    Version,
    HealthStatus,
    DiffPreview,
)

logger = logging.getLogger(__name__)


class MigratorClient:
    """
    Python SDK client for MigratorGen API.

    Args:
        base_url: Base URL of the MigratorGen API
        api_key: API key for authentication
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts for transient failures

    Example:
        client = MigratorClient(
            base_url="https://api.migratorgen.example.com",
            api_key="your-api-key",
        )
        result = client.migrate_code("foo()", rules, "1.0.0", "2.0.0")
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        if not HTTPX_AVAILABLE:
            raise SDKError("httpx is required. Install: pip install httpx")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with error handling.

        Args:
            method: HTTP method
            path: API path
            **kwargs: Additional arguments for httpx

        Returns:
            Response JSON

        Raises:
            APIError: On HTTP errors
            AuthenticationError: On auth failures
            RateLimitError: On rate limit exceeded
            TimeoutError: On timeout
        """
        try:
            response = await self.client.request(method, path, **kwargs)
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out after {self.timeout}s") from e
        except httpx.ConnectError as e:
            raise APIError(f"Failed to connect to {self.base_url}") from e

        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")
        elif response.status_code == 422:
            body = response.json()
            raise ValidationError(f"Validation failed: {body}")
        elif response.status_code >= 400:
            try:
                body = response.json()
                detail = body.get("detail", str(body))
            except Exception:
                detail = response.text
            raise APIError(f"HTTP {response.status_code}: {detail}")

        return response.json()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> HealthStatus:
        """Check API health status."""
        data = await self._request("GET", "/health")
        return HealthStatus(**data)

    async def migrate_code(
        self,
        code: str,
        rules: List[Rule],
        from_version: str,
        to_version: str = "latest",
        dry_run: bool = False,
    ) -> MigrateResponse:
        """
        Migrate source code.

        Args:
            code: Source code to migrate
            rules: List of migration rules
            from_version: Source version
            to_version: Target version
            dry_run: If True, validate without modifying

        Returns:
            MigrateResponse with transformed code and metadata
        """
        payload = {
            "source_code": code,
            "rules": [r.model_dump() for r in rules],
            "source_version": from_version,
            "target_version": to_version,
            "dry_run": dry_run,
        }
        data = await self._request("POST", "/migrate/code", json=payload)
        return MigrateResponse(**data)

    async def migrate_file(
        self,
        file_path: str,
        rules: List[Rule],
        from_version: str,
        to_version: str = "latest",
        dry_run: bool = False,
    ) -> MigrateResponse:
        """
        Migrate a file by path.

        Args:
            file_path: Path to file
            rules: List of migration rules
            from_version: Source version
            to_version: Target version
            dry_run: If True, validate without modifying

        Returns:
            MigrateResponse
        """
        with open(file_path, "r") as f:
            code = f.read()
        return await self.migrate_code(code, rules, from_version, to_version, dry_run)

    async def preview(
        self,
        code: str,
        rules: List[Rule],
        from_version: str,
        to_version: str = "latest",
    ) -> DiffPreview:
        """
        Preview migration as unified diff without modifying.

        Args:
            code: Source code
            rules: List of migration rules
            from_version: Source version
            to_version: Target version

        Returns:
            DiffPreview with diff and metadata
        """
        payload = {
            "source_code": code,
            "rules": [r.model_dump() for r in rules],
            "source_version": from_version,
            "target_version": to_version,
        }
        data = await self._request("POST", "/preview", json=payload)
        return DiffPreview(**data)

    async def validate_rules(self, rules: List[Rule]) -> ValidationReport:
        """
        Validate migration rules without applying them.

        Args:
            rules: List of rules to validate

        Returns:
            ValidationReport
        """
        payload = {"rules": [r.model_dump() for r in rules]}
        data = await self._request("POST", "/rules/validate", json=payload)
        return ValidationReport(**data)

    async def generate_rules_from_diff(
        self,
        old_code: str,
        new_code: str,
    ) -> List[Rule]:
        """
        Auto-generate migration rules from a code diff.

        Args:
            old_code: Original code
            new_code: Modified code

        Returns:
            List of generated rules
        """
        payload = {"old_code": old_code, "new_code": new_code}
        data = await self._request("POST", "/rules/generate-from-diff", json=payload)
        return [Rule(**r) for r in data.get("rules", [])]

    async def generate_rules_from_changelog(
        self,
        changelog_text: str,
        version: str,
    ) -> List[Rule]:
        """
        Generate rules from human-readable changelog text.

        Args:
            changelog_text: Changelog text (markdown)
            version: Version string

        Returns:
            List of generated rules
        """
        payload = {"changelog_text": changelog_text, "version": version}
        data = await self._request("POST", "/rules/generate-from-changelog", json=payload)
        return [Rule(**r) for r in data.get("rules", [])]

    async def list_versions(self) -> List[Version]:
        """List available library versions."""
        data = await self._request("GET", "/versions")
        return [Version(**v) for v in data.get("versions", [])]

    async def create_migration_job(
        self,
        source_code: str,
        rules: List[Rule],
        from_version: str,
        to_version: str = "latest",
    ) -> str:
        """
        Create an async migration job (returns job_id).

        Args:
            source_code: Source code
            rules: Migration rules
            from_version: Source version
            to_version: Target version

        Returns:
            Job ID for status polling
        """
        payload = {
            "source_code": source_code,
            "rules": [r.model_dump() for r in rules],
            "source_version": from_version,
            "target_version": to_version,
        }
        data = await self._request("POST", "/migrate/async", json=payload)
        return data.get("job_id", "")

    async def get_migration_status(self, job_id: str) -> MigrationJob:
        """
        Get status of a migration job.

        Args:
            job_id: Job identifier

        Returns:
            MigrationJob with current status
        """
        data = await self._request("GET", f"/jobs/{job_id}")
        return MigrationJob(**data)

    async def wait_for_completion(
        self,
        job_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> MigrationJob:
        """
        Wait for a migration job to complete.

        Args:
            job_id: Job identifier
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            Final MigrationJob
        """
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            job = await self.get_migration_status(job_id)
            if job.status in (MigrationStatus.COMPLETED, MigrationStatus.FAILED, MigrationStatus.CANCELLED):
                return job
            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")

    def __enter__(self) -> "MigratorClient":
        return self

    def __exit__(self, *args: Any) -> None:
        asyncio.run(self.close())


# Synchronous wrapper for convenience
class SyncMigratorClient:
    """Synchronous wrapper around MigratorClient."""

    def __init__(self, *args: Any, **kwargs: Any):
        self._async = MigratorClient(*args, **kwargs)

    def __enter__(self) -> "SyncMigratorClient":
        return self

    def __exit__(self, *args: Any) -> None:
        asyncio.run(self._async.close())

    def _run(self, coro: Any) -> Any:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)

    def health_check(self) -> HealthStatus:
        return self._run(self._async.health_check())

    def migrate_code(self, *args: Any, **kwargs: Any) -> MigrateResponse:
        return self._run(self._async.migrate_code(*args, **kwargs))

    def preview(self, *args: Any, **kwargs: Any) -> DiffPreview:
        return self._run(self._async.preview(*args, **kwargs))

    def validate_rules(self, *args: Any, **kwargs: Any) -> ValidationReport:
        return self._run(self._async.validate_rules(*args, **kwargs))

    def generate_rules_from_diff(self, *args: Any, **kwargs: Any) -> List[Rule]:
        return self._run(self._async.generate_rules_from_diff(*args, **kwargs))

    def generate_rules_from_changelog(self, *args: Any, **kwargs: Any) -> List[Rule]:
        return self._run(self._async.generate_rules_from_changelog(*args, **kwargs))

    def list_versions(self) -> List[Version]:
        return self._run(self._async.list_versions())

    def create_migration_job(self, *args: Any, **kwargs: Any) -> str:
        return self._run(self._async.create_migration_job(*args, **kwargs))

    def get_migration_status(self, *args: Any, **kwargs: Any) -> MigrationJob:
        return self._run(self._async.get_migration_status(*args, **kwargs))

    def wait_for_completion(self, *args: Any, **kwargs: Any) -> MigrationJob:
        return self._run(self._async.wait_for_completion(*args, **kwargs))