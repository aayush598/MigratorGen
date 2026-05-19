# MigratorGen Python SDK

## Overview

The `migrator-gen` SDK (`migrator_gen` package) provides programmatic access to the
MigratorGen migration platform. It supports two modes:

- **local mode** — imports the `core` engine directly (requires `libcst`)
- **remote mode** — talks to the MigratorGen API via HTTP (requires `httpx`)

## Quick Start

```python
from migrator_gen import MigrationClient, Rule, ChangeType

client = MigrationClient(mode="local")
result = client.migrate_code(
    "def old_func(): pass",
    [Rule(
        id="R1",
        change_type=ChangeType.RENAME_FUNCTION,
        version_introduced="2.0.0",
        description="Rename function",
        old_name="old_func",
        new_name="new_func",
    )],
)
print(result.transformed_code)
```

## Installation

```bash
pip install migrator-gen[local]
```

## API Reference

See the [module reference](https://migrator-gen.readthedocs.io) for full documentation.
