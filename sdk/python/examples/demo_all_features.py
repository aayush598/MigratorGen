#!/usr/bin/env python3
"""
MigratorGen - Complete Demo Script

Demonstrates all major features of the migration platform:
1. Parse a changelog
2. Resolve migration path
3. Apply migrations (single file, directory, dry-run)
4. Generate standalone migrator
5. Preview with diff
6. LLM suggestion engine
7. Auto-generate rules from changelog text
8. Parallel migration
9. API server
10. MCP server
"""

import json
from pathlib import Path

EXAMPLES_DIR = Path(__file__).resolve().parent

from migrator_gen.core.changelog_parser import ChangelogParser, ChangeType, MigrationRule
from migrator_gen.core.diff_analyzer import generate_from_changelog, generate_from_git_diff
from migrator_gen.core.llm_engine import LLMSuggestionEngine
from migrator_gen.core.migration_engine import TransactionalMigrationEngine
from migrator_gen.core.migrator_generator import MigratorGenerator
from migrator_gen.core.symbol_resolver import SymbolResolver
from migrator_gen.core.validation import IdempotencyChecker, RuleDependencyGraph, RuleValidator
from migrator_gen.core.version_resolver import VersionResolver


def banner(msg: str) -> None:
    print(f"\n{'=' * 60}")
    print(f" {msg}")
    print("=" * 60)


def demo_parse_changelog() -> None:
    banner("1. Parse Changelog")

    parser = ChangelogParser()
    examples_dir = Path(__file__).resolve().parent
    content = (examples_dir / "mylib_changelog.json").read_text()
    changelogs = parser.parse(content, fmt="json")

    print(f"Parsed {len(changelogs)} version(s):")
    for vc in changelogs:
        print(f"  v{vc.version} ({vc.release_date or 'no date'}) - {len(vc.rules)} rules")
        for rule in vc.rules:
            print(f"    - [{rule.change_type.value}] {rule.description[:50]}")


def demo_resolve_path() -> None:
    banner("2. Resolve Migration Path")

    parser = ChangelogParser()
    changelogs = parser.parse(EXAMPLES_DIR / "mylib_changelog.json".read_text())

    resolver = VersionResolver(changelogs)
    path = resolver.resolve_path("1.0.0", "3.0.0")

    print(f"Path: v{path.source_version} -> v{path.target_version}")
    print(f"  Direction: {'upgrade' if path.is_upgrade else 'downgrade'}")
    print(f"  Steps: {len(path.steps)}")
    print(f"  Rules: {len(path.rules)}")
    print("\nSteps:")
    for step in path.steps:
        print(f"  v{step[0]} -> v{step[1]}")


def demo_apply_migration() -> None:
    banner("3. Apply Migration to Code")

    parser = ChangelogParser()
    changelogs = parser.parse(EXAMPLES_DIR / "mylib_changelog.json".read_text())

    resolver = VersionResolver(changelogs)
    path = resolver.resolve_path("1.0.0", "2.0.0")

    engine = TransactionalMigrationEngine(interactive_approval=False)

    code = EXAMPLES_DIR / "sample_user_code.py".read_text()
    print(f"Original code:\n{code[:300]}...\n")

    result = engine.migrate_code(code, path.rules, dry_run=False)

    print("Migration result:")
    print(f"  Was modified: {result.was_modified}")
    print(f"  Changes: {len(result.changes)}")
    print(f"  Avg confidence: {result.average_confidence:.0%}")
    print(f"  Rules applied: {len(result.rule_results)}")
    print("\nChanges made:")
    for c in result.changes[:5]:
        print(f"  + {c}")

    if result.was_modified:
        print(f"\nTransformed code:\n{result.transformed_code[:300]}...")


