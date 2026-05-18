"""
Utility functions for MigratorGen platform.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, TypeVar

import aiofiles


def generate_request_id() -> str:
    """Generate a unique request ID (UUID4)."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def get_file_extension(filename: str) -> str:
    """Get the file extension (lowercase, with dot prefix)."""
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def safe_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename by removing dangerous characters.

    Args:
        filename: Original filename
        max_length: Maximum allowed length

    Returns:
        Sanitized filename safe for filesystem use
    """
    # Remove path separators and null bytes
    filename = filename.replace("/", "_").replace("\\", "_").replace("\x00", "")
    # Remove anything not alphanumeric, dash, underscore, dot, space
    filename = re.sub(r"[^\w.\- ]", "_", filename)
    # Collapse multiple spaces/underscores
    filename = re.sub(r"[\s_]+", "_", filename)
    # Remove leading/trailing whitespace and dots
    filename = filename.strip(". ")
    # Limit length
    if len(filename) > max_length:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        ext_len = len(ext) + 1 if ext else 0
        name = name[: max_length - ext_len]
        filename = f"{name}.{ext}" if ext else name
    return filename or "unnamed_file"


def validate_file_size(content: bytes, max_size_mb: int = 10) -> None:
    """
    Validate file size is within limit.

    Args:
        content: File content bytes
        max_size_mb: Maximum size in megabytes

    Raises:
        FileTooLargeError: If file exceeds limit
    """
    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        from .exceptions import FileTooLargeError

        raise FileTooLargeError(
            f"File size {len(content)} exceeds limit of {max_bytes} bytes",
            details={"size_bytes": len(content), "max_bytes": max_bytes},
        )


def validate_file_extension(
    filename: str,
    allowed: Tuple[str, ...] = ("py", "txt", "pyi"),
) -> None:
    """
    Validate file extension is allowed.

    Args:
        filename: Filename to check
        allowed: Tuple of allowed extensions

    Raises:
        UnsupportedFileTypeError: If extension not allowed
    """
    ext = get_file_extension(filename)
    if ext not in allowed:
        from .exceptions import UnsupportedFileTypeError

        raise UnsupportedFileTypeError(
            f"File extension '.{ext}' is not allowed. Allowed: {', '.join(allowed)}",
            details={"extension": ext, "allowed": list(allowed)},
        )


def compute_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """
    Compute a hash of a file's contents.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (sha256, md5, sha1)

    Returns:
        Hex digest of the hash
    """
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def format_bytes(bytes_count: int) -> str:
    """
    Format byte count as human-readable string.

    Examples:
        1024 -> "1.0 KB"
        1536 -> "1.5 KB"
        1048576 -> "1.0 MB"
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_count) < 1024:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} PB"


def format_duration(ms: float) -> str:
    """
    Format duration in milliseconds as human-readable string.

    Examples:
        500 -> "500ms"
        1500 -> "1.5s"
        90000 -> "1m 30s"
    """
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s" if seconds >= 1 else f"{ms:.0f}ms"
    minutes = int(seconds // 60)
    remaining = seconds % 60
    if minutes < 60:
        return f"{minutes}m {remaining:.0f}s"
    hours = int(minutes // 60)
    remaining_minutes = minutes % 60
    return f"{hours}h {remaining_minutes}m"


def chunked_reader(
    content: bytes,
    chunk_size: int = 8192,
) -> Generator[bytes, None, None]:
    """
    Yield chunks of bytes from content.

    Args:
        content: Bytes to chunk
        chunk_size: Size of each chunk

    Yields:
        Byte chunks
    """
    for i in range(0, len(content), chunk_size):
        yield content[i : i + chunk_size]


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge multiple dictionaries."""
    result = {}
    for d in dicts:
        if not d:
            continue
        for key, value in d.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = merge_dicts(result[key], value)
            else:
                result[key] = value
    return result


def deep_get(
    d: Dict[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    """
    Safely get a nested value from a dictionary.

    Args:
        d: Dictionary to traverse
        *keys: Sequence of keys
        default: Default value if not found

    Returns:
        Nested value or default
    """
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key)
        if d is None:
            return default
    return d


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """
    Parse a semantic version string.

    Args:
        version_str: Version like "2.0.0"

    Returns:
        Tuple of (major, minor, patch)
    """
    parts = version_str.strip().lstrip("v").split(".")
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    except (ValueError, IndexError):
        return (0, 0, 0)


T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential: bool = True,
):
    """
    Decorator to retry an async function with exponential backoff.

    Args:
        max_attempts: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap
        exponential: If True, use exponential backoff

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            import asyncio
            last_error: Optional[Exception] = None
            delay = base_delay
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(min(delay, max_delay))
                        if exponential:
                            delay = min(delay * 2, max_delay)
            if last_error:
                raise last_error
        return wrapper  # type: ignore
    return decorator


def slugify(text: str, max_length: int = 64) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:max_length].strip("-")


def truncate(text: str, length: int, suffix: str = "...") -> str:
    """Truncate text to a maximum length."""
    if len(text) <= length:
        return text
    return text[: length - len(suffix)].rstrip() + suffix