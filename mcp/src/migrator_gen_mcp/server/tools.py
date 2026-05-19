"""MCPTool dataclass and ToolRegistry for managing tool definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class MCPTool:
    """A single MCP tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., str]
    categories: list[str] = field(default_factory=list)
    version_introduced: str = "0.1.0"


class ToolRegistry:
    """Registry for managing MCP tool lifecycle."""

    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}

    def register(self, tool: MCPTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> MCPTool | None:
        return self._tools.get(name)

    def all(self) -> list[MCPTool]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def by_category(self, category: str) -> list[MCPTool]:
        return [t for t in self._tools.values() if category in t.categories]
