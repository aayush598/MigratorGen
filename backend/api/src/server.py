"""MigratorGen REST API — FastAPI server backed by the SDK.

All business logic delegates to :class:`migrator_gen.MigrationClient`.
"""

from __future__ import annotations

import json
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from migrator_gen import (
    MigrationClient,
    Rule,
    SDKConfig,
)
from migrator_gen.exceptions import SDKError

# ── Application ──────────────────────────────────────────────────

VERSION = "0.1.0"
TITLE = "MigratorGen API"

app = FastAPI(
    title=TITLE,
    version=VERSION,
    description="Migration infrastructure API for library maintainers",
    docs_url="/docs",
    redoc_url="/redoc",
    servers=[{"url": "/", "description": "Default"}],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_client = MigrationClient(mode="local")


# ── Request / Response schemas ───────────────────────────────────


class MigrateCodeRequest(BaseModel):
    source_code: str = Field(..., description="Source code to migrate")
    rules: List[Dict[str, Any]] = Field(..., description="Migration rules")
    source_version: str = "1.0.0"
    target_version: str = "latest"
    dry_run: bool = False


class MigrateCodeResponse(BaseModel):
    original_code: str = ""
    transformed_code: str = ""
    changes: List[str] = []
    rules_applied: List[str] = []
    average_confidence: float = 0.0
    was_modified: bool = False
    errors: List[str] = []


class PreviewRequest(BaseModel):
    source_code: str
    rules: List[Dict[str, Any]]
    source_version: str = "1.0.0"
    target_version: str = "latest"


class ValidateRulesRequest(BaseModel):
    rules_path: str


class GenerateFromChangelogRequest(BaseModel):
    changelog_text: str
    library_name: str = "unknown"


class GenerateFromDiffRequest(BaseModel):
    old_code: str
    new_code: str
    module: str = ""


class ResolvePathRequest(BaseModel):
    source_version: str
    target_version: str
    library_name: str


class ResolvePathResponse(BaseModel):
    source_version: str
    target_version: str
    is_upgrade: bool = True
    steps: List[Dict[str, Any]] = []
    rule_count: int = 0


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


class SuggestRequest(BaseModel):
    file_path: str
    destination_library: str


class ParseChangelogRequest(BaseModel):
    file_path: str


# ── Helper ───────────────────────────────────────────────────────


def _parse_rules(rules_data: List[Dict[str, Any]]) -> List[Rule]:
    try:
        return [Rule.from_dict(r) for r in rules_data]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid rule format: {e}")


def _handle_sdk_error(exc: SDKError) -> None:
    raise HTTPException(status_code=500, detail=str(exc))


# ── Health ───────────────────────────────────────────────────────


@app.get("/health")
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version=VERSION,
        timestamp=datetime.utcnow().isoformat(),
    )


# ── Migrate ──────────────────────────────────────────────────────


@app.post("/api/v1/migrate", response_model=MigrateCodeResponse)
async def migrate_code(request: MigrateCodeRequest):
    try:
        rules = _parse_rules(request.rules)
        result = _client.migrate_code(
            request.source_code,
            rules,
            source_version=request.source_version,
            target_version=request.target_version,
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
        )
    except SDKError as e:
        _handle_sdk_error(e)


@app.post("/api/v1/migrate/file")
async def migrate_file(
    file: UploadFile = File(...),
    rules_json: str = Form(...),
    dry_run: bool = Form(False),
):
    rules_data = json.loads(rules_json)
    rules = _parse_rules(rules_data)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        result = _client.migrate_file(str(tmp_path), rules, dry_run=dry_run)
        return {
            "file_path": file.filename,
            "was_modified": result.was_modified,
            "changes": result.changes,
            "errors": result.errors,
        }
    except SDKError as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


# ── Preview ──────────────────────────────────────────────────────


@app.post("/api/v1/preview")
async def preview_migration(request: PreviewRequest):
    try:
        rules = _parse_rules(request.rules)
        preview = _client.preview_migration(request.source_code, rules)
        return {
            "original_code": preview.original_code,
            "transformed_code": preview.transformed_code,
            "diff": preview.diff,
            "changes": preview.changes,
            "change_count": preview.change_count,
            "average_confidence": preview.average_confidence,
        }
    except SDKError as e:
        _handle_sdk_error(e)


