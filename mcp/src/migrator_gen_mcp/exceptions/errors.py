"""MCP-specific exception hierarchy."""


class MCPError(Exception):
    """Base exception for all MCP server errors."""


class TransportError(MCPError):
    """Error related to transport layer (stdio, HTTP, WebSocket)."""


class ConfigError(MCPError):
    """Error related to server configuration."""


class HandlerError(MCPError):
    """Error during tool handler execution."""


class ToolNotFoundError(MCPError):
    """Requested tool is not registered."""


class ValidationError(MCPError):
    """Input validation failed."""
