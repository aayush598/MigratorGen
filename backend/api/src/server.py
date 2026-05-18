"""
MigratorGen REST API Server - FastAPI-based HTTP API for programmatic migration access.

Endpoints:
- POST /migrate/code     - Migrate source code
- POST /migrate/file    - Migrate a file
- POST /migrate/dir     - Migrate a directory
- GET  /rules           - List rules for a library
- POST /rules/validate  - Validate rules
- POST /rules/generate   - Generate rules from git diff
- POST /rules/from-changelog - Convert changelog text to rules


- GET  /registry/libraries - List available migration packs
- GET  /registry/{lib}/rules - Get rules for a library
- POST /preview            - Preview migration diff
- GET  /health             - Health check
- POST /analyze            - Analyze code for potential migration needs
"""

import sys
import os
import json
import tempfile
import shutil
import re
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(ROOT_PATH))

import libcst as cst
from core.changelog_parser import ChangelogParser, MigrationRule, ChangeType, VersionChangelog, MigrationFile
from core.migration_engine import TransactionalMigrationEngine
from core.validation import RuleValidator, IdempotencyChecker
from core.diff_analyzer import GitDiffAnalyzer, ChangelogToRulesConverter, generate_from_git_diff, generate_from_changelog
from core.version_resolver import VersionResolver
from core.symbol_resolver import SymbolResolver

from typing import Optional, List, Dict, Any, Literal, Tuple
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl

app_title = "MigratorGen API"
app_version = "0.1.0"

app = FastAPI(
    title=app_title,
    version=app_version,
    description="AI-native migration infrastructure API for library maintainers",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": app_version,
        "timestamp": datetime.now().isoformat(),
    }


class MigrateCodeRequest(BaseModel):
    source_code: str = Field(..., description="Source code to migrate")
    rules: List[Dict[str, Any]] = Field(..., description="Migration rules")
    source_version: str = Field(..., description="Source version")
    target_version: str = Field(default="latest", description="Target version")
    dry_run: bool = Field(default=False, description="Dry run mode")
    interactive_approval: bool = Field(default=False, description="Require approval for risky transforms")
    transactional: bool = Field(default=True, description="Enable transactional mode")


class MigrateCodeResponse(BaseModel):
    original_code: str
    transformed_code: str
    changes: List[str]
    rules_applied: List[str]
    average_confidence: float
    was_modified: bool
    errors: List[str] = []
    rule_results: List[Dict[str, Any]] = []


@app.post("/migrate/code", response_model=MigrateCodeResponse)
async def migrate_code(request: MigrateCodeRequest):
    """Migrate source code using provided rules."""
    try:
        rules = [MigrationRule.from_dict(r) for r in request.rules]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid rule format: {e}")

    engine = TransactionalMigrationEngine(
        transactional=request.transactional,
        interactive_approval=request.interactive_approval,
    )

    result = engine.migrate_code(
        request.source_code,
        rules,
        dry_run=request.dry_run,
    )

    return MigrateCodeResponse(
        original_code=result.original_code,
        transformed_code=result.transformed_code,
        changes=result.changes,
        rules_applied=result.rules_applied,
        average_confidence=result.average_confidence,
        was_modified=result.was_modified,
        errors=result.errors,
        rule_results=[
            {
                "rule_id": r.rule_id,
                "rule_description": r.rule_description,
                "success": r.success,
                "confidence": r.confidence,
                "safety": r.safety.value if hasattr(r.safety, 'value') else str(r.safety),
                "changes_made": r.changes_made,
                "errors": r.errors,
                "skipped_reason": r.skipped_reason,
            }
            for r in result.rule_results
        ],
    )


class MigrateFileRequest(BaseModel):
    rules: List[Dict[str, Any]] = Field(..., description="Migration rules")
    source_version: str = Field(..., description="Source version")
    target_version: str = Field(default="latest", description="Target version")
    dry_run: bool = Field(default=False)
    backup: bool = Field(default=True)
    interactive_approval: bool = Field(default=False)


