"""Concrete CLI exception types."""

from .base import CLIError


class CommandError(CLIError):
    """A command failed during execution."""


class ParseError(CLIError):
    """Failed to parse user input or a file."""


class ConfigError(CLIError):
    """Invalid or missing configuration."""


class UserAbort(CLIError):
    """Operation aborted by the user."""

    def __init__(self, message: str = "Aborted.") -> None:
        super().__init__(message, exit_code=130)
