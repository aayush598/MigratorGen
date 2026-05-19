# Changelog

## 0.2.0 (unreleased)

- Restructured from single-file `main.py` to production-grade package layout
- Added `rich` as required dependency for consistent UX
- Migration from `MigrationClient` (async) to `SyncMigrationClient` (sync)
- Added `CLIContext`, `OutputFormatter`, exception hierarchy
- Added comprehensive test suite (unit + integration)
- Added documentation, scripts, examples

## 0.1.0 (initial)

- Single-file CLI with argparse and `rich` fallback
- 11 subcommands: create, update, migrate, preview, rules, interactive, export-schema, validate-rules, diff-rules, audit, auto-upgrade
