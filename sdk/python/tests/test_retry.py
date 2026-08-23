import pytest

from migrator_gen.exceptions import APIError, TimeoutError
from migrator_gen.utils.retry import RetryStrategy, _is_retryable


class TestIsRetryable:
    def test_timeout_is_retryable(self):
        assert _is_retryable(TimeoutError("timeout")) is True

    def test_429_is_retryable(self):
        assert _is_retryable(APIError("x", status_code=429)) is True

    def test_503_is_retryable(self):
        assert _is_retryable(APIError("x", status_code=503)) is True

    def test_400_not_retryable(self):
        assert _is_retryable(APIError("x", status_code=400)) is False

    def test_value_error_not_retryable(self):
        assert _is_retryable(ValueError("x")) is False


class TestRetryStrategy:
    def test_successful_call(self):
        assert RetryStrategy(max_retries=3).execute(lambda: "ok") == "ok"

    def test_retries_then_succeeds(self):
        strategy = RetryStrategy(max_retries=3, base_delay=0.01)
        call_count = [0]

        def fn():
            call_count[0] += 1
            if call_count[0] < 3:
                raise TimeoutError("transient")
            return "recovered"

        assert strategy.execute(fn) == "recovered"
        assert call_count[0] == 3

    def test_gives_up_after_max_retries(self):
        strategy = RetryStrategy(max_retries=2, base_delay=0.01)
        with pytest.raises(TimeoutError):
            strategy.execute(lambda: (_ for _ in ()).throw(TimeoutError("fail")))

    def test_decorate(self):
        strategy = RetryStrategy(max_retries=2, base_delay=0.01)
        call_count = [0]

        @strategy.decorate
        def fn():
            call_count[0] += 1
            if call_count[0] < 2:
                raise TimeoutError("transient")
            return "ok"

        assert fn() == "ok"
        assert call_count[0] == 2
