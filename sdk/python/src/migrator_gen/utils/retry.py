from __future__ import annotations

import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from ..exceptions import APIError, TimeoutError

F = TypeVar("F", bound=Callable[..., Any])

RETRYABLE_STATUSES: set[int] = {429, 502, 503, 504}


def _is_retryable(exception: Exception) -> bool:
    if isinstance(exception, TimeoutError):
        return True
    if isinstance(exception, APIError) and exception.status_code in RETRYABLE_STATUSES:
        return True
    return False


def _sleep_with_jitter(attempt: int, base: float = 1.0, max_delay: float = 30.0) -> None:
    delay = min(base * (2 ** (attempt - 1)), max_delay)
    jitter = random.uniform(0, delay * 0.1)
    time.sleep(delay + jitter)


class RetryStrategy:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        retryable: Callable[[Exception], bool] = _is_retryable,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retryable = retryable

    def execute(self, fn: Callable[[], Any], attempt: int = 1) -> Any:
        while True:
            try:
                return fn()
            except Exception as exc:
                if attempt >= self.max_retries or not self.retryable(exc):
                    raise
                _sleep_with_jitter(attempt, self.base_delay, self.max_delay)
                attempt += 1

    async def execute_async(self, fn: Callable[[], Any], attempt: int = 1) -> Any:
        import asyncio

        while True:
            try:
                return await fn()
            except Exception as exc:
                if attempt >= self.max_retries or not self.retryable(exc):
                    raise
                delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                jitter = random.uniform(0, delay * 0.1)
                await asyncio.sleep(delay + jitter)
                attempt += 1

    def decorate(self, fn: F) -> F:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.execute(lambda: fn(*args, **kwargs))

        return wrapper  # type: ignore[return-value]