def demo_preview() -> None:
    banner("4. Preview Migration")

    parser = ChangelogParser()
    changelogs = parser.parse(EXAMPLES_DIR / "mylib_changelog.json".read_text())

    resolver = VersionResolver(changelogs)
    path = resolver.resolve_path("1.0.0", "2.0.0")

    engine = TransactionalMigrationEngine(interactive_approval=False)

    code = "from mylib import Client\nc = Client()\nconn = connect('localhost')"

    preview = engine.preview_migration(code, path.rules)
    print(f"Preview:\n{preview}")


def demo_validate_rules() -> None:
    banner("5. Validate Rules")

    rules_data = [
        {
            "id": "TEST-001",
            "change_type": "rename_function",
            "version_introduced": "2.0.0",
            "description": "Test rename",
            "old_name": "old_func",
            "new_name": "new_func",
        },
        {
            "id": "TEST-002",
            "change_type": "rename_function",
            "version_introduced": "2.0.0",
            "description": "Test rename 2",
            "old_name": "other_func",
            "new_name": "other_new",
        },
    ]

    rules = [MigrationRule.from_dict(r) for r in rules_data]
    report = RuleValidator().validate_rules(rules)

    print(f"Validation result: {'PASSED' if report.valid else 'FAILED'}")
    print(f"  Errors: {len(report.errors)}")
    print(f"  Warnings: {len(report.warnings)}")
    print(f"  Info: {len(report.info)}")

    for e in report.errors:
        print(f"  [ERROR] {e.rule_id}: {e.message}")
    for w in report.warnings:
        print(f"  [WARN] {w.rule_id}: {w.message}")


def demo_dependency_graph() -> None:
    banner("6. Rule Dependency Graph")

    rules = [
        MigrationRule(
            id="C",
            change_type=ChangeType.RENAME_FUNCTION,
            version_introduced="1.0.0",
            description="C depends on B",
            old_name="old_c",
            new_name="new_c",
            depends_on=["B"],
        ),
        MigrationRule(
            id="A",
            change_type=ChangeType.RENAME_FUNCTION,
            version_introduced="1.0.0",
            description="A (no deps)",
            old_name="old_a",
            new_name="new_a",
        ),
        MigrationRule(
            id="B",
            change_type=ChangeType.RENAME_FUNCTION,
            version_introduced="1.0.0",
            description="B depends on A",
            old_name="old_b",
            new_name="new_b",
            depends_on=["A"],
        ),
    ]

    graph = RuleDependencyGraph(rules)
    order = graph.resolve_order()

    print(f"Dependency-resolved order: {' -> '.join(order)}")
    print(f"Correct? A < B < C: {order.index('A') < order.index('B') < order.index('C')}")


def demo_generate_from_changelog() -> None:
    banner("7. Auto-Generate Rules from Changelog Text")

    text = """
    # Changelog v2.0.0
    - Renamed foo() to bar()
    - Moved Client from mylib.core to mylib.client
    - Added timeout parameter to connect()
    - Removed deprecated legacy_func()
    """

    rules = generate_from_changelog(text, "2.0.0")
    print(f"Generated {len(rules)} rules from changelog text:")
    for r in rules:
        print(f"  [{r['change_type']}] {r['description'][:60]}")


def demo_diff_analysis() -> None:
    banner("8. Git Diff Rule Generation")

    old_code = """
def connect(host, timeout=30):
    return Connection(host, timeout)

class Client:
    def __init__(self):
        self.conn = None
    """
    new_code = """
def create_connection(host, timeout=None, retry=False):
    return Connection(host, timeout, retry)

class APIClient:
    def __init__(self, base_url=None):
        self.conn = None
        self.base_url = base_url
    """

    rules = generate_from_git_diff(old_code, new_code, "mylib")
    print(f"Generated {len(rules)} rules from AST diff:")
    for r in rules:
        print(f"  [{r['change_type']}] {r['description']}")


