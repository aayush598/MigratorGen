"""
Tests for libs/shared module.
Run with: python -m pytest tests/test_shared.py -v
"""

import pytest
import json
import time
from pathlib import Path
import sys
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent / "libs" / "shared" / "src"))


class TestLogging:
    def test_get_logger_returns_logger(self):
        from shared.logging import get_logger
        logger = get_logger("test")
        assert logger is not None

    def test_logger_handlers_configured(self):
        from shared.logging import get_logger
        logger = get_logger("test-handlers")
        assert logger is not None

    def test_logger_json_format(self):
        from shared.logging import get_logger
        logger = get_logger("test-json")
        assert logger is not None


class TestExceptions:
    def test_base_exception_instantiation(self):
        from shared.exceptions import MigratorBaseException
        exc = MigratorBaseException("test message")
        assert str(exc) == "test message"

    def test_validation_error(self):
        from shared.exceptions import ValidationError
        exc = ValidationError("invalid value")
        assert "invalid value" in str(exc)

    def test_rule_validation_error(self):
        from shared.exceptions import RuleValidationError
        exc = RuleValidationError("invalid rule")
        assert "invalid rule" in str(exc)

    def test_parsing_error(self):
        from shared.exceptions import ParsingError
        exc = ParsingError("parse failed")
        assert "parse failed" in str(exc)

    def test_migration_error(self):
        from shared.exceptions import MigrationError
        exc = MigrationError("migration failed")
        assert "migration failed" in str(exc)

    def test_file_too_large_error(self):
        from shared.exceptions import FileTooLargeError
        exc = FileTooLargeError("file too big")
        assert "file too big" in str(exc)

    def test_not_found_error(self):
        from shared.exceptions import NotFoundError
        exc = NotFoundError("rule not found")
        assert "rule not found" in str(exc)

    def test_unsupported_file_type_error(self):
        from shared.exceptions import UnsupportedFileTypeError
        exc = UnsupportedFileTypeError("unsupported")
        assert "unsupported" in str(exc)

    def test_exception_to_dict(self):
        from shared.exceptions import ValidationError
        exc = ValidationError("bad")
        d = exc.to_dict()
        assert d["code"] == "VALIDATION_ERROR"
        assert d["message"] == "bad"


class TestMetrics:
    def test_metrics_collector_init(self):
        from shared.metrics import MetricsCollector
        mc = MetricsCollector("test-svc")
        assert mc.service_name == "test-svc"

    def test_record_migration_start_increments_active(self):
        from shared.metrics import MetricsCollector
        mc = MetricsCollector()
        mc.record_migration_start("dockerfile")
        assert mc._active_migrations >= 1

    def test_record_migration_complete_decrements_active(self):
        from shared.metrics import MetricsCollector
        mc = MetricsCollector()
        mc.record_migration_start("dockerfile")
        mc.record_migration_complete("completed", "dockerfile", 1024)
        assert mc._active_migrations == 0

    def test_record_cache_hit(self):
        from shared.metrics import MetricsCollector
        mc = MetricsCollector()
        mc.record_cache_hit()
        assert mc._cache_hits == 1

    def test_record_cache_miss(self):
        from shared.metrics import MetricsCollector
        mc = MetricsCollector()
        mc.record_cache_miss()
        assert mc._cache_misses == 1

    def test_normalize_endpoint_with_uuid(self):
        from shared.metrics import normalize_endpoint
        result = normalize_endpoint("/migrations/123e4567-e89b-12d3-a456-426614174000")
        assert "{id}" in result

    def test_normalize_endpoint_with_numeric_id(self):
        from shared.metrics import normalize_endpoint
        result = normalize_endpoint("/migrations/12345")
        assert "{id}" in result


