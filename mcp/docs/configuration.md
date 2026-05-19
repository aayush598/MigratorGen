# Configuration

The MCP server supports layered configuration:

1. **Defaults** — built into `MCPSettings`
2. **Environment variables** — prefixed with `MCP_`
3. **TOML config file** — passed via `--config`
4. **CLI flags** — highest priority (e.g. `--port`)

## Environment Variables

| Variable | Maps to | Default |
|----------|---------|---------|
| `MCP_HOST` | `host` | `0.0.0.0` |
| `MCP_PORT` | `port` | `8001` |
| `MCP_TRANSPORT` | `transport` | `stdio` |
| `MCP_LOG_LEVEL` | `log_level` | `INFO` |

## TOML Config File

```toml
[mcp]
host = "127.0.0.1"
port = 8001
transport = "http"
log_level = "DEBUG"
allowed_origins = ["http://localhost:3000"]
request_validation = true
max_tool_timeout = 120
```