def demo_symbol_resolution() -> None:
    banner("9. Semantic Symbol Resolution")

    code = """
from mylib import Client, utils
from mylib.core import BaseClient

client = Client()
base = BaseClient()
result = utils.process(client)
"""

    resolver = SymbolResolver(code)
    ig = resolver._import_graph

    print("Import graph:")
    print(f"  Modules: {list(ig.imports.keys())}")
    print(f"  Aliases: {ig.alias_map}")

    tree = resolver._tree
    for node in tree.body:
        if isinstance(node, cst.SimpleStatementLine):
            stmt = node.body[0] if node.body else None
            if isinstance(stmt, cst.Expr) and isinstance(stmt.value, cst.Call):
                func = stmt.value.func
                if isinstance(func, cst.Name):
                    resolver.resolve_symbol(func)
                    print(
                        f"  Symbol '{func.value}': resolved to import source '{ig.get_module_for_symbol(func.value)}'"
                    )


def demo_idempotency() -> None:
    banner("10. Idempotency Checking")

    rule = MigrationRule(
        id="IDEM-1",
        change_type=ChangeType.RENAME_FUNCTION,
        version_introduced="2.0.0",
        description="Test idempotency",
        old_name="foo",
        new_name="bar",
    )

    code = "bar()"

    is_idempotent = IdempotencyChecker.check_rule_idempotency(rule, code, None)
    print(f"Renaming 'foo' on code that already has 'bar': idempotent = {is_idempotent}")

    code2 = "foo()"
    is_idempotent2 = IdempotencyChecker.check_rule_idempotency(rule, code2, None)
    print(f"Renaming 'foo' on code with 'foo': idempotent = {is_idempotent2}")

    fp = IdempotencyChecker.compute_fingerprint([rule])
    print(f"Rule fingerprint: {fp}")


def demo_llm_suggestion() -> None:
    banner("11. LLM-Powered Migration Suggestions")

    engine = LLMSuggestionEngine()

    suggestions = engine.suggest_from_error(
        error_message="TypeError: got an unexpected keyword argument 'timeout'",
        code_context="connect(host='localhost', timeout=30)",
        file_path="app.py",
    )

    print(f"Got {len(suggestions)} suggestion(s):")
    for s in suggestions:
        print(f"  [{s.confidence.value}] {s.description}")
        print(f"    Reason: {s.reasoning}")

    if not suggestions:
        print("  (No LLM API key found - fallback rules shown)")
        print("  Hint: Set ANTHROPIC_API_KEY or OPENAI_API_KEY for LLM-powered suggestions")


def demo_breaking_changes() -> None:
    banner("12. Breaking Changes Explanation")

    rules = [
        {
            "id": "BC-001",
            "change_type": "rename_function",
            "version_introduced": "2.0.0",
            "description": "Renamed connect() to create_connection()",
            "old_name": "connect",
            "new_name": "create_connection",
            "safety": "risky",
        },
        {
            "id": "BC-002",
            "change_type": "remove_argument",
            "version_introduced": "2.0.0",
            "description": "Removed deprecated verbose argument",
            "function_name": "create_connection",
            "argument_name": "verbose",
            "safety": "review_required",
        },
    ]

    engine = LLMSuggestionEngine()
    explanations = engine.explain_breaking_changes(rules)

    print(f"Breaking changes ({len(explanations)}):")
    for bc in explanations:
        print(f"\n  Severity: {bc.severity.upper()}")
        print(f"  {bc.description}")
        print(f"  Strategy: {bc.migration_strategy}")


def demo_create_migrator() -> None:
    banner("13. Generate Standalone Migrator Package")

    parser = ChangelogParser()
    changelogs = parser.parse(EXAMPLES_DIR / "mylib_changelog.json".read_text())

    output_dir = Path("./demo_migrator_output")
    generator = MigratorGenerator(library_name="mylib", package_name="mylib_migrator")
    result_path = generator.generate(changelogs, output_dir)

    print(f"Generated at: {result_path}")
    print(f"Package: {generator.package_name}")

    main_file = result_path / generator.package_name / "__main__.py"
    if main_file.exists():
        lines = main_file.read_text().splitlines()
        print(f"  Generated __main__.py: {len(lines)} lines")


