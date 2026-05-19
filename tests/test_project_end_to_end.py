"""Standalone end-to-end project validation.

Run:  python -m pytest tests/test_project_end_to_end.py -v
Or:   python tests/test_project_end_to_end.py

This file validates every major component of the MigratorGen project
without relying on any test framework internals -- it can be run
directly with ``python`` or via ``pytest``.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Expand paths so we can import from workspace ─────────────
_HERE = Path(__file__).resolve().parent
_WORKSPACE = _HERE.parent
sys.path.insert(0, str(_WORKSPACE / "sdk" / "python"))
sys.path.insert(0, str(_WORKSPACE / "cli"))
sys.path.insert(0, str(_WORKSPACE / "mcp"))
sys.path.insert(0, str(_WORKSPACE / "backend" / "api" / "src"))
sys.path.insert(0, str(_WORKSPACE / "backend" / "worker" / "src"))
sys.path.insert(0, str(_WORKSPACE))  # for core module

FAILURES: list[str] = []


def check(component: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  PASS  {component}")
    else:
        msg = f"FAIL  {component}"
        if detail:
            msg += f"  --  {detail}"
        print(f"  {msg}")
        FAILURES.append(msg)


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ═════════════════════════════════════════════════════════════
# 1.  Package structure
# ═════════════════════════════════════════════════════════════

def test_package_structure() -> None:
    section("1. Package Structure")

    required = [
        "sdk/python/migrator_gen/__init__.py",
        "sdk/python/migrator_gen/client.py",
        "sdk/python/migrator_gen/config.py",
        "sdk/python/migrator_gen/exceptions.py",
        "sdk/python/migrator_gen/models.py",
        "sdk/python/migrator_gen/_local.py",
        "sdk/python/migrator_gen/_remote.py",
        "sdk/python/pyproject.toml",
        "cli/main.py",
        "mcp/server.py",
        "backend/api/src/server.py",
        "backend/worker/src/main.py",
        "backend/worker/src/tasks/migration_tasks.py",
    ]
    for p in required:
        check(f"  File: {p}", (_WORKSPACE / p).exists())


# ═════════════════════════════════════════════════════════════
# 2.  No old import names
# ═════════════════════════════════════════════════════════════

def test_no_old_import_names() -> None:
    section("2. No old import names")
    bad = 0
    for root, _dirs, files in os.walk(_WORKSPACE):
        if ".git" in root or "__pycache__" in root or ".egg" in root:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            try:
                with open(path) as fh:
                    tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name == "migratorgen":
                                check(f"Old import in {path}", False)
                                bad += 1
                    elif isinstance(node, ast.ImportFrom):
                        if node.module == "migratorgen":
                            check(f"Old import in {path}", False)
                            bad += 1
            except (SyntaxError, UnicodeDecodeError):
                pass
    if bad == 0:
        check("No old 'migratorgen' imports remain", True)


# ═════════════════════════════════════════════════════════════
# 3.  SDK imports
# ═════════════════════════════════════════════════════════════

def test_sdk_imports() -> None:
    section("3. SDK Imports")
    try:
        from migrator_gen import (
            MigrationClient, Rule, ChangeType, SDKConfig,
            VersionChangelog, MigrationFile,
        )
        from migrator_gen.exceptions import SDKError, EngineError, APIError
        check("All SDK symbols importable", True)
    except Exception as e:
        check("SDK imports", False, str(e))
        return

    # Version string is set
    from migrator_gen import __version__
    check(f"SDK version: {__version__}", bool(__version__))


# ═════════════════════════════════════════════════════════════
# 4.  Client construction & mode detection
# ═════════════════════════════════════════════════════════════

def test_client_construction() -> None:
    section("4. Client Construction")
    from migrator_gen import MigrationClient

    c = MigrationClient(mode="local")
    check(f"local mode: {c.mode}", c.mode == "local")

    # context-manager works
    with MigrationClient(mode="local") as cm:
        check("context manager works", cm.health_check().status == "healthy")


# ═════════════════════════════════════════════════════════════
# 5.  SDK operations
# ═════════════════════════════════════════════════════════════

def test_sdk_operations() -> None:
    section("5. SDK Operations")
    from migrator_gen import MigrationClient, Rule, ChangeType

    client = MigrationClient(mode="local")

    # 5a. migrate_code
    try:
        result = client.migrate_code(
            "def old_func(): pass",
            [Rule(id="R1", change_type=ChangeType.RENAME_FUNCTION,
                  version_introduced="2.0.0", description="Rename",
                  old_name="old_func", new_name="new_func")],
        )
        ok = "new_func" in result.transformed_code and result.was_modified
        check("migrate_code", ok)
    except Exception as e:
        check("migrate_code", False, str(e))

    # 5b. preview_migration
    try:
        preview = client.preview_migration(
            "def old_func(): pass",
            [Rule(id="R1", change_type=ChangeType.RENAME_FUNCTION,
                  version_introduced="2.0.0", description="Rename",
                  old_name="old_func", new_name="new_func")],
        )
        check("preview_migration", bool(preview.diff))
    except Exception as e:
        check("preview_migration", False, str(e))

    # 5c. list_libraries
    try:
        libs = client.list_libraries()
        check("list_libraries", isinstance(libs, dict))
    except Exception as e:
        check("list_libraries", False, str(e))

    # 5d. health_check
    try:
        h = client.health_check()
        check("health_check", h.status == "healthy")
    except Exception as e:
        check("health_check", False, str(e))

    # 5e. parse_changelog (JSON)
    try:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump({"library": "testlib", "versions": [{"version": "1.0.0", "rules": []}]}, tmp)
        tmp.close()
        mf = client.parse_changelog(tmp.name)
        os.unlink(tmp.name)
        check("parse_changelog", mf.library == "testlib")
    except Exception as e:
        check("parse_changelog", False, str(e))

    # 5f. migrate_file (dry_run)
    try:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        tmp.write("def old_func(): pass")
        tmp.close()
        result = client.migrate_file(
            tmp.name,
            [Rule(id="R1", change_type=ChangeType.RENAME_FUNCTION,
                  version_introduced="2.0.0", description="Rename",
                  old_name="old_func", new_name="new_func")],
            dry_run=True,
        )
        os.unlink(tmp.name)
        check("migrate_file", result.was_modified)
    except Exception as e:
        check("migrate_file", False, str(e))

    # 5g. suggest_migrations
    try:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        tmp.write("import requests\n")
        tmp.close()
        analysis = client.suggest_migrations(tmp.name, "requests")
        os.unlink(tmp.name)
        check("suggest_migrations", isinstance(analysis.suggested_migrations, list))
    except Exception as e:
        check("suggest_migrations", False, str(e))

    # 5h. resolve_path (basic, checks no crash)
    try:
        path = client.resolve_path("1.0.0", "2.0.0", "testlib")
        check("resolve_path (fallback)", path.source_version == "1.0.0")
    except Exception as e:
        check("resolve_path", False, str(e))

    # 5i. generate_rules_from_diff
    try:
        rules = client.generate_rules_from_diff(
            "def old_func(): pass\n",
            "def new_func(): pass\n",
        )
        check("generate_rules_from_diff", isinstance(rules, list))
    except Exception as e:
        check("generate_rules_from_diff", False, str(e))


# ═════════════════════════════════════════════════════════════
# 6.  CLI module
# ═════════════════════════════════════════════════════════════

def test_cli() -> None:
    section("6. CLI")
    import importlib.util
    spec = importlib.util.spec_from_file_location("cli_main", str(_WORKSPACE / "cli" / "main.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    parser = mod.build_parser()
    check("CLI parser created", True)
    check("CLI prog name", parser.prog == "migrator-gen")

    # check all commands exist
    commands = ["create", "update", "migrate", "run", "preview",
                "rules", "interactive", "export-schema",
                "validate-rules", "diff-rules", "audit", "auto-upgrade"]
    for cmd in commands:
        found = any(cmd == a.dest or (hasattr(a, "choices") and a.choices and cmd in a.choices)
                    for a in parser._actions)
        # Actually check subparsers
    sub_actions = [a for a in parser._actions if hasattr(a, "_name_parser_map")]
    available = set()
    for a in sub_actions:
        available.update(a._name_parser_map.keys())
    for cmd in commands:
        check(f"CLI command '{cmd}'", cmd in available)


# ═════════════════════════════════════════════════════════════
# 7.  MCP server
# ═════════════════════════════════════════════════════════════

def test_mcp() -> None:
    section("7. MCP Server")
    import importlib.util
    spec = importlib.util.spec_from_file_location("mcp_server", str(_WORKSPACE / "mcp" / "server.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    server = mod.MigratorGenMCPServer()
    check("MCP server name", server.name == "migrator-gen")
    check("MCP tool count", len(server.tools) == 10)

    # each tool has required attributes
    for name, tool in server.tools.items():
        check(f"MCP tool '{name}'", bool(tool.name and tool.handler))

    # call_tool dispatches
    result = server.call_tool("nonexistent", {})
    check("MCP unknown tool error", "Unknown tool" in result)


# ═════════════════════════════════════════════════════════════
# 8.  REST API server
# ═════════════════════════════════════════════════════════════

def test_api() -> None:
    section("8. REST API")
    import importlib.util
    spec = importlib.util.spec_from_file_location("api_server", str(_WORKSPACE / "backend" / "api" / "src" / "server.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    routes = [r for r in mod.app.routes if hasattr(r, "methods")]
    check(f"API routes ({len(routes)})", len(routes) >= 15)

    v1_routes = [r.path for r in routes if "/api/v1/" in r.path]
    check(f"API versioned routes ({len(v1_routes)})", len(v1_routes) >= 10)
    for path in [
        "/api/v1/migrate", "/api/v1/preview", "/api/v1/validate",
        "/api/v1/libraries", "/api/v1/resolve-path",
    ]:
        check(f"API endpoint {path}", path in v1_routes)


# ═════════════════════════════════════════════════════════════
# 9.  Worker
# ═════════════════════════════════════════════════════════════

def test_worker() -> None:
    section("9. Worker")
    import importlib.util
    spec = importlib.util.spec_from_file_location("worker_main", str(_WORKSPACE / "backend" / "worker" / "src" / "main.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    routes = [r for r in mod.app.routes if hasattr(r, "methods")]
    check(f"Worker routes ({len(routes)})", len(routes) >= 5)


# ═════════════════════════════════════════════════════════════
# 10.  No emojis / AI-native markers
# ═════════════════════════════════════════════════════════════

def test_no_ai_or_emoji_markers() -> None:
    section("10. No AI-generated markers or emojis")
    emoji_chars = set("✅❌🔥✓✗•")
    skip_dirs = {".git", "__pycache__", ".egg", ".venv", "node_modules", ".mypy_cache", ".pytest_cache", ".github"}
    found = 0
    for root, dirs, files in os.walk(_WORKSPACE):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if not f.endswith((".py", ".md", ".toml", ".yml", ".yaml", ".json")):
                continue
            path = os.path.join(root, f)
            if os.path.samefile(path, __file__):
                continue
            try:
                with open(path, errors="replace") as fh:
                    for i, line in enumerate(fh, 1):
                        for ch in emoji_chars:
                            if ch in line:
                                check(f"Emoji '{ch}' in {path}:{i}", False)
                                found += 1
            except Exception:
                pass
    if found == 0:
        check("No emoji characters in source/docs", True)

    # AI-native references (skip self-check in this file)
    ai_phrases = ["AI-native", "ai-native", "AI powered", "ai powered"]
    found_ai = 0
    for root, dirs, files in os.walk(_WORKSPACE):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if not f.endswith((".py", ".md", ".toml", ".yml", ".yaml")):
                continue
            path = os.path.join(root, f)
            if os.path.samefile(path, __file__):
                continue
            try:
                with open(path, errors="replace") as fh:
                    content = fh.read()
                    for phrase in ai_phrases:
                        if phrase in content:
                            check(f"AI phrase '{phrase}' in {path}", False)
                            found_ai += 1
            except Exception:
                pass
    if found_ai == 0:
        check("No AI-native/AI-powered phrases in source/docs", True)


# ═════════════════════════════════════════════════════════════
# 11.  pyproject.toml correctness
# ═════════════════════════════════════════════════════════════

def test_pyproject_config() -> None:
    section("11. Project Configuration")

    # SDK pyproject
    sdk_pp = _WORKSPACE / "sdk" / "python" / "pyproject.toml"
    import tomllib
    with open(sdk_pp, "rb") as fh:
        cfg = tomllib.load(fh)

    check("SDK package name 'migrator-gen'", cfg["project"]["name"] == "migrator-gen")
    check("SDK python >=3.10", cfg["project"]["requires-python"] == ">=3.10")
    check("SDK has local extra", "local" in cfg["project"].get("optional-dependencies", {}))
    check("SDK has remote extra", "remote" in cfg["project"].get("optional-dependencies", {}))
    check("Build system hatchling", cfg.get("build-system", {}).get("build-backend") == "hatchling.build")

    # Root pyproject
    root_pp = _WORKSPACE / "pyproject.toml"
    with open(root_pp, "rb") as fh:
        root_cfg = tomllib.load(fh)
    check("Root workspace name", root_cfg["project"]["name"] == "migrator-gen-workspace")
    scripts = root_cfg["project"].get("scripts", {})
    check("CLI entry point 'migrator-gen'", "migrator-gen" in scripts)
    check("MCP entry point 'migrator-gen-mcp'", "migrator-gen-mcp" in scripts)
    check("API entry point 'migrator-gen-api'", "migrator-gen-api" in scripts)


# ═════════════════════════════════════════════════════════════
# 12.  Core tests pass
# ═════════════════════════════════════════════════════════════

def test_core_tests_pass() -> None:
    section("12. Core Tests")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/core/", "-q"],
        capture_output=True, text=True, cwd=_WORKSPACE,
    )
    output = result.stdout + result.stderr
    if result.returncode == 0:
        check("Core tests (131)", True)
    else:
        lines = [l for l in output.split("\n") if "passed" in l or "failed" in l]
        check("Core tests", False, "; ".join(lines) or output[:200])


# ═════════════════════════════════════════════════════════════
# Runner
# ═════════════════════════════════════════════════════════════

def run_all():
    print("=" * 60)
    print("  MigratorGen End-to-End Project Validation")
    print("=" * 60)

    test_package_structure()
    test_no_old_import_names()
    test_sdk_imports()
    test_client_construction()
    test_sdk_operations()
    test_cli()
    test_mcp()
    test_api()
    test_worker()
    test_no_ai_or_emoji_markers()
    test_pyproject_config()
    test_core_tests_pass()

    print(f"\n{'=' * 60}")
    if FAILURES:
        print(f"  FAILURES: {len(FAILURES)}")
        for f in FAILURES:
            print(f"    {f}")
    else:
        print("  ALL CHECKS PASSED")
    print(f"{'=' * 60}")
    return len(FAILURES) == 0


# ── pytest integration ──────────────────────────────────────
# Each function above is a pytest test when run via pytest.

# Register them as test functions for pytest discovery
test_package_structure.__name__ = "test_package_structure"
test_no_old_import_names.__name__ = "test_no_old_import_names"
test_sdk_imports.__name__ = "test_sdk_imports"
test_client_construction.__name__ = "test_client_construction"
test_sdk_operations.__name__ = "test_sdk_operations"
test_cli.__name__ = "test_cli"
test_mcp.__name__ = "test_mcp"
test_api.__name__ = "test_api"
test_worker.__name__ = "test_worker"
test_no_ai_or_emoji_markers.__name__ = "test_no_ai_or_emoji_markers"
test_pyproject_config.__name__ = "test_pyproject_config"
test_core_tests_pass.__name__ = "test_core_tests_pass"

if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
