# MigratorGen — Code Migration Platform

> Automatically migrate Python code across library versions by parsing changelogs into structured, machine-executable rules.

MigratorGen reads your library's changelog (JSON), extracts breaking changes, and produces a **standalone CLI migrator package** that users install once and run to upgrade (or downgrade) their codebase — fully automated, AST-accurate, with backup safety.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Requirements & Setup](#requirements--setup)
- [Core Concepts](#core-concepts)
  - [Changelog Formats](#changelog-formats)
  - [Supported Change Types](#supported-change-types)
- [Using the CLI](#using-the-cli)
  - [create — Build a Migrator](#create--build-a-migrator)
  - [update — Add New Versions](#update--add-new-versions)
  - [run — Migrate Code](#run--migrate-code)
  - [preview — Dry-run a File](#preview--dry-run-a-file)
  - [rules — Inspect Rules](#rules--inspect-rules)
  - [interactive — Manual Rule Builder](#interactive--manual-rule-builder)
- [Using the Generated Migrator](#using-the-generated-migrator)
  - [Installing the Generated Package](#installing-the-generated-package)
  - [Generated CLI Commands](#generated-cli-commands)
- [Python API (Programmatic Usage)](#python-api-programmatic-usage)
- [Writing Your Changelog JSON](#writing-your-changelog-json)
- [Downgrade Support](#downgrade-support)
- [Backup Behaviour](#backup-behaviour)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## How It Works

```
Your Changelog (JSON)
         │
         ▼
  ┌──────────────────┐
  │  ChangelogParser  │  ──→  Parses versions + rules
  └──────────────────┘

         │
         ▼
  ┌──────────────────┐
  │  VersionResolver  │  ──→  Computes ordered rule list for any A→B path
  └──────────────────┘
         │
         ▼
  ┌──────────────────┐
  │  MigrationEngine  │  ──→  Applies CST transformers to source files
  └──────────────────┘
         │
         ▼
  ┌────────────────────┐
  │  MigratorGenerator │  ──→  Emits a pip-installable standalone CLI package
  └────────────────────┘
```

---

## Project Structure

```
migrator_platform/
├── cli/
│   └── cli.py                  # Main CLI entry point (MigratorGen platform)
│
├── core/
│   ├── changelog_parser.py     # Parses JSON changelogs into MigrationRule objects
│   ├── version_resolver.py     # Resolves upgrade/downgrade paths between arbitrary versions
│   ├── migration_engine.py     # Applies transformation rules to Python source files
│   ├── migrator_generator.py   # Generates the standalone distributable migrator package
│   ├── transformers.py         # libcst-based AST transformers for each change type
│   └── __init__.py
│
├── examples/
│   ├── mylib_changelog.json    # Example structured JSON changelog
│   └── sample_user_code.py     # Example target Python file to migrate
│
├── generated_migrator/         # Output of `cli create` — distributable migrator package
│   ├── mylib_migrator/
│   │   ├── __init__.py
│   │   └── __main__.py         # Self-contained migrator with all rules embedded
│   ├── migration_rules.json    # Raw exported rules (can be reused with `cli run`)
│   ├── setup.py
│   └── README.md
│
├── tests/                      # Test suite
├── requirements.txt
└── README.md
```

---

## Requirements & Setup

**Python 3.8+** is required.

```bash
# Clone the project
git clone <repo-url>
cd migrator_platform

# Create a virtual environment (using uv — recommended on CachyOS/Arch)
uv venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

`requirements.txt` currently installs:

| Package | Purpose |
|---|---|
| `libcst>=1.0.0` | Concrete Syntax Tree — powers all code transformations |
| `pytest>=7.0.0` | Testing |

> **Note for CachyOS / Arch users:** Always use `uv pip` inside the activated `.venv`, not the system `pip`. Run `source .venv/bin/activate` before any command.

---

## Core Concepts

### Changelog Formats

MigratorGen accepts two input formats:

#### 1. Structured JSON (recommended)

A JSON file that explicitly lists every version and its machine-readable rules.

```json
{
  "library": "mylib",
  "versions": [
    {
      "version": "2.0.0",
      "release_date": "2024-03-01",
      "notes": "Major breaking release",
      "rules": [
        {
          "change_type": "rename_function",
          "version_introduced": "2.0.0",
          "description": "Renamed connect() to create_connection()",
          "old_name": "connect",
          "new_name": "create_connection"
        }
      ]
    }
  ]
}
```

---

### Supported Change Types

| `change_type` | What it does | Required extra fields |
|---|---|---|
| `rename_function` | Renames a function call everywhere | `old_name`, `new_name` |
| `rename_class` | Renames a class everywhere (incl. instantiation) | `old_name`, `new_name` |
| `rename_attribute` | Renames an object attribute (`.old` → `.new`) | `old_name`, `new_name` |
| `rename_import` | Renames a symbol and/or moves it to a new module | `old_name`, `new_name`, `old_module`, `new_module` |
| `add_argument` | Adds a keyword argument with a default value to all call sites | `function_name`, `argument_name`, `default_value` |
| `remove_argument` | Removes a keyword argument from all call sites | `function_name`, `argument_name` |
| `change_argument_default` | Changes the default value of a parameter | `function_name`, `argument_name`, `default_value` |
| `reorder_arguments` | Reorders arguments in function call sites | `function_name`, `new_order` |
| `deprecate_function` | Adds a `# DEPRECATED:` comment above all call sites | `old_name`, `replacement` |
| `remove_function` | Marks call sites of a removed function | `old_name` |
| `remove_class` | Marks usages of a removed class | `old_name` |
| `replace_with_property` | Converts method calls (`.method()`) to property access (`.prop`) | `old_name`, `new_name` |
| `move_to_module` | Updates import path when a symbol moves modules | `old_name`, `source_module`, `target_module` |
| `add_decorator` | Adds a decorator to a named function | `function_name`, `decorator_name` |
| `remove_decorator` | Removes a decorator from a named function | `function_name`, `decorator_name` |
| `wrap_in_context_manager` | Wraps a block in a `with` statement | `function_name` |
| `custom_transform` | Reserved for custom transformations | (depends) |

---

## Using the CLI

All CLI commands are in `cli/cli.py`. Run from the project root:

```bash
# Always activate venv first
source .venv/bin/activate

python cli/cli.py <command> [options]
```

---

### `create` — Build a Migrator

Reads a changelog and generates a complete, pip-installable migrator package.

```bash
python cli/cli.py create \
  --changelog examples/mylib_changelog.json \
  --library mylib \
  --output ./generated_migrator
```

| Flag | Required | Description |
|---|---|---|
| `--changelog` | Yes | Path to changelog file (`.json`) |
| `--library` | Yes | The library name (e.g. `mylib`, `requests`) |
| `--output` | No | Output directory (default: `./generated_migrator`) |

**Output structure:**
```
generated_migrator/
├── mylib_migrator/
│   ├── __init__.py
│   └── __main__.py       ← All rules embedded here; self-contained
├── migration_rules.json  ← Raw rule export (reusable)
├── setup.py
└── README.md
```

---

### `update` — Add New Versions

Update an already-generated migrator with rules from a newer changelog:

```bash
python cli/cli.py update \
  --existing generated_migrator/migration_rules.json \
  --new-changelog CHANGELOG_v4.json \
  --output ./generated_migrator
```

| Flag | Required | Description |
|---|---|---|
| `--existing` | Yes | Path to existing `migration_rules.json` |
| `--new-changelog` | Yes | Path to the new changelog file |
| `--output` | No | Output dir (defaults to same location as `--existing`) |
| `--library` | No | Override library name |

Only **new versions** found in the new changelog will be merged in — existing versions are preserved.

---

### `run` — Migrate Code

Apply migration rules to a file or entire directory of Python files:

```bash
# Migrate a whole project directory
python cli/cli.py run \
  --rules generated_migrator/migration_rules.json \
  --from 1.0.0 \
  --to 3.0.0 \
  ./myproject/

# Migrate a single file
python cli/cli.py run \
  --rules generated_migrator/migration_rules.json \
  --from 1.0.0 \
  --to latest \
  myfile.py
```

| Flag | Required | Description |
|---|---|---|
| `path` | Yes | File or directory to migrate (positional) |
| `--rules` | Yes | Path to `migration_rules.json` |
| `--from` | Yes | Source version (e.g. `1.0.0`) |
| `--to` | No | Target version (default: `latest`) |
| `--dry-run` | No | Show what would change, but don't write files |
| `--no-backup` | No | Skip creating `.py.bak` backup files |

---

### `preview` — Dry-run a File

Show a unified diff of what the migration would change in a single file, without modifying it:

```bash
python cli/cli.py preview \
  --rules generated_migrator/migration_rules.json \
  --from 1.0.0 \
  --to 2.0.0 \
  examples/sample_user_code.py
```

| Flag | Required | Description |
|---|---|---|
| `file` | Yes | Python file to preview (positional) |
| `--rules` | Yes | Path to `migration_rules.json` |
| `--from` | Yes | Source version |
| `--to` | No | Target version (default: `latest`) |

---

### `rules` — Inspect Rules

List all migration rules inside a `migration_rules.json` file:

```bash
python cli/cli.py rules --rules generated_migrator/migration_rules.json
```

Example output:
```
📚 Migration rules for: mylib
==================================================

  v2.0.0 (2024-03-01) - 5 rule(s)
    • [rename_function] [connect -> create_connection] Renamed connect() to create_connection()
    • [rename_class] [Client -> APIClient] Client class renamed to APIClient
    ...
```

---

### `interactive` — Manual Rule Builder

Build migration rules step-by-step in your terminal — no changelog file needed:

```bash
python cli/cli.py interactive --output my_rules_v2.json
```

The wizard will prompt you for:
1. Version number
2. Change type (from a numbered list)
3. Type-specific fields (old name, new name, module, argument, etc.)

Repeat for as many rules as needed, then type `0` to finish. Rules are saved to the specified JSON file.

---

## Using the Generated Migrator

The `create` command outputs a standalone Python package. This is what you distribute to your library's users — they don't need to install MigratorGen itself.

### Installing the Generated Package

```bash
cd generated_migrator

# Install (editable mode, recommended for development)
pip install -e .
# or with uv:
uv pip install -e .
```

This registers the `mylib_migrator` command on your PATH.

### Generated CLI Commands

#### List supported versions
```bash
mylib_migrator list-versions
# or equivalently:
python -m mylib_migrator list-versions
```

Output:
```
Available versions for mylib:
  v1.1.0  (1 rule)
  v2.0.0  (5 rules)
  v2.1.0  (3 rules)
  v3.0.0  (3 rules)
```

#### Migrate a project
```bash
# Upgrade from v1.0.0 to latest
mylib_migrator migrate --from 1.0.0 --to latest ./myproject/

# Upgrade to a specific version
mylib_migrator migrate --from 1.0.0 --to 2.0.0 ./myproject/

# Downgrade
mylib_migrator migrate --from 3.0.0 --to 1.0.0 ./myproject/

# Dry run (no files written)
mylib_migrator migrate --from 1.0.0 --to latest ./myproject/ --dry-run

# Migrate + show unified diffs instead of writing
mylib_migrator migrate --from 1.0.0 --to latest myfile.py --preview

# Migrate without creating .bak backups
mylib_migrator migrate --from 1.0.0 --to latest ./myproject/ --no-backup
```

#### Validate a file parses correctly
```bash
mylib_migrator validate myfile.py
```

---

## Python API (Programmatic Usage)

You can use all components directly in your own Python scripts:

```python
from pathlib import Path
from core.changelog_parser import ChangelogParser
from core.version_resolver import VersionResolver
from core.migration_engine import MigrationEngine

# 1. Parse a changelog
content = Path('examples/mylib_changelog.json').read_text()
parser = ChangelogParser()
changelogs = parser.parse(content, fmt='json')   # or fmt='auto'

# 2. Resolve the migration path
resolver = VersionResolver(changelogs)
path = resolver.resolve_path('1.0.0', '3.0.0')

print(f"Migration: {path.source_version} → {path.target_version}")
print(f"Is upgrade: {path.is_upgrade}")
print(f"Rules: {len(path.rules)}")

# 3. Migrate a string of code
engine = MigrationEngine()
result = engine.migrate_code(source_code, path.rules)
print(result.transformed_code)
print(result.changes)        # List of human-readable change descriptions
print(result.was_modified)   # bool
print(result.errors)         # Any errors encountered

# 4. Migrate a file in place
result = engine.migrate_file(
    Path('myfile.py'),
    path.rules,
    dry_run=False,   # Set True to skip writing
    backup=True,     # Creates myfile.py.bak before overwriting
)

# 5. Migrate an entire directory
report = engine.migrate_directory(
    Path('./myproject/'),
    path,
    dry_run=False,
    backup=True,
)
print(report.summary())

# 6. Preview as unified diff
preview = engine.preview_migration(source_code, path.rules)
print(preview)
```

### Working with MigrationRule objects directly

```python
from core.changelog_parser import MigrationRule, ChangeType

rule = MigrationRule(
    change_type=ChangeType.RENAME_FUNCTION,
    version_introduced="2.0.0",
    description="Renamed old_func to new_func",
    old_name="old_func",
    new_name="new_func",
)

# Serialize / deserialize
d = rule.to_dict()
rule2 = MigrationRule.from_dict(d)
```

### Generating the Migrator Package Programmatically

```python
from core.migrator_generator import MigratorGenerator

generator = MigratorGenerator(library_name="mylib")
output_path = generator.generate(changelogs, output_dir="./dist/")
```

---

## Writing Your Changelog JSON

The JSON schema for a full changelog:

```json
{
  "library": "<your-library-name>",
  "versions": [
    {
      "version": "2.0.0",
      "release_date": "2024-03-01",
      "notes": "Optional human-readable notes",
      "rules": [
        {
          "change_type": "<see table above>",
          "version_introduced": "2.0.0",
          "description": "Human-readable description of this change",

          "old_name": "old_function_name",
          "new_name": "new_function_name",

          "function_name": "some_function",
          "argument_name": "verbose",
          "default_value": "30",

          "old_module": "mylib.old",
          "new_module": "mylib.new",

          "source_module": "mylib.helpers",
          "target_module": "mylib.utils",

          "replacement": "new_function_name",
          "decorator_name": "handler"
        }
      ]
    }
  ]
}
```

**Only include the fields relevant to your change type.** Unused fields can be omitted or set to `null`.

---


## Downgrade Support

The `VersionResolver` supports **backwards migrations** — simply set `--from` to the higher version and `--to` to the lower one:

```bash
mylib_migrator migrate --from 3.0.0 --to 1.0.0 ./myproject/
```

Reversible rules (renames, import moves, attribute renames) are automatically inverted. Non-reversible rules (function/class removal, decorator additions) emit a warning and are skipped.

| Change type | Reversible? |
|---|---|
| `rename_function` | Yes (swaps old/new) |
| `rename_class` | Yes |
| `rename_attribute` | Yes |
| `rename_import` | Yes |
| `remove_function` | No (warns and skips) |
| `remove_class` | No (warns and skips) |
| All others | Warning (warns and skips) |

---

## Backup Behaviour

By default, whenever a file is modified, the **original is saved with a `.bak` extension** in the same directory:

```
myfile.py      ← migrated version
myfile.py.bak  ← original backup
```

To skip backups, pass `--no-backup` to `run` or `migrate`.

---

## Examples

### Full end-to-end example

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Generate migrator from the provided example changelog
python cli/cli.py create \
  --changelog examples/mylib_changelog.json \
  --library mylib \
  --output ./generated_migrator

# 3. Install the generated migrator
cd generated_migrator && uv pip install -e . && cd ..

# 4. Check supported versions
mylib_migrator list-versions

# 5. Preview changes on the example file
mylib_migrator migrate --from 1.0.0 --to 3.0.0 examples/sample_user_code.py --preview

# 6. Apply the migration
mylib_migrator migrate --from 1.0.0 --to 3.0.0 examples/sample_user_code.py

# 7. Inspect the result
cat examples/sample_user_code.py
```

### Running the platform programmatic demo

```bash
python demo_migration.py
```

This runs a full end-to-end demo: parsing the JSON changelog, resolving v1.0.0→v3.0.0, applying 12 rules to sample code, and printing the migrated output.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'core'`

Run the CLI from the project root with the full path:
```bash
# From project root:
python cli/cli.py create ...
```
`cli/cli.py` adds its parent directory to `sys.path` automatically, so always run it as `python cli/cli.py` (not `python -m cli.cli` or from within the `cli/` directory).

### `ModuleNotFoundError: No module named 'libcst'`

Install the dependencies inside your venv:
```bash
source .venv/bin/activate
uv pip install -r requirements.txt
```

### `mylib_migrator: command not found`

You need to install the generated package first:
```bash
cd generated_migrator
uv pip install -e .
```
Then make sure your venv is active when you run it.

### Migration produces no changes

- Check that the versions you specified with `--from` and `--to` actually exist by running `list-versions`.
- Confirm your source file actually uses the old API names the rules are looking for.
- Try `--preview` mode to see the diff without committing changes.
