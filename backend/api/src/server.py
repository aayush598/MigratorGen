"""MigratorGen REST API — FastAPI server backed by the SDK.

Uses shared middleware for auth, logging, metrics, error handling.
All business logic delegates to :class:`migrator_gen.MigrationClient`.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import uuid
from typing import Any, Dict, List, Optional

from fastapi import Body, Depends, FastAPI, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel, Field

from migrator_gen import (
    SyncMigrationClient,
    Rule,
    SDKConfig,
)
from migrator_gen.exceptions import SDKError

from shared.middleware import setup_middlewares, create_rate_limiter
from shared.metrics import setup_metrics, MetricsCollector
from shared.logging import setup_logging
from shared.exceptions import global_exception_handler, MigratorBaseException
from shared.auth import (
    generate_api_key,
    verify_api_key,
    Role,
)

VERSION = "0.2.0"
TITLE = "MigratorGen API"

app = FastAPI(
    title=TITLE,
    version=VERSION,
    description="Migration infrastructure API for library maintainers",
    docs_url="/docs",
    redoc_url="/redoc",
    servers=[{"url": "/", "description": "Default"}],
)

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")
SERVICE_KEY = os.environ.get("SERVICE_KEY", "dev-service-key-change-in-production")

setup_middlewares(
    app,
    cors_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    jwt_secret=JWT_SECRET,
    service_key=SERVICE_KEY,
    timeout_seconds=120.0,
)
setup_metrics(app)

_limiter = create_rate_limiter(default_limit="100/minute")

_client = SyncMigrationClient(mode="local")
_metrics = MetricsCollector(service_name="api")


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


# ── Auth schemas (API keys only — user auth handled by better-auth) ──


class APIKeyCreateRequest(BaseModel):
    name: str
    scopes: List[str] = Field(default_factory=lambda: ["migrate", "read"])


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: Optional[str] = None
    key_prefix: str
    scopes: List[str]
    created_at: str
    is_active: bool


# ── In-memory stores (replace with DB in production) ─────────────


_api_keys: Dict[str, Dict[str, Any]] = {}


# ── Helpers ───────────────────────────────────────────────────────


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
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ── API Key endpoints ────────────────────────────────────────────


@app.post("/api/v1/keys", response_model=APIKeyResponse)
async def create_api_key(request: APIKeyCreateRequest, req: Request):
    tenant_id = getattr(req.state, "tenant_id", None)
    user_id = getattr(req.state, "user_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    raw_key, key_hash = generate_api_key()
    key_id = f"key_{len(_api_keys) + 1}"
    _api_keys[key_id] = {
        "id": key_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "name": request.name,
        "key_hash": key_hash,
        "key_prefix": raw_key[:12],
        "scopes": request.scopes,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return APIKeyResponse(
        id=key_id,
        name=request.name,
        key=raw_key,
        key_prefix=raw_key[:12],
        scopes=request.scopes,
        created_at=datetime.now(timezone.utc).isoformat(),
        is_active=True,
    )


@app.get("/api/v1/keys", response_model=List[APIKeyResponse])
async def list_api_keys(req: Request):
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    keys = [
        APIKeyResponse(
            id=k["id"],
            name=k["name"],
            key_prefix=k["key_prefix"],
            scopes=k["scopes"],
            created_at=k["created_at"],
            is_active=k["is_active"],
        )
        for k in _api_keys.values()
        if k["tenant_id"] == tenant_id
    ]
    return keys


@app.delete("/api/v1/keys/{key_id}")
async def delete_api_key(key_id: str, req: Request):
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    key = _api_keys.get(key_id)
    if not key or key["tenant_id"] != tenant_id:
        raise HTTPException(status_code=404, detail="API key not found")

    key["is_active"] = False
    return {"status": "deleted"}


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
        _metrics.record_migration_complete("completed", "api")
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
        _metrics.record_migration_complete("failed", "api")
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


@app.get("/api/v1/libraries/{name}")
async def get_library(name: str):
    libraries = _client.list_libraries()
    lib = libraries.get(name)
    if not lib:
        raise HTTPException(status_code=404, detail=f"Library '{name}' not found")
    return lib


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


# ── User Migration Packs (custom libraries) ────────────────────


USER_PACKS_DIR = Path(__file__).parent.parent.parent.parent / "user-packs"
USER_PACKS_DIR.mkdir(exist_ok=True)


class UserPackCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    library: str = Field(..., min_length=1, max_length=100)
    versions: List[Dict[str, Any]] = Field(default_factory=list)


class UserPackUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    versions: Optional[List[Dict[str, Any]]] = None


class UserPackRuleRequest(BaseModel):
    id: str = ""
    change_type: str = "custom_replacement"
    description: str = ""
    version_introduced: str = ""
    old_name: Optional[str] = None
    new_name: Optional[str] = None
    function_name: Optional[str] = None
    argument_name: Optional[str] = None
    new_argument_name: Optional[str] = None
    replacement: Optional[str] = None
    safety: str = "safe"
    confidence_hint: str = "high"
    tags: List[str] = Field(default_factory=list)


def _read_user_pack(pack_id: str) -> Optional[Dict[str, Any]]:
    pack_file = USER_PACKS_DIR / f"{pack_id}.json"
    if not pack_file.exists():
        return None
    try:
        return json.loads(pack_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_user_pack(pack_id: str, data: Dict[str, Any]) -> None:
    pack_file = USER_PACKS_DIR / f"{pack_id}.json"
    pack_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _delete_user_pack_file(pack_id: str) -> bool:
    pack_file = USER_PACKS_DIR / f"{pack_id}.json"
    if pack_file.exists():
        pack_file.unlink()
        return True
    return False


@app.get("/api/v1/user-packs")
async def list_user_packs(req: Request):
    tenant_id = getattr(req.state, "tenant_id", None)
    packs = []
    for pack_file in USER_PACKS_DIR.glob("*.json"):
        try:
            data = json.loads(pack_file.read_text(encoding="utf-8"))
            pack_id = pack_file.stem
            versions = data.get("versions", [])
            rule_count = sum(len(v.get("rules", [])) for v in versions)
            packs.append({
                "id": pack_id,
                "name": data.get("name", pack_id),
                "description": data.get("description", ""),
                "library": data.get("library", pack_id),
                "version_count": len(versions),
                "rule_count": rule_count,
                "is_published": data.get("is_published", False),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
            })
        except Exception:
            continue
    return {"packs": packs}


@app.post("/api/v1/user-packs")
async def create_user_pack(request: UserPackCreateRequest, req: Request):
    pack_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "library": request.library,
        "name": request.name,
        "description": request.description,
        "schema_version": "1.0",
        "is_published": False,
        "created_at": now,
        "updated_at": now,
        "versions": request.versions,
    }
    _write_user_pack(pack_id, data)
    return {
        "id": pack_id,
        "name": request.name,
        "library": request.library,
        "description": request.description,
        "version_count": len(request.versions),
        "created_at": now,
    }


@app.get("/api/v1/user-packs/{pack_id}")
async def get_user_pack(pack_id: str, req: Request):
    data = _read_user_pack(pack_id)
    if not data:
        raise HTTPException(status_code=404, detail="Pack not found")
    versions = data.get("versions", [])
    rule_count = sum(len(v.get("rules", [])) for v in versions)
    return {
        "id": pack_id,
        "name": data.get("name", pack_id),
        "description": data.get("description", ""),
        "library": data.get("library", pack_id),
        "versions": versions,
        "version_count": len(versions),
        "rule_count": rule_count,
        "is_published": data.get("is_published", False),
        "created_at": data.get("created_at", ""),
        "updated_at": data.get("updated_at", ""),
    }


@app.put("/api/v1/user-packs/{pack_id}")
async def update_user_pack(pack_id: str, request: UserPackUpdateRequest, req: Request):
    data = _read_user_pack(pack_id)
    if not data:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    if request.name is not None:
        data["name"] = request.name
    if request.description is not None:
        data["description"] = request.description
    if request.versions is not None:
        data["versions"] = request.versions
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    _write_user_pack(pack_id, data)
    return {"status": "updated", "id": pack_id}


@app.delete("/api/v1/user-packs/{pack_id}")
async def delete_user_pack(pack_id: str, req: Request):
    if not _delete_user_pack_file(pack_id):
        raise HTTPException(status_code=404, detail="Pack not found")
    return {"status": "deleted"}


@app.post("/api/v1/user-packs/{pack_id}/publish")
async def publish_user_pack(pack_id: str, req: Request):
    data = _read_user_pack(pack_id)
    if not data:
        raise HTTPException(status_code=404, detail="Pack not found")
    data["is_published"] = not data.get("is_published", False)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_user_pack(pack_id, data)
    return {"status": "published" if data["is_published"] else "unpublished", "id": pack_id}


@app.post("/api/v1/user-packs/{pack_id}/versions/{version}/rules")
async def add_rule_to_pack(pack_id: str, version: str, request: UserPackRuleRequest, req: Request):
    data = _read_user_pack(pack_id)
    if not data:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    rule_id = request.id or f"{pack_id[:4]}-{len(data.get('versions', []))}-{uuid.uuid4().hex[:4]}"
    rule_data = {
        "id": rule_id,
        "change_type": request.change_type,
        "description": request.description,
        "version_introduced": version,
        "old_name": request.old_name,
        "new_name": request.new_name,
        "function_name": request.function_name,
        "argument_name": request.argument_name,
        "new_argument_name": request.new_argument_name,
        "replacement": request.replacement,
        "safety": request.safety,
        "confidence_hint": request.confidence_hint,
        "tags": request.tags,
    }
    
    versions = data.get("versions", [])
    target_version = None
    for v in versions:
        if v.get("version") == version:
            target_version = v
            break
    
    if target_version is None:
        target_version = {"version": version, "rules": []}
        versions.append(target_version)
    
    target_version.setdefault("rules", []).append(rule_data)
    data["versions"] = versions
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_user_pack(pack_id, data)
    
    return {"status": "created", "rule_id": rule_id}


# ── Main ─────────────────────────────────────────────────────────


def main() -> None:
    import uvicorn
    setup_logging(
        app_env=os.environ.get("APP_ENV", "development"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
