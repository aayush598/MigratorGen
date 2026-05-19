"""Base CLI exception — all CLI errors inherit from this."""


class CLIError(Exception):
    """Base exception for all CLI-level errors."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        self.exit_code = exit_code
        super().__init__(message)
