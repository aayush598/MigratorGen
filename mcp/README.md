# MigratorGen MCP Server

Model Context Protocol (MCP) server for AI-assisted code migration.

## Installation

```bash
pip install "migrator-gen-mcp[all]"
```

## Usage

### stdio transport (for IDE integration)

```bash
migrator-gen-mcp
# or
python -m mcp
```

### HTTP transport (for remote access)

```bash
migrator-gen-mcp --transport http --port 8001
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--transport` | `stdio` | Transport protocol: `stdio` or `http` |
| `--host` | `0.0.0.0` | Bind address (HTTP only) |
| `--port` | `8001` | Port number (HTTP only) |
| `--log-level` | `INFO` | Logging level |
| `--config` | — | Path to TOML config file |

## Tools

| Tool | Description |
|------|-------------|
| `generate_rules` | Generate migration rules from changelog / diff |
| `preview_migration` | Dry-run a migration and return the diff |
| `run_migration` | Apply migration rules to source code |
| `validate_rules` | Validate migration rules from a file |
| `analyze_code` | Extract imports / functions / classes from code |
| `suggest_migrations` | Suggest applicable migrations for a codebase |
| `create_migrator` | Generate a standalone pip-installable migrator package |
| `list_libraries` | List libraries with available migration packs |
| `explain_breaking_changes` | Explain breaking changes in a migration rule-set |
| `resolve_path` | Resolve migration path between two versions |

## Configuration

Create a `mcp.toml` file:

```toml
[mcp]
host = "127.0.0.1"
port = 8001
transport = "http"
log_level = "DEBUG"
```

Or use environment variables:

```bash
export MCP_HOST=127.0.0.1
export MCP_PORT=8001
export MCP_TRANSPORT=http
```
