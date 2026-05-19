import pytest

from migrator_gen import (
    APIError,
    AuthenticationError,
    ConflictError,
    EngineError,
    MigrationEngineError,
    MigrationError,
    MigrationParseError,
    MigrationValidationError,
    NotFoundError,
    RateLimitError,
    SDKError,
    TimeoutError,
    ValidationError,
)


class TestSDKError:
    def test_base_with_details(self):
        err = SDKError("msg", details={"code": 123})
        assert err.details["code"] == 123


class TestAPIErrorStatusCodes:
    def test_authentication(self):
        assert AuthenticationError().status_code == 401

    def test_rate_limit(self):
        assert RateLimitError().status_code == 429
        assert RateLimitError(retry_after=30.5).retry_after == 30.5

    def test_not_found(self):
        assert NotFoundError().status_code == 404

    def test_conflict(self):
        assert ConflictError().status_code == 409

    def test_validation(self):
        assert ValidationError("bad").status_code == 422


class TestInheritance:
    def test_timeout_not_api_error(self):
        assert isinstance(TimeoutError("x"), SDKError)
        assert not isinstance(TimeoutError("x"), APIError)

    def test_migration_hierarchy(self):
        assert isinstance(MigrationParseError("x"), MigrationError)
        assert isinstance(MigrationValidationError("x"), MigrationError)
        assert isinstance(MigrationEngineError("x"), MigrationError)

    def test_engine_error_separate(self):
        assert isinstance(EngineError("x"), SDKError)
        assert not isinstance(EngineError("x"), MigrationError)

    def test_catch_sdk_error(self):
        with pytest.raises(SDKError):
            raise AuthenticationError()

    def test_catch_api_error(self):
        with pytest.raises(APIError):
            raise RateLimitError()

    def test_catch_migration_error(self):
        with pytest.raises(MigrationError):
            raise MigrationParseError("bad")
