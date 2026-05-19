"""CLI-level settings not covered by SDKConfig."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CLISettings:
    """CLI-specific configuration (SDK config is handled by SDKConfig)."""

    output_dir: Path = Path.cwd()
    backup_suffix: str = ".bak"
    max_preview_lines: int = 80
    audit_max_files: int = 20
    progress_spinner: bool = True
