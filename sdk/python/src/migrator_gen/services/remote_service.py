from __future__ import annotations

import logging
from typing import Any

from .._version import USER_AGENT
from ..config import SDKConfig
from ..core import models as m
from ..exceptions import (
    APIError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from ..utils.retry import RetryStrategy
from ..utils.serialization import read_file

log = logging.getLogger(__name__)


class AsyncRemoteService:
    def __init__(self, config: SDKConfig) -> None:
        import httpx

        self._config = config
        self._base_url = config.base_url.rstrip("/")
        headers: dict[str, str] = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        limits = httpx.Limits(
            max_keepalive_connections=20, max_connections=100, keepalive_expiry=30
        )
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=httpx.Timeout(config.timeout),
            limits=limits,
        )
        self._retry = RetryStrategy(max_retries=config.max_retries)

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        from httpx import HTTPError, HTTPStatusError
        from httpx import TimeoutException as HttpxTimeout

        log.debug("AsyncRemoteService %s %s", method, path)

        async def _do() -> Any:
            try:
                response = await self._client.request(method, path, params=params, json=json_body)
                response.raise_for_status()
                return response.json() if response.content else {}
            except HttpxTimeout as exc:
                raise TimeoutError(f"Request timed out after {self._config.timeout}s") from exc
            except HTTPStatusError as exc:
                self._raise_by_status(exc)
                raise
            except HTTPError as exc:
                raise APIError(
                    f"HTTP request failed: {exc}", details={"method": method, "path": path}
                ) from exc

        return await self._retry.execute_async(_do)

    def _raise_by_status(self, exc: Any) -> None:
        status = exc.response.status_code
        body = ""
        try:
            body = exc.response.json()
        except Exception:
            body = exc.response.text
        message = body.get("detail", str(exc)) if isinstance(body, dict) else str(body)
        if status == 401:
            raise AuthenticationError(message)
        elif status == 404:
            raise NotFoundError(message, status_code=status, response=body)
        elif status == 409:
            raise ConflictError(message, status_code=status, response=body)
        elif status == 422:
            raise ValidationError(message, status_code=status, response=body)
        elif status == 429:
            retry_after = float(exc.response.headers.get("Retry-After", 60))
            raise RateLimitError(message, retry_after=retry_after)
        else:
            raise APIError(message, status_code=status, response=body)

    async def migrate_code(
        self,
        source_code: str,
        rules: list[m.Rule],
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
        data = await self._request("POST", "/api/v1/migrate", json_body=payload)
        return m.MigrateResponse(**data)

    async def preview_migration(
        self,
        source_code: str,
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
    ) -> m.DiffPreview:
        return await self.migrate_code(
            source_code,
            rules,
            source_version=source_version,
            target_version=target_version,
            dry_run=True,
        )

    async def validate_rules(self, rules_file_path: str) -> m.ValidationReport:
        data = await self._request("POST", "/api/v1/validate", json_body={"path": rules_file_path})
        return m.ValidationReport(**data)

    async def parse_changelog(self, file_path: str) -> m.MigrationFile:
        data = await self._request("POST", "/api/v1/parse-changelog", json_body={"path": file_path})
        return m.MigrationFile(**data)

    async def suggest_migrations(self, file_path: str, destination_library: str) -> Any:
        return await self._request(
            "POST", "/api/v1/suggest", json_body={"path": file_path, "library": destination_library}
        )

    async def list_libraries(self) -> dict[str, dict[str, Any]]:
        data = await self._request("GET", "/api/v1/libraries")
        return {k: dict(v) for k, v in data.get("libraries", {}).items()}

    async def generate_rules_from_diff(
        self, old_code: str, new_code: str, module: str = ""
    ) -> list[m.Rule]:
        data = await self._request(
            "POST",
            "/api/v1/generate-rules/diff",
            json_body={"old_code": old_code, "new_code": new_code, "module": module},
        )
        return [m.Rule(**r) for r in data.get("rules", [])]

    async def generate_rules_from_changelog(
        self, changelog_text: str, library_name: str = "unknown"
    ) -> m.VersionChangelog:
        data = await self._request(
            "POST",
            "/api/v1/generate-rules/changelog",
            json_body={"changelog_text": changelog_text, "library_name": library_name},
        )
        return m.VersionChangelog(**data)

    async def resolve_path(
        self, source_version: str, target_version: str, library_name: str
    ) -> m.ResolvedPath:
        data = await self._request(
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

    async def migrate_file(
        self,
        file_path: str,
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        source_code = read_file(file_path)
        return await self.migrate_code(
            source_code,
            rules,
            source_version=source_version,
            target_version=target_version,
            dry_run=dry_run,
        )

    async def generate_migrator_package(self, library_name: str, output_dir: str = ".") -> str:
        data = await self._request(
            "POST",
            "/api/v1/generate-package",
            json_body={"library": library_name, "output_dir": output_dir},
        )
        return data.get("path", "")

    async def health_check(self) -> m.HealthStatus:
        data = await self._request("GET", "/api/v1/health")
        return m.HealthStatus(**data)


class SyncRemoteService:
    def __init__(self, config: SDKConfig) -> None:
        import httpx

        self._config = config
        self._base_url = config.base_url.rstrip("/")
        headers: dict[str, str] = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        limits = httpx.Limits(
            max_keepalive_connections=20, max_connections=100, keepalive_expiry=30
        )
        self._client = httpx.Client(
            base_url=self._base_url,
            headers=headers,
            timeout=httpx.Timeout(config.timeout),
            limits=limits,
        )
        self._retry = RetryStrategy(max_retries=config.max_retries)

    def close(self) -> None:
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        from httpx import HTTPError, HTTPStatusError
        from httpx import TimeoutException as HttpxTimeout

        log.debug("SyncRemoteService %s %s", method, path)

        def _do() -> Any:
            try:
                response = self._client.request(method, path, params=params, json=json_body)
                response.raise_for_status()
                return response.json() if response.content else {}
            except HttpxTimeout as exc:
                raise TimeoutError(f"Request timed out after {self._config.timeout}s") from exc
            except HTTPStatusError as exc:
                self._raise_by_status(exc)
                raise
            except HTTPError as exc:
                raise APIError(
                    f"HTTP request failed: {exc}", details={"method": method, "path": path}
                ) from exc

        return self._retry.execute(_do)

    def _raise_by_status(self, exc: Any) -> None:
        status = exc.response.status_code
        body = ""
        try:
            body = exc.response.json()
        except Exception:
            body = exc.response.text
        message = body.get("detail", str(exc)) if isinstance(body, dict) else str(body)
        if status == 401:
            raise AuthenticationError(message)
        elif status == 404:
            raise NotFoundError(message, status_code=status, response=body)
        elif status == 409:
            raise ConflictError(message, status_code=status, response=body)
        elif status == 422:
            raise ValidationError(message, status_code=status, response=body)
        elif status == 429:
            retry_after = float(exc.response.headers.get("Retry-After", 60))
            raise RateLimitError(message, retry_after=retry_after)
        else:
            raise APIError(message, status_code=status, response=body)

    def migrate_code(
        self,
        source_code: str,
        rules: list[m.Rule],
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
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
    ) -> m.DiffPreview:
        return self.migrate_code(
            source_code,
            rules,
            source_version=source_version,
            target_version=target_version,
            dry_run=True,
        )

    def validate_rules(self, rules_file_path: str) -> m.ValidationReport:
        data = self._request("POST", "/api/v1/validate", json_body={"path": rules_file_path})
        return m.ValidationReport(**data)

    def parse_changelog(self, file_path: str) -> m.MigrationFile:
        data = self._request("POST", "/api/v1/parse-changelog", json_body={"path": file_path})
        return m.MigrationFile(**data)

    def suggest_migrations(self, file_path: str, destination_library: str) -> Any:
        return self._request(
            "POST", "/api/v1/suggest", json_body={"path": file_path, "library": destination_library}
        )

    def list_libraries(self) -> dict[str, dict[str, Any]]:
        data = self._request("GET", "/api/v1/libraries")
        return {k: dict(v) for k, v in data.get("libraries", {}).items()}

    def generate_rules_from_diff(
        self, old_code: str, new_code: str, module: str = ""
    ) -> list[m.Rule]:
        data = self._request(
            "POST",
            "/api/v1/generate-rules/diff",
            json_body={"old_code": old_code, "new_code": new_code, "module": module},
        )
        return [m.Rule(**r) for r in data.get("rules", [])]

    def generate_rules_from_changelog(
        self, changelog_text: str, library_name: str = "unknown"
    ) -> m.VersionChangelog:
        data = self._request(
            "POST",
            "/api/v1/generate-rules/changelog",
            json_body={"changelog_text": changelog_text, "library_name": library_name},
        )
        return m.VersionChangelog(**data)

    def resolve_path(
        self, source_version: str, target_version: str, library_name: str
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
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        source_code = read_file(file_path)
        return self.migrate_code(
            source_code,
            rules,
            source_version=source_version,
            target_version=target_version,
            dry_run=dry_run,
        )

    def generate_migrator_package(self, library_name: str, output_dir: str = ".") -> str:
        data = self._request(
            "POST",
            "/api/v1/generate-package",
            json_body={"library": library_name, "output_dir": output_dir},
        )
        return data.get("path", "")

    def health_check(self) -> m.HealthStatus:
        data = self._request("GET", "/api/v1/health")
        return m.HealthStatus(**data)
