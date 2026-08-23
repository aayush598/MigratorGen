"""Pydantic settings for the MCP server."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MCPSettings(BaseModel):
    """Configurable settings for the MCP server."""

    host: str = Field(default="0.0.0.0", description="HTTP server bind address")
    port: int = Field(default=8001, ge=1, le=65535, description="HTTP server port")
    transport: str = Field(default="stdio", description="Transport protocol: stdio | http")
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        description="Log format string",
    )
    max_tool_timeout: int = Field(
        default=60, ge=1, le=300, description="Max tool execution timeout in seconds"
    )
    allowed_origins: list[str] = Field(default=["*"], description="CORS allowed origins (HTTP)")
    request_validation: bool = Field(default=True, description="Enable input validation")
    tool_auto_discovery: bool = Field(default=True, description="Auto-register tools on init")