class TestUtils:
    def test_generate_request_id_is_uuid(self):
        from shared.utils import generate_request_id
        rid = generate_request_id()
        assert len(rid) == 36
        assert rid.count('-') == 4

    def test_generate_request_id_unique(self):
        from shared.utils import generate_request_id
        ids = [generate_request_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_utc_now_is_timezone_aware(self):
        from shared.utils import utc_now
        now = utc_now()
        assert now.tzinfo is not None

    def test_safe_filename_removes_special_chars(self):
        from shared.utils import safe_filename
        result = safe_filename('My File <>:test.txt')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result

    def test_safe_filename_max_length(self):
        from shared.utils import safe_filename
        result = safe_filename("a" * 300, max_length=100)
        assert len(result) <= 100

    def test_format_bytes_kilobyte(self):
        from shared.utils import format_bytes
        assert format_bytes(1024) == "1.0 KB"

    def test_format_bytes_megabyte(self):
        from shared.utils import format_bytes
        result = format_bytes(1024 * 1024 * 2)
        assert "MB" in result

    def test_format_bytes_gigabyte(self):
        from shared.utils import format_bytes
        result = format_bytes(1024 * 1024 * 1024)
        assert "GB" in result

    def test_format_duration_seconds(self):
        from shared.utils import format_duration
        result = format_duration(3000)
        assert "s" in result
        assert "3" in result

    def test_format_duration_milliseconds(self):
        from shared.utils import format_duration
        result = format_duration(125)
        assert "ms" in result

    def test_validate_file_extension_valid(self):
        from shared.utils import validate_file_extension
        validate_file_extension("test.py", [".py", ".txt"])

    def test_validate_file_extension_invalid(self):
        from shared.utils import validate_file_extension
        from shared.exceptions import UnsupportedFileTypeError
        with pytest.raises(UnsupportedFileTypeError):
            validate_file_extension("test.xyz", [".py", ".txt"])

    def test_validate_file_size_under_limit(self):
        from shared.utils import validate_file_size
        validate_file_size(b"x" * 100, max_size_mb=10)

    def test_validate_file_size_over_limit(self):
        from shared.utils import validate_file_size
        from shared.exceptions import FileTooLargeError
        with pytest.raises(FileTooLargeError):
            validate_file_size(b"x" * 20 * 1024 * 1024, max_size_mb=10)

    def test_compute_file_hash_sha256(self):
        from shared.utils import compute_file_hash
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("hello world")
            path = f.name
        try:
            h = compute_file_hash(path, "sha256")
            assert len(h) == 64
        finally:
            os.unlink(path)

    def test_compute_file_hash_md5(self):
        from shared.utils import compute_file_hash
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("hello")
            path = f.name
        try:
            h = compute_file_hash(path, "md5")
            assert len(h) == 32
        finally:
            os.unlink(path)

    def test_deep_get_simple(self):
        from shared.utils import deep_get
        result = deep_get({"a": 1}, "a")
        assert result == 1

    def test_deep_get_nested(self):
        from shared.utils import deep_get
        result = deep_get({"a": {"b": {"c": 42}}}, "a", "b", "c")
        assert result == 42

    def test_deep_get_missing_returns_default(self):
        from shared.utils import deep_get
        result = deep_get({"a": 1}, "b", default="missing")
        assert result == "missing"

    def test_deep_get_partial_path(self):
        from shared.utils import deep_get
        result = deep_get({"a": {"b": 2}}, "a", "b")
        assert result == 2

    def test_parse_version_simple(self):
        from shared.utils import parse_version
        result = parse_version("1.2.3")
        assert result == (1, 2, 3)

    def test_parse_version_with_v_prefix(self):
        from shared.utils import parse_version
        result = parse_version("v1.2.3")
        assert result == (1, 2, 3)

    def test_parse_version_with_prerelease(self):
        from shared.utils import parse_version
        result = parse_version("v1.0.0-alpha")
        assert result[0] >= 0

    def test_slugify(self):
        from shared.utils import slugify
        result = slugify("Hello World! Test")
        assert result == "hello-world-test"

    def test_truncate_short_text(self):
        from shared.utils import truncate
        result = truncate("short", 10)
        assert result == "short"

    def test_truncate_long_text(self):
        from shared.utils import truncate
        result = truncate("this is a long text", 10)
        assert len(result) <= 10
        assert result.endswith("...")


class TestRetryWithBackoff:
    def test_retry_success_first_attempt(self):
        from shared.utils import retry_with_backoff
        import asyncio

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        async def succeed():
            return "ok"

        result = asyncio.run(succeed())
        assert result == "ok"

    def test_retry_succeeds_after_failures(self):
        from shared.utils import retry_with_backoff
        import asyncio

        attempts = []

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        async def flaky():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("fail")
            return "ok"

        result = asyncio.run(flaky())
        assert result == "ok"
        assert len(attempts) == 3

    def test_retry_exhausts_attempts(self):
        from shared.utils import retry_with_backoff
        import asyncio

        @retry_with_backoff(max_attempts=2, base_delay=0.01)
        async def always_fail():
            raise ValueError("always fail")

        with pytest.raises(ValueError):
            asyncio.run(always_fail())


class TestDatabaseModels:
    def test_migration_job_table_name(self):
        from shared.database import MigrationJob
        assert MigrationJob.__tablename__ == "migration_jobs"

    def test_migration_session_table_name(self):
        from shared.database import MigrationSession
        assert MigrationSession.__tablename__ == "migration_sessions"

    def test_migration_job_fields(self):
        from shared.database import MigrationJob
        columns = [c.name for c in MigrationJob.__table__.columns]
        assert "id" in columns
        assert "status" in columns
        assert "source_version" in columns
        assert "target_version" in columns
        assert "created_at" in columns

    def test_migration_session_fields(self):
        from shared.database import MigrationSession
        columns = [c.name for c in MigrationSession.__table__.columns]
        assert "id" in columns
        assert "tenant_id" in columns


class TestCache:
    def test_cache_init(self):
        from shared.cache import CacheManager
        cache = CacheManager(prefix="test")
        assert cache.prefix == "test"

    def test_cache_key_generation(self):
        from shared.cache import CacheManager
        cache = CacheManager(prefix="test")
        key = cache._make_key("item1", "sub")
        assert "item1" in key
        assert key.startswith("test:")

    def test_cache_key_with_colon_separator(self):
        from shared.cache import CacheManager
        cache = CacheManager(prefix="myapp")
        key = cache._make_key("foo", "bar")
        parts = key.split(":")
        assert len(parts) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])