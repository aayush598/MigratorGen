# Architecture

```
cli/
├── src/cli/
│   ├── cli/          # App framework: parser, context, output
│   ├── commands/     # Command handlers (migrate, rules, config, audit)
│   ├── services/     # Service layer wrapping SDK
│   ├── config/       # CLI-level configuration
│   ├── exceptions/   # CLI exception hierarchy
│   └── utils/        # Formatting, validation utilities
├── tests/
│   ├── unit/         # Unit tests (parser, config, output, utils)
│   └── integration/  # Integration tests (real command execution)
├── docs/
├── scripts/
└── examples/
```

## Key design decisions

- **`SyncMigrationClient`** used for all SDK interaction (CLI is synchronous)
- **`rich`** required dependency (no fallback) for consistent UX
- **`CLIContext`** holds per-command shared state (client, args, json_mode)
- **`OutputFormatter`** abstracts display; `--json` mode silences all human output
- Exceptions use `SDKError` from the SDK + `CLIError` for CLI-specific errors
