# Architecture

```
mcp/
├── src/mcp/
│   ├── __init__.py          # Public API exports
│   ├── __main__.py          # python -m mcp
│   ├── version.py           # Version string
│   ├── server/              # Core server logic
│   │   ├── app.py           # MigratorGenMCPServer + main()
│   │   ├── handlers.py      # Tool handler implementations
│   │   └── tools.py         # MCPTool dataclass + ToolRegistry
│   ├── transport/           # Transport layer
│   │   ├── stdio.py         # stdio MCP transport
│   │   └── http.py          # HTTP (FastAPI) transport
│   ├── config/              # Configuration
│   │   ├── settings.py      # MCPSettings (pydantic)
│   │   └── loader.py        # Layered config loader
│   ├── exceptions/          # Exception hierarchy
│   │   └── errors.py        # MCPError base + subclasses
│   └── utils/               # Utilities
│       ├── formatting.py    # Response formatters
│       └── validators.py    # Input validation
```

## Layered Design

```
                   ┌─────────────┐
                   │  CLI Flags   │
                   ├─────────────┤
                   │  TOML File   │
                   ├─────────────┤
                   │  Env Vars    │
                   ├─────────────┤
                   │  Defaults    │
                   └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  MCPSettings │
                   └─────────────┘
                          │
                          ▼
              ┌──────────────────────┐
              │ MigratorGenMCPServer │
              ├──────────────────────┤
              │ ToolRegistry (10×)   │
              │ ToolHandlers (SDK)   │
              └──────────────────────┘
                     ↕        ↕
              ┌────────┐ ┌────────┐
              │ stdio  │ │  HTTP  │
              └────────┘ └────────┘
```