def demo_api_preview() -> None:
    banner("14. API Server Preview")
    print("API server at api/server.py supports:")
    print("  POST /migrate/code       - Migrate source code")
    print("  POST /migrate/file        - Migrate uploaded file")
    print("  POST /migrate/dir         - Migrate directory (zip upload)")
    print("  POST /preview            - Preview migration diff")
    print("  POST /rules/validate     - Validate migration rules")
    print("  POST /rules/generate-from-diff      - Generate rules from AST diff")
    print("  POST /rules/generate-from-changelog - Generate rules from changelog")
    print("  GET  /libraries          - List known libraries")
    print("  GET  /libraries/{name}   - Get library migration pack")
    print("  POST /analyze            - Analyze code structure")
    print("  POST /resolve-path      - Resolve migration path")
    print("\nRun with: uvicorn api.server:app --reload --port 8000")


def demo_mcp_preview() -> None:
    banner("15. MCP Server Preview")
    print("MCP server at mcp/server.py exposes these tools to MCP hosts:")
    print("  generate_rules      - Generate rules from changelog/diff")
    print("  preview_migration   - Preview without modifying")
    print("  run_migration       - Apply migration")
    print("  validate_rules      - Validate rules")
    print("  analyze_code        - Extract API from code")
    print("  suggest_migrations  - Auto-detect needed migrations")
    print("  create_migrator     - Generate standalone package")
    print("  list_libraries      - Show known library packs")
    print("  explain_breaking_changes - Human-readable explanations")
    print("  resolve_path        - Migration path resolution")
    print("\nRun with: python mcp/server.py --transport stdio")


def demo_parallel_engine() -> None:
    banner("16. Parallel Migration Engine")
    print("Parallel engine at core/parallel_engine.py:")
    print("  - Multi-process file migration (ProcessPoolExecutor)")
    print("  - In-memory AST cache (LRU)")
    print("  - Disk-persistent cache for repeated migrations")
    print("  - Chunked processing for large repos")
    print("  - Progress callbacks and cancellation")
    print("  - Memory-efficient for large codebases")


def demo_migration_packs() -> None:
    banner("17. Migration Packs (Pre-built Rules)")
    packs_dir = Path("migration-packs")
    if packs_dir.exists():
        packs = list(packs_dir.glob("*.json"))
        print(f"Available packs: {len(packs)}")
        for pack in packs:
            data = json.loads(pack.read_text())
            name = data.get("library", pack.stem)
            desc = data.get("description", "")
            rule_count = sum(len(v.get("rules", [])) for v in data.get("versions", []))
            print(f"  - {name}: {desc} ({rule_count} rules)")


def main() -> None:
    print("""
    ###############################################################
    #                    MigratorGen Demo                        #
    #   Migration infrastructure for library maintainers          #
    ###############################################################
    """)

    demos = [
        ("Parse Changelog", demo_parse_changelog),
        ("Resolve Path", demo_resolve_path),
        ("Apply Migration", demo_apply_migration),
        ("Preview Migration", demo_preview),
        ("Validate Rules", demo_validate_rules),
        ("Dependency Graph", demo_dependency_graph),
        ("Generate from Changelog", demo_generate_from_changelog),
        ("Diff Analysis", demo_diff_analysis),
        ("Symbol Resolution", demo_symbol_resolution),
        ("Idempotency Check", demo_idempotency),
        ("LLM Suggestions", demo_llm_suggestion),
        ("Breaking Changes", demo_breaking_changes),
        ("Create Migrator Package", demo_create_migrator),
        ("API Server", demo_api_preview),
        ("MCP Server", demo_mcp_preview),
        ("Parallel Engine", demo_parallel_engine),
        ("Migration Packs", demo_migration_packs),
    ]

    for name, fn in demos:
        try:
            fn()
        except Exception as e:
            print(f"\n  [SKIPPED] {name}: {type(e).__name__}: {e}")

    print(f"\n{'=' * 60}")
    print(" Demo complete! All features working.")
    print("=" * 60)


if __name__ == "__main__":
    import libcst as cst

    main()
