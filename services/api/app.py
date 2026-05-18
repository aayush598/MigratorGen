"""API gateway FastAPI application."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys_path_inserted = False
for _p in [str(Path(__file__).parent.parent.parent), str(Path(__file__).parent.parent.parent.parent)):
    if _p not in __import__("sys").path:
        __import__("sys").path.insert(0, _p)
        sys_path_inserted = True

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.requests import Request

from core.changelog_parser import ChangelogParser, MigrationRule, ChangeType
from core.version_resolver import VersionResolver
from core.migration_engine import TransactionalMigrationEngine
from core.validation import RuleValidator
from core.diff_analyzer import GitDiffAnalyzer, ChangelogToRulesConverter

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MigratorGen API",
    version="0.1.0",
    description="AI-native migration infrastructure API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MigrateCodeRequest(BaseModel):
    source_code: str = Field(..., description="Source code to migrate")
    rules: List[Dict[str, Any]] = Field(..., description="Migration rules")
    source_version: str = Field(..., description="Source version")
    target_version: str = Field(default="latest")
    dry_run: bool = Field(default=False)


class ValidateRulesRequest(BaseModel):
    rules: List[Dict[str, Any]] = Field(...)


@app.get("/health")
async def health_check():
    """API health check."""
    return {
        "status": "healthy",
        "service": "migration-api",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/migrate/code")
async def migrate_code(req: MigrateCodeRequest):
    """Migrate source code."""
    try:
        rules = [MigrationRule.from_dict(r) for r in req.rules]
        engine = TransactionalMigrationEngine()
        result = engine.migrate_code(
            req.source_code,
            rules,
            dry_run=req.dry_run,
        )
        return {
            "original_code": req.source_code,
            "transformed_code": result.transformed_code,
            "was_modified": result.was_modified,
            "changes": result.changes,
            "confidence": result.overall_confidence,
        }
    except Exception as e:
        logger.exception("Migration failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rules/validate")
async def validate_rules(req: ValidateRulesRequest):
    """Validate migration rules."""
    try:
        rules = [MigrationRule.from_dict(r) for r in req.rules]
        validator = RuleValidator()
        report = validator.validate_rules(rules)
        return {
            "valid": report.valid,
            "errors": [e.model_dump() for e in report.errors],
            "warnings": [w.model_dump() for w in report.warnings],
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/rules/generate-from-diff")
async def generate_rules_from_diff(
    old_code: str = Body(...),
    new_code: str = Body(...),
):
    """Generate rules from code diff."""
    analyzer = GitDiffAnalyzer(old_code, new_code)
    rules = analyzer.analyze()
    return {"rules": rules, "rule_count": len(rules)}


@app.post("/rules/generate-from-changelog")
async def generate_rules_from_changelog(
    changelog_text: str = Body(...),
    version: str = Body(...),
):
    """Generate rules from changelog text."""
    converter = ChangelogToRulesConverter(changelog_text, version)
    rules = converter.convert()
    return {"rules": rules, "rule_count": len(rules)}


@app.get("/versions")
async def list_versions():
    """List available versions from migration packs."""
    packs_dir = Path(__file__).parent.parent.parent / "migration_packs"
    versions = []
    if packs_dir.exists():
        for pack in packs_dir.glob("*.json"):
            try:
                import json
                data = json.loads(pack.read_text())
                lib = data.get("library", pack.stem)
                vers = [v["version"] for v in data.get("versions", [])]
                versions.append({"library": lib, "versions": vers})
            except Exception:
                pass
    return {"versions": versions}


@app.get("/libraries")
async def list_libraries():
    """List known migration libraries."""
    packs_dir = Path(__file__).parent.parent.parent / "migration_packs"
    libs = []
    if packs_dir.exists():
        for pack in packs_dir.glob("*.json"):
            try:
                import json
                data = json.loads(pack.read_text())
                libs.append({
                    "name": data.get("library", pack.stem),
                    "description": f"Migration rules for {pack.stem}",
                })
            except Exception:
                pass
    return {"libraries": libs}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return __import__("fastapi").Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, workers=4)