class MigrateFileResponse(BaseModel):
    file_path: str
    was_modified: bool
    changes: List[str]
    errors: List[str] = []


@app.post("/migrate/file", response_model=MigrateFileResponse)
async def migrate_file(
    file: UploadFile = File(...),
    rules_json: str = Form(..., description="JSON array of migration rules"),
    source_version: str = Form(...),
    target_version: str = Form(default="latest"),
    dry_run: bool = Form(default=False),
    backup: bool = Form(default=True),
    interactive_approval: bool = Form(default=False),
):
    """Migrate an uploaded file."""
    try:
        rules_data = json.loads(rules_json)
        rules = [MigrationRule.from_dict(r) for r in rules_data]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid rules: {e}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        engine = TransactionalMigrationEngine(interactive_approval=interactive_approval)
        result = engine.migrate_file(
            tmp_path,
            rules,
            dry_run=dry_run,
            backup=backup,
        )
        return MigrateFileResponse(
            file_path=file.filename,
            was_modified=result.was_modified,
            changes=result.changes,
            errors=result.errors,
        )
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


class MigrateDirRequest(BaseModel):
    rules: List[Dict[str, Any]]
    source_version: str
    target_version: str = "latest"
    dry_run: bool = False
    backup: bool = True
    exclude_patterns: List[str] = Field(
        default=["**/test_*.py", "**/__pycache__/**", "**/.venv/**", "**/venv/**", "**/node_modules/**"],
        description="Patterns to exclude",
    )
    interactive_approval: bool = False


class MigrateDirResponse(BaseModel):
    source_version: str
    target_version: str
    is_upgrade: bool
    files_processed: int
    files_modified: int
    files_failed: int
    files_skipped: int
    total_changes: int
    average_confidence: float
    transactions_rolled_back: int
    change_records: List[Dict[str, Any]] = []


@app.post("/migrate/dir", response_model=MigrateDirResponse)
async def migrate_directory(
    directory: UploadFile = File(...),
    rules_json: str = Form(...),
    source_version: str = Form(...),
    target_version: str = Form(default="latest"),
    dry_run: bool = Form(default=False),
    backup: bool = Form(default=True),
    interactive_approval: bool = Form(default=False),
    exclude_patterns: str = Form(default="**/test_*.py,**/__pycache__/**"),
):
    """Migrate all files in an uploaded directory as a zip."""
    import zipfile
    import io

    try:
        rules_data = json.loads(rules_json)
        rules = [MigrationRule.from_dict(r) for r in rules_data]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid rules: {e}")

    exclude_list = [p.strip() for p in exclude_patterns.split(",")]

    zip_bytes = await directory.read()
    zip_buffer = io.BytesIO(zip_bytes)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            zf.extractall(tmp_path)

        from core.version_resolver import MigrationPath
        path = MigrationPath(
            source_version=source_version,
            target_version=target_version,
            steps=[],
            rules=rules,
            is_upgrade=True,
        )

        engine = TransactionalMigrationEngine(interactive_approval=interactive_approval)
        report = engine.migrate_directory(
            tmp_path,
            path,
            dry_run=dry_run,
            backup=backup,
            exclude_patterns=exclude_list,
        )

        avg_conf = round(report.total_confidence / report.files_modified, 3) if report.files_modified > 0 else 0.0

        return MigrateDirResponse(
            source_version=report.source_version,
            target_version=report.target_version,
            is_upgrade=report.is_upgrade,
            files_processed=report.files_processed,
            files_modified=report.files_modified,
            files_failed=report.files_failed,
            files_skipped=report.files_skipped,
            total_changes=report.total_changes,
            average_confidence=avg_conf,
            transactions_rolled_back=report.transactions_rolled_back,
            change_records=[
                {
                    "rule_id": cr.rule_id,
                    "change_type": cr.change_type,
                    "file_path": cr.file_path,
                    "confidence": cr.confidence,
                }
                for cr in report.change_records
            ],
        )


