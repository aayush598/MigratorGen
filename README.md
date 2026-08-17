# MigratorGen — Library Migration Platform

> Automatically migrate Python code across library versions by parsing changelogs into structured, machine-executable rules. AST-accurate, transaction-safe, with REST API, MCP server, and parallel execution support.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [CLI Reference](#cli-reference)
- [REST API](#rest-api)
- [MCP Server](#mcp-server)
- [Python API](#python-api)
- [Supported Change Types](#supported-change-types)
- [Advanced Features](#advanced-features)
  - [Rule Conditions (`when`)](#rule-conditions-when)
  - [Rule Dependencies & Ordering](#rule-dependencies--ordering)
  - [Transactional Engine & Rollback](#transactional-engine--rollback)
  - [Validation & Safety](#validation--safety)
  - [Semantic Symbol Resolution](#semantic-symbol-resolution)
  - [Auto-Rule Generation from Git Diffs](#auto-rule-generation-from-git-diffs)
  - [LLM-Powered Suggestions](#llm-powered-suggestions)
  - [Parallel Migration](#parallel-migration)
- [Migration Packs](#migration-packs)
- [Writing Changelog JSON](#writing-changelog-json)
- [Testing](#testing)
- [Linting & Type Checking](#linting--type-checking)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# 1. Setup
git clone <repo-url>
cd migrator_platform
make install-dev     # Creates .venv, installs all dependencies

# 2. Run demo
python examples/demo_all_features.py

# 3. Run tests
make test            # 186 test cases (131 core + 55 shared)
make lint            # ruff linter

# 4. Create a migrator
migrator-gen create --changelog examples/mylib_changelog.json --library mylib

# 5. Start REST API
make docker-up && make health

# 6. Start MCP server
migrator-gen-mcp
```

---

## Architecture

```
Your Changelog (JSON)
         │
         ▼
  ┌──────────────────┐
  │  ChangelogParser  │  Parse versions + rules into MigrationRule objects
  └──────────────────┘
         │
         ▼
  ┌──────────────────┐
  │  VersionResolver  │  Resolve upgrade/downgrade paths (A→B)
  └──────────────────┘
         │
         ▼
  ┌────────────────────────┐
  │   RuleValidator         │  Validate rule schema, dependencies, conditions
  └────────────────────────┘
         │
         ▼
  ┌──────────────────────────────┐
  │ TransactionalMigrationEngine │  Apply rules with rollback + checkpoints
  └──────────────────────────────┘
         │
         ▼
  ┌────────────────────────┐
  │  LibCST Transformers   │  AST-level code transformations
  └────────────────────────┘
         │
         ▼
  ┌────────────────────────┐
  │  MigratorGenerator    │  Emit standalone pip-installable CLI package
  └────────────────────────┘
```

**Parallel pipeline:** For multi-file directories, `ParallelMigrationEngine` distributes work across CPU cores using `ProcessPoolExecutor`, with AST-level and disk caching for performance.

---

## Project Structure

```
migrator_platform/
├── sdk/python/src/migrator_gen/   # Core SDK library
│   ├── core/                      # Migration engine modules
│   │   ├── changelog_parser.py    # MigrationRule, ChangeType, VersionChangelog
│   │   ├── version_resolver.py    # VersionResolver, MigrationPath
│   │   ├── migration_engine.py    # TransactionalMigrationEngine, MigrationReport
│   │   ├── migrator_generator.py  # Generates standalone migrator package
│   │   ├── transformers.py        # LibCST transformers (16 base types)
│   │   ├── transformers_advanced.py  # 7 advanced transformers
│   │   ├── validation.py         # RuleValidator, IdempotencyChecker, RuleDependencyGraph
│   │   ├── symbol_resolver.py     # SymbolResolver, ImportGraph, ConfidenceScorer
│   │   ├── diff_analyzer.py       # GitDiffAnalyzer, ChangelogToRulesConverter
│   │   ├── llm_engine.py          # LLMSuggestionEngine (Anthropic/OpenAI)
│   │   └── parallel_engine.py     # ParallelMigrationEngine, ASTCache, DiskCache
│   ├── api/                       # REST clients (async + sync)
│   ├── services/                  # Local and remote service backends
│   ├── config/                    # SDK configuration (SDKConfig)
│   └── exceptions/                # SDK exception hierarchy
├── cli/src/cli/                   # CLI package (migrator-gen)
│   ├── app.py                     # main() entrypoint
│   ├── commands/                  # CLI subcommands (create, migrate, preview, rules, etc.)
│   └── services/                  # CLI service layer
├── mcp/src/migrator_gen_mcp/      # MCP server (migrator-gen-mcp)
│   ├── server/
│   │   ├── app.py                 # MCP server class + main() entrypoint
│   │   ├── handlers.py            # Tool handler implementations
│   │   └── tools.py               # MCPTool definitions and registry
│   ├── transport/                 # stdio and HTTP transports
│   └── config/                    # MCP server settings
├── backend/                       # Backend services
│   ├── api/src/
│   │   ├── server.py              # Full-featured FastAPI REST API (13+ endpoints)
│   │   └── main.py                # Minimal FastAPI app (containerized deployments)
│   └── worker/src/
│       ├── celery_app.py          # Celery app config (Redis broker)
│       ├── run.py                 # Worker entry point
│       └── tasks/                 # Celery task definitions
├── shared/                        # Shared utilities package (migrators-shared)
│   ├── logging.py                 # Structured JSON logging with structlog
│   ├── exceptions.py              # RFC 7807 Problem Details exceptions + Sentry
│   ├── metrics.py                 # Prometheus metrics collector
│   ├── middleware.py               # CORS, rate limiting, request ID injection
│   ├── utils.py                   # File validation, hashing, retry, datetime utils
│   ├── database.py                # Async SQLAlchemy models + connection pooling
│   └── cache.py                   # Async Redis cache manager with TTL
├── examples/
│   ├── mylib_changelog.json       # Example changelog (4 versions, 11 rules)
│   ├── sample_user_code.py        # Sample target file to migrate
│   └── demo_all_features.py       # Demo of all 17 features
├── migration-packs/               # Pre-built rule sets
│   ├── pydantic.json              # 20 rules for Pydantic v1→v2
│   ├── fastapi.json               # 4 rules for FastAPI migration
│   └── httpx.json                 # 3 rules for httpx migration
├── tests/
│   ├── unit/core/test_platform.py # 131 test cases covering all core modules
│   ├── unit/packages/test_shared.py # 55 test cases covering shared utilities
│   └── test_project_end_to_end.py # End-to-end integration tests
├── infra/docker/                  # Docker + docker-compose + K8s manifests
├── .github/workflows/             # CI (lint, typecheck, test, security, docker-build)
├── Makefile                       # Development shortcuts
├── pyproject.toml                 # Project metadata, ruff, mypy, pytest config
├── CONTRIBUTING.md                # Contribution guidelines
├── CHANGELOG.md                   # Project changelog
├── LICENSE                        # MIT license
└── README.md
```

## Shared Utilities

Reusable components across all services (`shared/`):

| Module | Description |
|---|---|
| `logging.py` | Structured JSON logging with request IDs, log levels, service name |
| `exceptions.py` | RFC 7807 Problem Details exceptions + global exception handler + Sentry |
| `metrics.py` | Prometheus metrics (requests, migrations, cache, LLM calls, Celery) |
| `middleware.py` | CORS, rate limiting, request ID injection, security headers, compression |
| `utils.py` | File validation, hashing, retry with backoff, datetime, slugify, truncate |
| `database.py` | Async SQLAlchemy models (MigrationJob, MigrationSession) with connection pooling |
| `cache.py` | Async Redis cache manager with JSON serialization and TTL |

## Python SDK

`MigrationClient` (async) and `SyncMigrationClient` for programmatic API access:

```python
from migrator_gen import MigrationClient

client = MigrationClient(mode="local")
result = client.migrate(code, rules, source_version="1.0.0", target_version="2.0.0")
```

---

## Installation

**Python 3.10+ required.**

```bash
# Clone and enter directory
cd migrator_platform

# Create virtual environment and install everything
make install-dev

# Or manually:
uv venv .venv && source .venv/bin/activate
make install-sdk          # Install migrator_gen SDK
uv pip install -e ".[dev]"  # Install workspace with dev extras
```

**Core dependencies** (`pyproject.toml`):

| Package | Purpose |
|---|---|
| `libcst>=1.0.0` | Concrete Syntax Tree — powers all code transformations |
| `pydantic>=2.0.0` | Rule/schema validation models |

---

## CLI Reference

```bash
source .venv/bin/activate
migrator-gen <command>
```

### `create` — Build a Migrator Package

```bash
migrator-gen create \
  --changelog examples/mylib_changelog.json \
  --library mylib \
  --output ./generated
```

### `migrate` — Migrate Code

```bash
migrator-gen migrate \
  --rules generated/migration_rules.json \
  --from 1.0.0 \
  --to 3.0.0 \
  ./myproject/
```

### `preview` — Dry-run a File

```bash
migrator-gen preview \
  --rules generated/migration_rules.json \
  --from 1.0.0 \
  --to 2.0.0 \
  examples/sample_user_code.py
```

### `rules` — Inspect Rules

```bash
migrator-gen rules --rules generated/migration_rules.json
```

### `interactive` — Manual Rule Builder

```bash
migrator-gen interactive --output my_rules.json
```

---

## REST API

Start the server:
```bash
# Using make
make run-api

# Or directly
uvicorn backend.api.src.server:app --host 0.0.0.0 --port 8000 --reload
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/migrate` | Migrate code string with rules |
| `POST` | `/api/v1/migrate/file` | Migrate an uploaded file |
| `POST` | `/api/v1/preview` | Preview migration as unified diff |
| `POST` | `/api/v1/validate` | Validate rules from a file |
| `POST` | `/api/v1/generate-rules/changelog` | Auto-generate rules from changelog text |
| `POST` | `/api/v1/generate-rules/diff` | Auto-generate rules from git diff |
| `POST` | `/api/v1/suggest` | Suggest migrations for a file |
| `POST` | `/api/v1/resolve-path` | Resolve migration path between versions |
| `GET` | `/api/v1/libraries` | List available libraries |
| `POST` | `/api/v1/parse-changelog` | Parse a changelog file |
| `POST` | `/api/v1/generate-package` | Generate a standalone migrator package |
| `POST` | `/api/v1/dependencies/check` | Check if migrations exist for dependencies |

### Example: Migrate via API

```bash
curl -X POST http://localhost:8000/api/v1/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "source_code": "Client()",
    "rules": [{"id": "R1", "change_type": "rename_class", "version_introduced": "2.0.0",
      "description": "Rename", "old_name": "Client", "new_name": "APIClient"}],
    "source_version": "1.0.0",
    "target_version": "2.0.0"
  }'
```

---

## MCP Server

Start the MCP server for tool integration:

```bash
migrator-gen-mcp
# or with HTTP transport:
migrator-gen-mcp --transport http --port 8001
```

The server exposes **10 tools** for MCP-compatible hosts:

| Tool | Description |
|---|---|
| `generate_rules` | Generate migration rules from a changelog or by comparing old and new code |
| `preview_migration` | Preview migration changes as a unified diff |
| `run_migration` | Apply migration rules to source code |
| `validate_rules` | Validate migration rules from a file |
| `analyze_code` | Analyse source code: extract imports, functions, classes |
| `suggest_migrations` | Analyse a file and suggest migration packs that apply |
| `list_libraries` | List libraries with available migration packs |
| `explain_breaking_changes` | Explain breaking changes from a set of rules in human-readable terms |
| `resolve_path` | Resolve the migration path between two versions of a library |
| `create_migrator` | Generate a standalone pip-installable migrator package |

---

## Python API

```python
from migrator_gen.core.changelog_parser import ChangelogParser, MigrationRule, ChangeType
from migrator_gen.core.version_resolver import VersionResolver
from migrator_gen.core.migration_engine import TransactionalMigrationEngine

# 1. Parse
parser = ChangelogParser()
changelogs = parser.parse(Path('examples/mylib_changelog.json').read_text())

# 2. Resolve path
resolver = VersionResolver(changelogs)
path = resolver.resolve_path('1.0.0', '3.0.0')

# 3. Migrate
engine = TransactionalMigrationEngine()
result = engine.migrate_code("connect(host='localhost')", path.rules)
print(result.transformed_code)
```

---

## Supported Change Types

| Change Type | Description | Key Fields |
|---|---|---|
| `rename_function` | Renames function calls/definitions | `old_name`, `new_name` |
| `rename_class` | Renames class usages | `old_name`, `new_name` |
| `rename_attribute` | Renames `.old` → `.new` | `old_name`, `new_name` |
| `rename_import` | Renames symbol and/or moves module | `old_name`, `new_name`, `old_module`, `new_module` |
| `add_argument` | Adds keyword arg to call sites | `function_name`, `argument_name`, `default_value` |
| `remove_argument` | Removes argument from call sites | `function_name`, `argument_name` |
| `change_argument_default` | Changes parameter default | `function_name`, `argument_name`, `default_value` |
| `reorder_arguments` | Reorders arguments | `function_name`, `new_order` |
| `deprecate_function` | Adds `# DEPRECATED:` comment | `old_name`, `replacement` |
| `remove_function` | Marks removed function calls | `old_name` |
| `remove_class` | Marks removed class usages | `old_name` |
| `replace_with_property` | Converts `.method()` → `.prop` | `old_name`, `new_name` |
| `move_to_module` | Updates import path | `old_name`, `source_module`, `target_module` |
| `add_decorator` | Adds decorator to function | `function_name`, `decorator_name` |
| `remove_decorator` | Removes decorator | `function_name`, `decorator_name` |
| `rename_argument` | Renames keyword argument | `function_name`, `argument_name`, `new_argument_name` |
| `sync_to_async` | Converts sync ↔ async functions | `function_name`, `extra.convert_to_async` |
| `wrap_in_context_manager` | Wraps function in context manager | `function_name`, `decorator_name` |
| `class_split` | Extracts methods to new class | `extra.split_class`, `extra.extract_methods`, `extra.new_class_name` |
| `module_split` | Extracts symbols to new module | `source_module`, `extra.extract_symbols`, `target_module` |
| `change_return_type` | Changes function return annotation | `function_name`, `extra.new_return_type` |
| `enum_migration` | Renames enum values | `old_name`, `new_name`, `extra.enum_class` |
| `dataclass_field_change` | Changes dataclass field defs | `old_name`, `new_name`, `extra.field_operation` |

---

## Advanced Features

### Rule Conditions (`when`)

Rules can include conditional activation using the `when` clause:

```json
{
  "id": "R-001",
  "change_type": "rename_function",
  "version_introduced": "2.0.0",
  "description": "Rename Client",
  "old_name": "Client",
  "new_name": "APIClient",
  "when": {
    "imported_from": "mylib.legacy",
    "inside_class": "Service",
    "python_version": ">=3.8"
  }
}
```

Supported conditions:
- `imported_from` — only when imported from a specific module
- `not_imported_from` — only when NOT from a module
- `inside_class` / `outside_class` — scope-based filtering
- `inside_function` — only within specific function
- `python_version`, `min_python_version`, `max_python_version` — version gating
- `has_decorator` / `lacks_decorator` — decorator presence
- `returns_type` — return type filtering
- `called_from_module` — call site filtering
- `called_as_method` — method vs function call
- `custom_condition` — arbitrary Python expression

### Rule Dependencies & Ordering

Rules can declare execution order:

```json
{
  "id": "R-002",
  "change_type": "add_argument",
  "version_introduced": "2.0.0",
  "description": "Add timeout",
  "function_name": "connect",
  "argument_name": "timeout",
  "default_value": "30",
  "depends_on": ["R-001"],
  "priority": 50,
  "conflicts_with": ["R-OLD"],
  "run_after": ["R-001"]
}
```

- `priority` (0-1000, lower = higher priority)
- `depends_on` — rule must run after referenced rule
- `conflicts_with` — rules that cannot coexist
- `run_after` — explicit ordering directive

`RuleDependencyGraph` validates these and produces a DAG-based execution order.

### Transactional Engine & Rollback

`TransactionalMigrationEngine` provides:
- **Rollback**: On syntax error, restores original code from checkpoint
- **Checkpoints**: Saves state before each rule application
- **Confidence scoring**: Per-rule confidence (high/medium/low)
- **Safety classification**: `safe`, `review_required`, `risky`
- **Dry-run mode**: Preview changes without file modification

```python
from migrator_gen.core.migration_engine import TransactionalMigrationEngine, SafetyLevel

engine = TransactionalMigrationEngine()
result = engine.migrate_code(code, rules, dry_run=False)

print(f"Confidence: {result.average_confidence}")
print(f"Changes: {result.changes}")
print(f"Modified: {result.was_modified}")
```

### Validation & Safety

`RuleValidator` validates all rules before migration:

```python
from migrator_gen.core.validation import RuleValidator

validator = RuleValidator()
report = validator.validate_rules(rules)
if not report.valid:
    for error in report.errors:
        print(f"ERROR: {error.message}")
```

Checks include:
- Required/forbidden fields per change type
- Conflicting rename rules
- Invalid Python identifiers
- Invalid module paths
- Dependency cycle detection
- Reversibility warnings

`IdempotencyChecker` verifies rules produce identical output when applied twice:
```python
from migrator_gen.core.validation import IdempotencyChecker
is_safe = IdempotencyChecker.check_rule_idempotency(rule, code, None)
```

### Semantic Symbol Resolution

`SymbolResolver` uses LibCST metadata providers (`ScopeProvider`, `QualifiedNameProvider`) for accurate, scope-aware symbol resolution:

```python
from migrator_gen.core.symbol_resolver import SymbolResolver

resolver = SymbolResolver(code)
resolver._build_import_graph()
src = resolver._import_graph.import_sources.get("Client")
# -> "mylib"
```

`ConfidenceScorer` rates rule confidence based on change type and scope:

```python
from migrator_gen.core.symbol_resolver import ConfidenceScorer

score = ConfidenceScorer.score_import_change(stmt, "mylib", "Client")
```

### Auto-Rule Generation from Git Diffs

`GitDiffAnalyzer` automatically extracts migration rules from code diffs:

```python
from migrator_gen.core.diff_analyzer import GitDiffAnalyzer

analyzer = GitDiffAnalyzer(old_code, new_code)
rules = analyzer.analyze()
# Returns list of MigrationRule dicts
```

`ChangelogToRulesConverter` parses human-readable changelog text:

```python
from migrator_gen.core.diff_analyzer import ChangelogToRulesConverter

converter = ChangelogToRulesConverter(
    text="renamed Client to APIClient\nadded timeout parameter",
    version="2.0.0"
)
rules = converter.convert()
```

### LLM-Powered Suggestions

`LLMSuggestionEngine` uses Anthropic or OpenAI to suggest migration strategies:

```python
from migrator_gen.core.llm_engine import LLMSuggestionEngine

engine = LLMSuggestionEngine()
suggestions = engine.suggest_from_error(
    error_message="TypeError: got an unexpected keyword argument 'timeout'",
    code_context="connect(host='localhost', timeout=30)",
)
```

Requires environment variables: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`.

### Parallel Migration

`ParallelMigrationEngine` distributes file migration across CPU cores:

```python
from pathlib import Path
from migrator_gen.core.parallel_engine import ParallelMigrationEngine

engine = ParallelMigrationEngine(max_workers=4)
report = engine.migrate_directory(Path('./myproject/'), rules)
print(report.summary())
```

Features:
- `ProcessPoolExecutor` for true parallelism
- AST-level LRU cache (`ASTCache`)
- Disk-based cache for repeated migrations (`DiskCache`)
- Per-file and aggregate reports

---

## Migration Packs

Pre-built rule sets for popular libraries are in `migration-packs/`:

| Pack | Description |
|---|---|
| `pydantic.json` | 20 rules: Pydantic v1 → v2 (`model_validator`, `ConfigDict`, etc.) |
| `fastapi.json` | 4 rules: FastAPI dependency changes |
| `httpx.json` | 3 rules: httpx async client migration |

```bash
# Use a migration pack
migrator-gen create \
  --changelog migration-packs/pydantic.json \
  --library pydantic \
  --output ./pydantic_migrator
```

---

## Writing Changelog JSON

```json
{
  "library": "mylib",
  "versions": [
    {
      "version": "2.0.0",
      "release_date": "2024-03-01",
      "notes": "Breaking changes",
      "rules": [
        {
          "id": "R-001",
          "change_type": "rename_function",
          "version_introduced": "2.0.0",
          "description": "Renamed connect() to create_connection()",
          "old_name": "connect",
          "new_name": "create_connection",
          "confidence_hint": "high",
          "tags": ["api-change"],
          "safety": "safe"
        },
        {
          "id": "R-002",
          "change_type": "add_argument",
          "version_introduced": "2.0.0",
          "description": "Added timeout parameter",
          "function_name": "create_connection",
          "argument_name": "timeout",
          "default_value": "30",
          "when": {
            "imported_from": "mylib",
            "min_python_version": "3.8"
          },
          "depends_on": ["R-001"],
          "priority": 100
        }
      ]
    }
  ]
}
```

**Only include fields relevant to the change type.** Each `change_type` has specific required and forbidden fields (validated by `RuleValidator`).

---

## Testing

```bash
# Run full test suite
make test
# or:
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/unit/core/test_platform.py::TestChangelogParserBasics -v

# Run shared library tests
python -m pytest tests/unit/packages/test_shared.py -v

# Run SDK tests
python -m pytest sdk/python/tests/ -v
```

**186 test cases** total (131 core + 55 shared libs):
- Changelog parsing & serialization
- Version resolution & path building
- All 16 base transformers + 7 advanced transformers
- Transformer map completeness
- Rule conditions (`when` clauses)
- Rule dependencies & ordering
- Validation reports & error detection
- CAPABILITIES registry
- Rule dependency graph (DAG, cycle detection)
- Idempotency checking & fingerprinting
- Import graph & symbol resolution
- Confidence scoring
- Migration engine (single file, multi-file, dry-run, preview)
- Safety classification
- Migration report formatting
- Changelog-to-rules conversion
- Git diff analysis
- LLM suggestion engine
- Parallel migration engine
- AST and disk caching
- Full end-to-end pipeline
- Edge cases (empty code, comments, multiline strings)
- libs/shared: logging, exceptions, metrics, utils, database models, cache

---

## Linting & Type Checking

Pre-commit hooks are configured (`.pre-commit-config.yaml`):

```bash
# Install pre-commit
uv pip install pre-commit
pre-commit install

# Run all hooks manually
pre-commit run --all-files
```

Tools configured:
- **ruff** + **ruff-format** — linting and formatting
- **mypy** — type checking (`--ignore-missing-imports`)
- **bandit** — security scanning
- **pyright** — static type analysis
- **pre-commit-hooks** — trailing whitespace, YAML, large files, merge conflicts

Run linting directly (if tools installed in venv):
```bash
ruff check cli/ mcp/ sdk/python/ backend/ shared/ tests/ --fix
ruff format .
mypy cli/ mcp/ sdk/python/ backend/ tests/ --ignore-missing-imports
```

---

## Examples

### 1. Demo all features
```bash
python examples/demo_all_features.py
```
Prints output for all 17 major features.

### 2. Create and use a migrator
```bash
# Create
migrator-gen create \
  --changelog examples/mylib_changelog.json \
  --library mylib \
  --output ./generated

# Install
cd generated && uv pip install -e . && cd ..

# List versions
mylib_migrator list-versions

# Preview migration
mylib_migrator migrate \
  --from 1.0.0 --to 3.0.0 \
  examples/sample_user_code.py --preview

# Apply migration
mylib_migrator migrate \
  --from 1.0.0 --to 3.0.0 \
  examples/sample_user_code.py
```

### 3. Start REST API and migrate via HTTP
```bash
# Terminal 1: Start API
make run-api

# Terminal 2: Make requests
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/libraries
```

### 4. Auto-generate rules from a changelog
```bash
migrator-gen migrate \
  --rules migration-packs/pydantic.json \
  --from 1.0.0 \
  --to 2.0.0 \
  ./my_project/
```

### 5. Parallel migration
```python
from pathlib import Path
from migrator_gen.core.parallel_engine import ParallelMigrationEngine
from migrator_gen.core.changelog_parser import ChangelogParser
from migrator_gen.core.version_resolver import VersionResolver

parser = ChangelogParser()
changelogs = parser.parse(open("migration-packs/pydantic.json").read())
resolver = VersionResolver(changelogs)
path = resolver.resolve_path("1.0.0", "2.0.0")

engine = ParallelMigrationEngine(max_workers=8)
report = engine.migrate_directory(Path("./my_project/"), path.rules)
print(report.summary())
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'core'`
The `core` package lives inside the SDK at `migrator_gen.core`. Install the SDK first: `make install-sdk`. Import via `from migrator_gen.core.xxx import ...` or use the SDK's top-level API (`from migrator_gen import ...`).

### `ModuleNotFoundError: No module named 'libcst'`
Activate venv and reinstall: `source .venv/bin/activate && make install-sdk`.

### `mylib_migrator: command not found`
Install the generated package: `cd generated && uv pip install -e .`.

### Migration produces no changes
Check versions exist: `mylib_migrator list-versions`. Confirm source code uses old API names. Use `--preview` to inspect diffs.

### API server won't start
Check port is free: `lsof -i :8000`. If busy, kill the process or use `--port 8001`.

### MCP server won't start
Ensure dependencies are installed: `make install-dev`. Check for import errors: `python -c "import migrator_gen_mcp"`.
