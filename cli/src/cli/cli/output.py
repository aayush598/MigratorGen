"""Output formatting — rich console + plain fallback."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

_console = Console()


class OutputFormatter:
    """Abstracts rich vs plain output. Delegates to RichOutput by default."""

    def __init__(self, json_mode: bool = False) -> None:
        self.json_mode = json_mode

    def info(self, msg: str) -> None:
        if not self.json_mode:
            _console.print(f"[cyan]ℹ[/cyan] {msg}")

    def ok(self, msg: str) -> None:
        if not self.json_mode:
            _console.print(f"[green]✓[/green] {msg}")

    def warn(self, msg: str) -> None:
        if not self.json_mode:
            _console.print(f"[yellow]⚠[/yellow] {msg}")

    def err(self, msg: str, code: int = 1) -> None:
        _console.print(f"[red]✗[/red] {msg}")
        sys.exit(code)

    def print_json(self, data: Any) -> None:
        print(json.dumps(data, indent=2, default=str))

    def table(self, title: str, columns: list[str], rows: list[list[str]]) -> None:
        if self.json_mode:
            return
        table = Table(title=title, show_header=True, header_style="bold")
        for col in columns:
            table.add_column(col)
        for row in rows:
            table.add_row(*row)
        _console.print(table)

    def syntax(self, code: str, lang: str = "python") -> None:
        if self.json_mode:
            return
        _console.print(Syntax(code, lang))

    def progress(self, description: str = "Working...") -> Progress:
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=_console,
        )
