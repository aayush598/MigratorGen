"""
Exception hierarchy and retry strategies.
"""

from migrator_gen import ConfigurationError, SDKError
from migrator_gen.exceptions import (
    APIError,
    RateLimitError,
    TimeoutError,
)
from migrator_gen.utils import RetryStrategy

# --- Exception hierarchy ---
# SDKError (base)
# ├── ConfigurationError
# ├── APIError
# │   ├── AuthenticationError
# │   ├── RateLimitError
# │   ├── NotFoundError
# │   ├── ConflictError
# │   └── ValidationError
# ├── TimeoutError
# ├── MigrationError
# │   ├── MigrationParseError
# │   └── MigrationValidationError
# └── EngineError / MigrationEngineError

# --- Catch any SDK error ---
try:
    raise ConfigurationError("Invalid mode", details={"mode": "invalid"})
except SDKError as e:
    print(f"SDKError: {e}, details={e.details}")

# --- Catch an API error with status ---
try:
    raise RateLimitError("Rate limited")
except APIError as e:
    print(f"APIError (status {e.status_code}): {e}")

# --- RetryStrategy with default retryable check ---
retry = RetryStrategy(max_retries=3, base_delay=0.1)

# Sync usage — retry handles SDK TimeoutError
attempts = 0


def unreliable_call():
    global attempts
    attempts += 1
    if attempts < 3:
        raise TimeoutError("timed out")
    return "success"


result = retry.execute(unreliable_call)
print(f"Retry succeeded after {attempts} attempt(s): {result}")


# Custom retryable: catch any exception
def catch_all(exc):
    return True


catch_all_retry = RetryStrategy(max_retries=2, base_delay=0.05, retryable=catch_all)


def always_fails():
    raise ValueError("boom")


try:
    catch_all_retry.execute(always_fails)
except ValueError as e:
    print(f"Gave up after retries: {e}")

# Async usage
import asyncio


async def demo_retry_async():
    attempts = 0

    async def unreliable_async():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise TimeoutError("timed out")
        return "ok"

    result = await retry.execute_async(unreliable_async)
    print(f"Async retry result: {result}")


asyncio.run(demo_retry_async())


# Decorate a function with retry
@retry.decorate
def flaky_api_call():
    raise TimeoutError("service unavailable")
