"""CLI framework: app, context, output, parser."""

from .context import CLIContext
from .output import OutputFormatter
from .parser import build_parser

__all__ = ["CLIContext", "OutputFormatter", "build_parser"]
