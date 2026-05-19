# Configuration

The CLI accepts a `--config` flag pointing to a TOML config file:

```toml
[migrator_gen]
mode = "local"
timeout = 60
max_retries = 5
log_level = "DEBUG"
```

The config is parsed by `SDKConfig` (from the SDK) and overlaid with CLI-level settings.

## Environment variables

All SDK config fields can also be set via environment variables with the `MIGRATOR_` prefix:

- `MIGRATOR_BASE_URL`
- `MIGRATOR_API_KEY`
- `MIGRATOR_TIMEOUT`
- `MIGRATOR_MODE`
- `MIGRATOR_MAX_RETRIES`
- `MIGRATOR_LOG_LEVEL`