class PreviewRequest(BaseModel):
    source_code: str
    rules: List[Dict[str, Any]]
    source_version: str
    target_version: str = "latest"


class PreviewResponse(BaseModel):
    original_code: str
    transformed_code: str
    diff: str
    changes: List[str]
    average_confidence: float
    rule_results: List[Dict[str, Any]]


@app.post("/preview", response_model=PreviewResponse)
async def preview_migration(request: PreviewRequest):
    """Preview what a migration would do."""
    try:
        rules = [MigrationRule.from_dict(r) for r in request.rules]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid rules: {e}")

    engine = TransactionalMigrationEngine(interactive_approval=False)
    preview = engine.preview_migration(request.source_code, rules)

    result = engine.migrate_code(request.source_code, rules, dry_run=False)

    return PreviewResponse(
        original_code=result.original_code,
        transformed_code=result.transformed_code,
        diff=preview,
        changes=result.changes,
        average_confidence=result.average_confidence,
        rule_results=[
            {
                "rule_id": r.rule_id,
                "confidence": r.confidence,
                "safety": r.safety.value if hasattr(r.safety, 'value') else str(r.safety),
                "success": r.success,
                "changes_made": r.changes_made,
            }
            for r in result.rule_results
        ],
    )


class ValidateRulesRequest(BaseModel):
    rules: List[Dict[str, Any]]


class ValidateRulesResponse(BaseModel):
    valid: bool
    error_count: int
    warning_count: int
    info_count: int
    errors: List[Dict[str, str]]
    warnings: List[Dict[str, str]]
    info: List[Dict[str, str]]


@app.post("/rules/validate", response_model=ValidateRulesResponse)
async def validate_rules(request: ValidateRulesRequest):
    """Validate migration rules."""
    try:
        rules = [MigrationRule.from_dict(r) for r in request.rules]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid rule format: {e}")

    report = RuleValidator().validate_rules(rules)

    return ValidateRulesResponse(
        valid=report.valid,
        error_count=len(report.errors),
        warning_count=len(report.warnings),
        info_count=len(report.info),
        errors=[{"rule_id": e.rule_id, "message": e.message, "field": e.field} for e in report.errors],
        warnings=[{"rule_id": w.rule_id, "message": w.message} for w in report.warnings],
        info=[{"rule_id": i.rule_id, "message": i.message} for i in report.info],
    )


class GenerateFromDiffRequest(BaseModel):
    old_code: str = Field(..., description="Old version source code")
    new_code: str = Field(..., description="New version source code")
    module: str = Field(default="", description="Module name for context")


class GenerateFromChangelogRequest(BaseModel):
    changelog_text: str = Field(..., description="Changelog markdown text")
    version: str = Field(default="X.Y.Z", description="Version introduced")


class GenerateRulesResponse(BaseModel):
    rules: List[Dict[str, Any]]
    rule_count: int


@app.post("/rules/generate-from-diff", response_model=GenerateRulesResponse)
async def generate_rules_from_diff(request: GenerateFromDiffRequest):
    """Generate migration rules by analyzing AST diff between two code versions."""
    rules = generate_from_git_diff(request.old_code, request.new_code, request.module)
    return GenerateRulesResponse(rules=rules, rule_count=len(rules))


@app.post("/rules/generate-from-changelog", response_model=GenerateRulesResponse)
async def generate_rules_from_changelog(request: GenerateFromChangelogRequest):
    """Convert changelog markdown text into migration rules."""
    rules = generate_from_changelog(request.changelog_text, request.version)
    return GenerateRulesResponse(rules=rules, rule_count=len(rules))


class AnalyzeCodeRequest(BaseModel):
    source_code: str
    detect_outdated_patterns: bool = True


