"""stdio transport for the MCP server — used by IDE integrations."""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

log = logging.getLogger("migrator-gen.mcp.stdio")


def run_stdio_server() -> None:
    from ..server.app import MigratorGenMCPServer

    """Run the MCP server over stdio transport."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool
    except ImportError:
        print("[ERROR] MCP library not installed. Install: pip install mcp", file=sys.stderr)
        sys.exit(1)

    server = Server("migrator-gen")
    mcp_server = MigratorGenMCPServer()

    @server.list_tools()
    async def list_tools():
        return [
            Tool(name=t.name, description=t.description, inputSchema=t.input_schema)
            for t in mcp_server.get_tools()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]):
        result = mcp_server.call_tool(name, arguments)
        return [TextContent(type="text", text=result)]

    async def _main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(_main())
