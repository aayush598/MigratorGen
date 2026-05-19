"""HTTP client for the MigratorGen REST API.

Requires ``httpx`` and ``tenacity`` (``pip install migrator-gen[remote]``).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import models as m
from .config import SDKConfig
from .exceptions import (
    APIError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    SDKError,
    TimeoutError,
    ValidationError,
)

log = logging.getLogger(__name__)


class RemoteClient:
    """HTTP client for the MigratorGen API.

    Handles connection pooling, retry/backoff, request/response
    serialisation, and converts HTTP errors to SDK exceptions.

    Usage::

        from migrator_gen import MigrationClient

        client = MigrationClient(mode="remote", base_url="https://api.example.com")
    """

    def __init__(self, config: SDKConfig) -> None:
        import httpx as _httpx

        self._config = config
        self._base_url = config.base_url.rstrip("/")

        headers: Dict[str, str] = {
            "User-Agent": f"migrator-gen-sdk/{_get_version()}",
            "Accept": "application/json",
        }
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        limits = _httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30,
        )

        self._client = _httpx.Client(
            base_url=self._base_url,
            headers=headers,
            timeout=_httpx.Timeout(config.timeout),
            limits=limits,
        )

        self._retry_decorator = self._build_retry()

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP client and release resources."""
        self._client.close()

    def __enter__(self) -> RemoteClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ── Retry logic ───────────────────────────────────────────────────────

    def _build_retry(self):
        import tenacity as _tenacity

        return _tenacity.retry(
            reraise=True,
            stop=_tenacity.stop_after_attempt(self._config.max_retries),
            wait=_tenacity.wait_exponential(min=1, max=30),
            retry=_tenacity.retry_if_exception(self._is_retryable),
        )

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        from httpx import TransportError, TimeoutException
        if isinstance(exc, TimeoutException):
            return True
        if isinstance(exc, TransportError):
            return True
        if isinstance(exc, APIError) and exc.status_code in (429, 502, 503, 504):
            return True
        return False

    # ── Request dispatcher ────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        from httpx import HTTPError, HTTPStatusError, TimeoutException as HttpxTimeout

        log.debug("RemoteClient %s %s", method, path)

        @self._retry_decorator
        def _do() -> Any:
            try:
                response = self._client.request(
                    method,
                    path,
                    params=params,
                    json=json_body,
                )
                response.raise_for_status()
                data = response.json() if response.content else {}
                return data
            except HttpxTimeout as exc:
                raise TimeoutError(
                    f"Request timed out after {self._config.timeout}s",
                ) from exc
            except HTTPStatusError as exc:
                self._raise_by_status(exc)
                raise  # unreachable
            except HTTPError as exc:
                raise APIError(
                    f"HTTP request failed: {exc}",
                    details={"method": method, "path": path},
                ) from exc

        return _do()

    def _raise_by_status(self, exc: Any) -> None:
        status = exc.response.status_code
        body = ""
        try:
            body = exc.response.json()
        except Exception:
            body = exc.response.text

        message = body.get("detail", str(exc)) if isinstance(body, dict) else str(body)

        if status == 401:
            raise AuthenticationError(message) from exc
        elif status == 404:
            raise NotFoundError(message, status_code=status, response=body) from exc
        elif status == 409:
            raise ConflictError(message, status_code=status, response=body) from exc
        elif status == 422:
            raise ValidationError(message, status_code=status, response=body) from exc
        elif status == 429:
            retry_after = float(exc.response.headers.get("Retry-After", 60))
            raise RateLimitError(message, retry_after=retry_after) from exc
        else:
            raise APIError(message, status_code=status, response=body) from exc

    # ── SDK operations ────────────────────────────────────────────────────

    def migrate_code(
        self,
        source_code: str,
        rules: List[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        payload = {
            "source_code": source_code,
            "rules": [r.to_dict() for r in rules],
            "source_version": source_version,
            "target_version": target_version,
            "dry_run": dry_run,
        }
        data = self._request("POST", "/api/v1/migrate", json_body=payload)
        return m.MigrateResponse(**data)

    def preview_migration(
        self,
        source_code: str,
        rules: List[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
    ) -> m.DiffPreview:
        return self.migrate_code(
            source_code, rules, source_version=source_version,
            target_version=target_version, dry_run=True,
        )

    def validate_rules(self, rules_file_path: str) -> m.ValidationReport:
        data = self._request("POST", "/api/v1/validate", json_body={"path": rules_file_path})
        return m.ValidationReport(**data)

    def parse_changelog(self, file_path: str) -> m.MigrationFile:
        data = self._request("POST", "/api/v1/parse-changelog", json_body={"path": file_path})
        return m.MigrationFile(**data)

    def suggest_migrations(
        self,
        file_path: str,
        destination_library: str,
    ) -> m.AnalyzeResult:
        data = self._request(
            "POST",
            "/api/v1/suggest",
            json_body={"path": file_path, "library": destination_library},
        )
        return m.AnalyzeResult(**data)

    def list_libraries(self) -> Dict[str, Dict[str, Any]]:
        data = self._request("GET", "/api/v1/libraries")
        return {k: dict(v) for k, v in data.get("libraries", {}).items()}

    def generate_rules_from_diff(
        self,
        old_code: str,
        new_code: str,
        module: str = "",
    ) -> List[m.Rule]:
        data = self._request(
            "POST", "/api/v1/generate-rules/diff",
            json_body={"old_code": old_code, "new_code": new_code, "module": module},
        )
        return [m.Rule(**r) for r in data.get("rules", [])]

    def generate_rules_from_changelog(
        self,
        changelog_text: str,
        library_name: str = "unknown",
    ) -> m.VersionChangelog:
        data = self._request(
            "POST",
            "/api/v1/generate-rules/changelog",
            json_body={"changelog_text": changelog_text, "library_name": library_name},
        )
        return m.VersionChangelog(**data)

    def resolve_path(
        self,
        source_version: str,
        target_version: str,
        library_name: str,
    ) -> m.ResolvedPath:
        data = self._request(
            "POST",
            "/api/v1/resolve-path",
            json_body={
                "source_version": source_version,
                "target_version": target_version,
                "library_name": library_name,
            },
        )
        steps_data = data.pop("steps", [])
        path = m.ResolvedPath(**data)
        path.steps = [m.MigrationStep(**s) for s in steps_data]
        return path

    def migrate_file(
        self,
        file_path: str,
        rules: List[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        from pathlib import Path
        source_code = Path(file_path).read_text(encoding="utf-8")
        return self.migrate_code(
            source_code, rules, source_version=source_version,
            target_version=target_version, dry_run=dry_run,
        )

    def generate_migrator_package(
        self,
        library_name: str,
        output_dir: str = ".",
    ) -> str:
        data = self._request(
            "POST",
            "/api/v1/generate-package",
            json_body={"library": library_name, "output_dir": output_dir},
        )
        return data.get("path", "")

    def health_check(self) -> m.HealthStatus:
        data = self._request("GET", "/api/v1/health")
        return m.HealthStatus(**data)


def _get_version() -> str:
    try:
        from . import __version__
        return __version__
    except ImportError:
        return "0.0.0-dev"
