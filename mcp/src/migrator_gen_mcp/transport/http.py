"""HTTP transport for the MCP server — FastAPI + Uvicorn."""

from __future__ import annotations

import logging
import sys
from typing import Any

from ..config.settings import MCPSettings

log = logging.getLogger("migrator-gen.mcp.http")


def run_http_server(settings: MCPSettings | None = None) -> None:
    from ..server.app import MigratorGenMCPServer
    """Run the MCP server over HTTP transport using FastAPI."""
    try:
        import uvicorn
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError:
        print("[ERROR] fastapi/uvicorn not installed. Install: pip install fastapi uvicorn", file=sys.stderr)
        sys.exit(1)

    if settings is None:
        from ..config.settings import MCPSettings as S
        settings = S()

    mcp_server = MigratorGenMCPServer()

    app = FastAPI(
        title="MigratorGen MCP HTTP",
        version="0.2.0",
        description="Model Context Protocol server for code migration",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/tools")
    async def list_tools():
        return [
            {"name": t.name, "description": t.description, "inputSchema": t.input_schema}
            for t in mcp_server.get_tools()
        ]

    @app.post("/tools/{tool_name}/call")
    async def call_tool(tool_name: str, arguments: dict[str, Any] = {}):
        return {"result": mcp_server.call_tool(tool_name, arguments)}

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.2.0"}

    uvicorn.run(app, host=settings.host, port=settings.port)
