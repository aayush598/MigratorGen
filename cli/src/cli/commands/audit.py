"""audit / auto-upgrade — scan projects for version references."""

from __future__ import annotations

import re
from pathlib import Path

from ..cli.context import CLIContext
from ..cli.output import OutputFormatter
from ..utils.validators import STDLIB_MODULES


def cmd_audit(ctx: CLIContext, out: OutputFormatter) -> None:
    args = ctx.args
    directory = Path(args.directory)
    if not directory.exists():
        out.err(f"Directory not found: {directory}")

    rules_path = Path(args.rules) if args.rules else None
    if not rules_path or not rules_path.exists():
        out.err("--rules is required for audit")

    client = ctx.client
    mf = client.parse_changelog(str(rules_path))
    available = [v.version for v in mf.versions]

    py_files = list(directory.rglob("*.py"))
    version_pattern = re.compile(r'["\']?(\d+\.\d+\.\d+)["\']?')

    if ctx.json_mode:
        results = []
        for f in py_files:
            content = f.read_text(encoding="utf-8", errors="ignore")
            found = version_pattern.findall(content)
            if found:
                results.append({"file": str(f), "versions": sorted(set(found))})
        out.print_json(
            {
                "directory": str(directory),
                "available_versions": available,
                "file_count": len(py_files),
                "version_references": results,
            }
        )
        return

    out.info(f"Scanning: {directory}")
    out.info(f"Rules: {rules_path}")
    out.info(f"Available versions: {', '.join(available)}")
    out.info(f"Python files: {len(py_files)}")

    for f in py_files[:20]:
        content = f.read_text(encoding="utf-8", errors="ignore")
        found = version_pattern.findall(content)
        if found:
            print(f"  {f.relative_to(directory)}: mentions {set(found)}")

    if len(py_files) > 20:
        print(f"  ... and {len(py_files) - 20} more files")


def cmd_auto_upgrade(ctx: CLIContext, out: OutputFormatter) -> None:
    args = ctx.args
    directory = Path(args.directory)
    if not directory.exists():
        out.err(f"Directory not found: {directory}")

    req_file = directory / "requirements.txt"
    pyproject_file = directory / "pyproject.toml"

    if ctx.json_mode:
        info: dict = {"directory": str(directory)}
        if req_file.exists():
            deps = [
                d.strip()
                for d in req_file.read_text().splitlines()
                if d.strip() and not d.startswith("#")
            ]
            info["type"] = "requirements.txt"
            info["dependencies"] = deps
        elif pyproject_file.exists():
            matches = re.findall(r'["\']?([a-zA-Z0-9_-]+)\s*[<>=!]+', pyproject_file.read_text())
            info["type"] = "pyproject.toml"
            info["dependencies"] = matches
        else:
            info["type"] = "scan"
            info["imports"] = sorted(_scan_imports(directory))
        out.print_json(info)
        return

    out.info(f"Analyzing: {directory}")

    if req_file.exists():
        out.info("Found requirements.txt")
        deps = [
            d.strip()
            for d in req_file.read_text().splitlines()
            if d.strip() and not d.startswith("#")
        ]
        for dep in deps:
            print(f"   • {dep}")
    elif pyproject_file.exists():
        out.info("Found pyproject.toml")
        matches = re.findall(r'["\']?([a-zA-Z0-9_-]+)\s*[<>=!]+', pyproject_file.read_text())
        for dep in matches:
            print(f"   • {dep}")
    else:
        out.info("Scanning Python files for imports ...")
        imports_found = _scan_imports(directory)
        for imp in sorted(imports_found)[:20]:
            print(f"   • {imp}")
        if len(imports_found) > 20:
            print(f"   ... and {len(imports_found) - 20} more")


def _scan_imports(directory: Path) -> set:
    imports_found: set = set()
    for f in directory.rglob("*.py"):
        content = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"^import\s+([a-zA-Z_][a-zA-Z0-9_.]*)", content, re.MULTILINE):
            base = m.group(1).split(".")[0]
            if base not in STDLIB_MODULES:
                imports_found.add(base)
        for m in re.finditer(r"^from\s+([a-zA-Z_][a-zA-Z0-9_.]+)\s+import", content, re.MULTILINE):
            base = m.group(1).split(".")[0]
            if base not in STDLIB_MODULES:
                imports_found.add(base)
    return imports_found