class AnalyzedSymbol(BaseModel):
    name: str
    kind: str
    qualifiers: List[str] = []
    import_source: Optional[str] = None
    line: int = 0


class AnalyzeCodeResponse(BaseModel):
    imports: List[Dict[str, str]]
    functions: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    analyzed_symbols: List[AnalyzedSymbol] = []


@app.post("/analyze", response_model=AnalyzeCodeResponse)
async def analyze_code(request: AnalyzeCodeRequest):
    """Analyze source code and extract API information."""
    resolver = SymbolResolver(request.source_code)
    tree = resolver._tree

    imports = []
    functions = []
    classes = []

    for node in tree.body:
        if isinstance(node, cst.SimpleStatementLine):
            stmt = node.body[0] if node.body else None
            if isinstance(stmt, cst.ImportFrom):
                module = ""
                if stmt.module:
                    if isinstance(stmt.module, cst.Name):
                        module = stmt.module.value
                    elif isinstance(stmt.module, cst.Attribute):
                        module = resolver._dotted_name_from_node(stmt.module)
                if isinstance(stmt.names, cst.ImportStar):
                    imports.append({"module": module, "name": "*"})
                else:
                    for alias in stmt.names:
                        name = alias.name.value if isinstance(alias.name, cst.Name) else ""
                        imports.append({"module": module, "name": name})
        elif isinstance(node, cst.FunctionDef):
            functions.append({
                "name": node.name.value,
                "line": node.name.line,
                "params": [p.name.value for p in node.params.params],
                "decorators": [d.decorator.value if isinstance(d.decorator, cst.Name) else "" for d in node.decorators],
            })
        elif isinstance(node, cst.ClassDef):
            classes.append({
                "name": node.name.value,
                "line": node.name.line,
            })

    return AnalyzeCodeResponse(
        imports=imports,
        functions=functions,
        classes=classes,
        analyzed_symbols=[],
    )


class ResolvePathRequest(BaseModel):
    changelog_json: Dict[str, Any]
    source_version: str
    target_version: str


class ResolvePathResponse(BaseModel):
    source_version: str
    target_version: str
    is_upgrade: bool
    steps: List[Tuple[str, str]]
    rule_count: int
    rules: List[Dict[str, Any]]


@app.post("/resolve-path", response_model=ResolvePathResponse)
async def resolve_migration_path(request: ResolvePathRequest):
    """Resolve migration path between versions."""
    try:
        mf = MigrationFile(**request.changelog_json)
        changelogs = mf.versions
    except Exception:
        changelogs = []
        for item in request.changelog_json.get("versions", request.changelog_json if isinstance(request.changelog_json, list) else []):
            changelogs.append(VersionChangelog(**item))

    resolver = VersionResolver(changelogs)
    path = resolver.resolve_path(request.source_version, request.target_version)

    return ResolvePathResponse(
        source_version=path.source_version,
        target_version=path.target_version,
        is_upgrade=path.is_upgrade,
        steps=path.steps,
        rule_count=len(path.rules),
        rules=[r.to_dict() for r in path.rules],
    )


class ExportRulesRequest(BaseModel):
    rules: List[Dict[str, Any]]
    library: str
    version: str = "X.Y.Z"
    release_date: Optional[str] = None


class ExportRulesResponse(BaseModel):
    rules_json: str = Field(..., alias="json")
    rules_count: int

    model_config = {"populate_by_name": True}


@app.post("/rules/export", response_model=ExportRulesResponse)
async def export_rules_json(request: ExportRulesRequest):
    """Export rules as a structured JSON migration file."""
    data = {
        "library": request.library,
        "schema_version": "1.0",
        "versions": [
            {
                "version": request.version,
                "release_date": request.release_date or "",
                "rules": request.rules,
            }
        ],
    }
    return ExportRulesResponse(
        rules_json=json.dumps(data, indent=2),
        rules_count=len(request.rules),
    )


