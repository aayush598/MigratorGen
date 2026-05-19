# MigratorGen CLI

Production-grade command-line interface for automated Python code migration.

## Quick start

```bash
# Install (from the monorepo root)
pip install -e cli

# Run migration
migrator-gen run app.py --rules migration_rules.json
```

## Commands

| Command | Description |
|---|---|
| `create` | Create migrator from changelog |
| `update` | Update migrator with new changelog |
| `migrate` / `run` | Apply migration to file/directory |
| `preview` | Show migration diff |
| `rules` | List migration rules |
| `validate-rules` | Validate rules file |
| `diff-rules` | Diff two rule sets |
| `audit` | Scan project for version references |
| `auto-upgrade` | Detect dependencies |
| `interactive` | Interactive rule builder |
| `export-schema` | Export JSON schema |

All commands support `--json` for machine-readable output.

## Documentation

See [docs/commands.md](docs/commands.md) for full command reference.
