# migrator-gen

Python SDK for the [MigratorGen](https://github.com/migrator-gen/migrator-gen) platform — automate Python code migration across library versions.

## Installation

```bash
pip install migrator-gen            # basic (pydantic + yaml)
pip install "migrator-gen[local]"   # + libcst (local code transforms)
pip install "migrator-gen[remote]"  # + httpx (remote API client)
pip install "migrator-gen[all]"     # everything
```

## Quick start

```python
from migrator_gen import MigrationClient, Rule, ChangeType

client = MigrationClient()  # auto-detects local (default) or remote

rules = [
    Rule(
        id="R001",
        change_type=ChangeType.RENAME_FUNCTION,
        version_introduced="2.0.0",
        description="Rename old_func to new_func",
        old_name="old_func",
        new_name="new_func",
    )
]

result = client.migrate_code("def old_func(): pass", rules)
print(result.transformed_code)  # def new_func(): pass
```

## Configuration

The SDK reads configuration from, in order of priority:

| Source              | Example                                          |
|---------------------|--------------------------------------------------|
| Defaults            | `base_url="http://localhost:8000"`               |
| Environment vars    | `MIGRATOR_BASE_URL`, `MIGRATOR_API_KEY`, …       |
| TOML config file    | `~/.config/migrator-gen/config.toml`              |
| Programmatic kwargs | `MigrationClient(base_url="...", api_key="...")` |

## Key concepts

- **`MigrationClient`** — single entry point, auto-selects local or remote mode
- **`Rule`** — describes one code transformation (rename, add arg, move class, …)
- **`MigrateResponse`** — result of applying rules to source code
- **`ValidationReport`** — errors/warnings from rule-file validation
- **`ChangeType`** — enum of all supported transformation kinds

## Development

```bash
pip install -e "sdk/python[all,dev]"
pytest tests/
```

## License

MIT
