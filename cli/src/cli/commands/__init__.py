"""Command registry — maps command names to handler functions."""

from typing import Any, Callable

from .audit import cmd_audit, cmd_auto_upgrade
from .config import cmd_create, cmd_export_schema, cmd_update, cmd_interactive
from .migrate import cmd_migrate
from .preview import cmd_preview
from .rules import cmd_diff_rules, cmd_rules, cmd_validate_rules

COMMANDS: dict[str, Callable[..., Any]] = {
    "create": cmd_create,
    "update": cmd_update,
    "migrate": cmd_migrate,
    "run": cmd_migrate,
    "preview": cmd_preview,
    "rules": cmd_rules,
    "interactive": cmd_interactive,
    "export-schema": cmd_export_schema,
    "validate-rules": cmd_validate_rules,
    "diff-rules": cmd_diff_rules,
    "audit": cmd_audit,
    "auto-upgrade": cmd_auto_upgrade,
}

__all__ = ["COMMANDS"]