# ── Validate ─────────────────────────────────────────────────────


@app.post("/api/v1/validate")
async def validate_rules(request: ValidateRulesRequest):
    try:
        report = _client.validate_rules(request.rules_path)
        return {
            "valid": report.valid,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "info_count": report.info_count,
            "errors": [{"rule_id": e.rule_id, "message": e.message} for e in report.errors],
            "warnings": [{"rule_id": w.rule_id, "message": w.message} for w in report.warnings],
            "info": [{"rule_id": i.rule_id, "message": i.message} for i in report.info],
        }
    except SDKError as e:
        _handle_sdk_error(e)


# ── Generate rules ───────────────────────────────────────────────


@app.post("/api/v1/generate-rules/changelog")
async def generate_from_changelog(request: GenerateFromChangelogRequest):
    try:
        result = _client.generate_rules_from_changelog(
            request.changelog_text, request.library_name,
        )
        return {
            "version": result.version,
            "release_date": result.release_date,
            "rules": [r.to_dict() for r in result.rules],
            "rule_count": len(result.rules),
        }
    except SDKError as e:
        _handle_sdk_error(e)


@app.post("/api/v1/generate-rules/diff")
async def generate_from_diff(request: GenerateFromDiffRequest):
    try:
        rules = _client.generate_rules_from_diff(request.old_code, request.new_code, request.module)
        return {
            "rules": [r.to_dict() for r in rules],
            "rule_count": len(rules),
        }
    except SDKError as e:
        _handle_sdk_error(e)


# ── Suggest ──────────────────────────────────────────────────────


@app.post("/api/v1/suggest")
async def suggest_migrations(request: SuggestRequest):
    try:
        analysis = _client.suggest_migrations(
            request.file_path, request.destination_library,
        )
        return {
            "imports": [{"module": i.module, "name": i.name} for i in analysis.imports],
            "functions": [{"name": f.name, "params": f.params} for f in analysis.functions],
            "classes": [{"name": c.name, "methods": len(c.methods)} for c in analysis.classes],
            "suggested_migrations": analysis.suggested_migrations,
        }
    except SDKError as e:
        _handle_sdk_error(e)


# ── Resolve path ─────────────────────────────────────────────────


@app.post("/api/v1/resolve-path", response_model=ResolvePathResponse)
async def resolve_migration_path(request: ResolvePathRequest):
    try:
        path = _client.resolve_path(
            request.source_version, request.target_version, request.library_name,
        )
        return ResolvePathResponse(
            source_version=path.source_version,
            target_version=path.target_version,
            is_upgrade=path.is_upgrade,
            steps=[{"source": s.source, "target": s.target, "rules": len(s.rules)} for s in path.steps],
            rule_count=path.rule_count,
        )
    except SDKError as e:
        _handle_sdk_error(e)


# ── Libraries ────────────────────────────────────────────────────


@app.get("/api/v1/libraries")
async def list_libraries():
    libraries = _client.list_libraries()
    return {"libraries": libraries}


# ── Parse changelog ──────────────────────────────────────────────


@app.post("/api/v1/parse-changelog")
async def parse_changelog(request: ParseChangelogRequest):
    try:
        mf = _client.parse_changelog(request.file_path)
        return mf.model_dump(exclude_none=True)
    except SDKError as e:
        _handle_sdk_error(e)


# ── Generate migrator package ────────────────────────────────────


@app.post("/api/v1/generate-package")
async def generate_migrator_package(
    library: str = Body(...),
    output_dir: str = Body("."),
):
    try:
        out_path = _client.generate_migrator_package(library, output_dir)
        return {"path": out_path, "library": library}
    except SDKError as e:
        _handle_sdk_error(e)


# ── Dependency check ─────────────────────────────────────────────


@app.post("/api/v1/dependencies/check")
async def check_dependencies(requirements: List[str] = Body(...)):
    known = set(_client.list_libraries().keys())
    results = []
    for req in requirements:
        parts = re.split(r"[<>=!]+", req)
        pkg = parts[0].strip()
        results.append({
            "package": pkg,
            "migration_available": pkg in known,
        })
    return {
        "dependencies": results,
        "total_checked": len(results),
        "migration_ready_count": sum(1 for r in results if r["migration_available"]),
    }


# ── Main ─────────────────────────────────────────────────────────


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
