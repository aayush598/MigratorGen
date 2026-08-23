"""Application entry point — wires parser, context, and command dispatch."""

from __future__ import annotations

import sys

from migrator_gen.exceptions import SDKError

from ..commands import COMMANDS
from ..version import __version__
from .context import CLIContext
from .output import OutputFormatter
from .parser import build_parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "version", False):
        print(f"migrator-gen {__version__}")
        return

    if not args.command:
        parser.print_help()
        sys.exit(1)

    ctx = CLIContext(args)
    out = OutputFormatter(json_mode=ctx.json_mode)

    try:
        handler = COMMANDS[args.command]
        handler(ctx, out)
    except SDKError as e:
        out.err(str(e))
    except KeyboardInterrupt:
        out.info("Aborted.")
        sys.exit(1)
    except Exception as e:
        if ctx.json_mode:
            out.print_json({"error": str(e)})
        else:
            out.err(f"Unexpected error: {e}", code=1)
    finally:
        ctx.close()