class GenerateMigratorRequest(BaseModel):
    rules: List[Dict[str, Any]]
    library: str
    package_name: Optional[str] = None
    output_dir: str = "./generated_migrator"


class GenerateMigratorResponse(BaseModel):
    output_dir: str
    package_name: str
    rule_count: int
    files_created: List[str]


@app.post("/migrator/generate", response_model=GenerateMigratorResponse)
async def generate_migrator_package(request: GenerateMigratorRequest):
    """Generate a standalone migrator package from rules."""
    try:
        changelogs = []
        rules_by_version: Dict[str, List] = {}
        for r in request.rules:
            v = r.get("version_introduced", "X.Y.Z")
            if v not in rules_by_version:
                rules_by_version[v] = []
            rules_by_version[v].append(MigrationRule.from_dict(r))

        for v, rules in rules_by_version.items():
            changelogs.append(VersionChangelog(version=v, rules=rules))

        generator = MigratorGenerator(
            library_name=request.library,
            package_name=request.package_name,
        )
        output_path = Path(request.output_dir)
        generator.generate(changelogs, output_path)

        files_created = [str(f) for f in output_path.rglob("*") if f.is_file()]

        return GenerateMigratorResponse(
            output_dir=str(output_path),
            package_name=generator.package_name,
            rule_count=len(request.rules),
            files_created=files_created,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate migrator: {e}")


@app.get("/libraries")
async def list_libraries():
    """List known libraries with migration packs."""
    return {
        "libraries": [
            {"name": "pydantic", "description": "Pydantic V1 to V2 migration"},
            {"name": "fastapi", "description": "FastAPI version migrations"},
            {"name": "httpx", "description": "HTTPX version migrations"},
            {"name": "sqlalchemy", "description": "SQLAlchemy version migrations"},
            {"name": "django", "description": "Django version migrations"},
            {"name": "attrs", "description": "Attrs to dataclasses migrations"},
        ]
    }


@app.get("/libraries/{library}")
async def get_library_info(library: str):
    """Get information about a specific library migration pack."""
    registry_dir = ROOT_PATH / "migration-packs"
    pack_file = registry_dir / f"{library}.json"

    if pack_file.exists():
        content = json.loads(pack_file.read_text())
        return content

    return {
        "name": library,
        "status": "not_found",
        "message": f"No migration pack found for '{library}'",
        "suggestion": "Use /rules/generate-from-diff to create rules from your own diff",
    }


class DependencyCheckRequest(BaseModel):
    requirements: List[str] = Field(..., description="List of 'package>=version' strings")


class OutdatedDependency(BaseModel):
    package: str
    current: str
    latest: str
    migration_available: bool
    migration_pack: Optional[str] = None


class DependencyCheckResponse(BaseModel):
    dependencies: List[OutdatedDependency]
    total_checked: int
    outdated_count: int
    migration_ready_count: int


@app.post("/dependencies/check", response_model=DependencyCheckResponse)
async def check_dependencies(request: DependencyCheckRequest):
    """Check dependencies for available migrations."""
    registry_dir = ROOT_PATH / "migration-packs"
    known_packages = {f.stem for f in registry_dir.glob("*.json")}

    results = []
    for req in request.requirements:
        parts = re.split(r"[<>=!]+", req)
        pkg = parts[0].strip()
        current = parts[-1].strip() if len(parts) > 1 else "unknown"

        results.append(OutdatedDependency(
            package=pkg,
            current=current,
            latest="unknown",
            migration_available=pkg in known_packages,
            migration_pack=pkg if pkg in known_packages else None,
        ))

    outdated = [r for r in results if r.migration_available]
    return DependencyCheckResponse(
        dependencies=results,
        total_checked=len(results),
        outdated_count=len(outdated),
        migration_ready_count=len([r for r in results if r.migration_available]),
    )


if __name__ == "__main__":
    import uvicorn
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    uvicorn.run(app, host="0.0.0.0", port=8000)