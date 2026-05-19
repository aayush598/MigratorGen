# MCP Server Installation

## Quick Install

```bash
# From the workspace root
pip install -e "mcp[all]"
```

## Dependencies

Required:
- `migrator-gen>=0.2.0`
- `mcp>=1.0.0` (for stdio transport)
- `libcst` (for local migration engine)

Optional:
- `fastapi>=0.100` + `uvicorn>=0.20` (for HTTP transport)

## Verify Installation

```bash
migrator-gen-mcp --version
# → migrator-gen-mcp 0.2.0
```
