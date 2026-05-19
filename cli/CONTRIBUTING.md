# Contributing

## Setup

```bash
pip install -e ".[dev]"
```

## Development

```bash
make lint     # ruff check
make format   # ruff format
make typecheck  # mypy
make test     # pytest
```

## Adding a command

1. Create `src/cli/commands/new_feature.py` with a `cmd_new_feature(ctx, out)` function
2. Register in `src/cli/commands/__init__.py` and `src/cli/cli/parser.py`
3. Add tests in `tests/`
