# migrator-gen

[![PyPI version](https://badge.fury.io/py/migrator-gen.svg)](https://pypi.org/project/migrator-gen/)
[![Python](https://img.shields.io/pypi/pyversions/migrator-gen)](https://pypi.org/project/migrator-gen/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Python SDK for **MigratorGen** — automatically migrate Python code across library versions using structured changelog rules and AST-accurate transformations.

## Features

- **Transactional migrations** — atomic all-or-nothing file modifications with checkpoint-based rollback
- **AST-aware transformations** — powered by [LibCST](https://github.com/Instagram/LibCST) for syntax-tree-level precision
- **Idempotency guards** — safe to re-run migrations without duplicating changes
- **Confidence scoring** — per-rule confidence metrics and safety classification (`safe` / `review_required` / `risky`)
- **Structured changelogs** — JSON-based rule packs describing renames, argument changes, module moves, and more
- **Sync and async clients** — use locally or connect to a remote MigratorGen API server

## Installation

```bash
pip install migrator-gen
```

For the full local engine (LibCST-based transformations):

```bash
pip install "migrator-gen[local]"
```

## Quick Start

```python
from migrator_gen import SyncMigrationClient, Rule, ChangeType

client = SyncMigrationClient()

rule = Rule(
    id="REQ-001",
    change_type=ChangeType.RENAME_FUNCTION,
    description="requests.get renamed to httpx.get",
    old_name="requests.get",
    new_name="httpx.get",
    version_introduced="2.0.0",
)

result = client.migrate_code(
    source_code="import requests\nresp = requests.get(url)",
    rules=[rule],
    target_version="2.0.0",
)

print(result.transformed_code)
# import requests
# resp = httpx.get(url)
```

## Preview Changes (Dry Run)

```python
preview = client.preview_migration(source_code, [rule])
print(preview.diff)  # Unified diff output
```

## Validate Rules

```python
report = client.validate_rules("migration-pack.json")
if report.valid:
    print("All rules are valid")
else:
    for error in report.errors:
        print(f"Error: {error['message']}")
```

## Async Client

```python
import asyncio
from migrator_gen import MigrationClient, Rule, ChangeType

async def main():
    async with MigrationClient() as client:
        rule = Rule(
            id="REQ-001",
            change_type=ChangeType.RENAME_FUNCTION,
            description="requests.get renamed to httpx.get",
            old_name="requests.get",
            new_name="httpx.get",
            version_introduced="2.0.0",
        )
        result = await client.migrate_code(
            source_code="import requests\nresp = requests.get(url)",
            rules=[rule],
            target_version="2.0.0",
        )
        print(result.transformed_code)

asyncio.run(main())
```

## Rule Structure

Rules are defined as JSON objects conforming to the `MigrationRule` schema:

```json
{
  "id": "H001",
  "change_type": "rename_function",
  "version_introduced": "1.0.0",
  "description": "Rename escape() to html.escape()",
  "old_name": "cgi.escape",
  "new_name": "html.escape",
  "safety": "safe",
  "confidence_hint": "high"
}
```

### Supported Change Types

| Change Type | Description |
|---|---|
| `rename_function` | Rename a function or method |
| `rename_class` | Rename a class |
| `rename_import` | Update import path |
| `add_argument` | Add a new function argument |
| `remove_argument` | Remove a function argument |
| `rename_argument` | Rename a function argument |
| `change_argument_default` | Change a default parameter value |
| `deprecate_function` | Mark a function as deprecated |
| `move_to_module` | Move code to a different module |
| `wrap_in_context_manager` | Wrap a call in a context manager |
| `sync_to_async` | Convert sync code to async |
| `enum_migration` | Migrate enum definitions |

See `migrator_gen.core.constants.ChangeType` for the full list.

## Configuration

```python
from migrator_gen import SyncMigrationClient

# Use defaults (local mode)
client = SyncMigrationClient()

# Custom configuration
client = SyncMigrationClient(
    mode="local",
    timeout=60,
    max_retries=5,
)
```

## Development

```bash
git clone https://github.com/aayush598/MigratorGen.git
cd MigratorGen/sdk/python
pip install -e ".[dev]"
pytest
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Author

**Aayush Gid** — [GitHub](https://github.com/aayush598) · [LinkedIn](https://www.linkedin.com/in/aayush-gid)
