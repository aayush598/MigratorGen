"""Migration worker FastAPI application — delegates to the SDK in local mode."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from migrator_gen import MigrationClient, Rule

logger = logging.getLogger(__name__)

_client = MigrationClient(mode="local")

app = FastAPI(
    title="MigratorGen Worker",
    version="0.1.0",
    description="Background migration worker API",
)


class MigrateCodeRequest(BaseModel):
    source_code: str
    rules: List[Dict[str, Any]]
    source_version: str = "1.0.0"
    target_version: str = "latest"
    dry_run: bool = False


class PreviewRequest(BaseModel):
    source_code: str
    rules: List[Dict[str, Any]]


class GenerateRulesDiffRequest(BaseModel):
    old_code: str
    new_code: str
    module: str = ""


class GenerateRulesChangelogRequest(BaseModel):
    changelog_text: str
    library_name: str = "unknown"


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "migration-worker",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/v1/migrate")
async def migrate_code(req: MigrateCodeRequest):
    try:
        rules = [Rule.from_dict(r) for r in req.rules]
        result = _client.migrate_code(
            req.source_code, rules,
            source_version=req.source_version,
            target_version=req.target_version,
            dry_run=req.dry_run,
        )
        return {
            "original_code": req.source_code,
            "transformed_code": result.transformed_code,
            "was_modified": result.was_modified,
            "changes": result.changes,
            "confidence": result.average_confidence,
            "errors": result.errors,
        }
    except Exception as e:
        logger.exception("Migration failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/preview")
async def preview_migration(req: PreviewRequest):
    try:
        rules = [Rule.from_dict(r) for r in req.rules]
        preview = _client.preview_migration(req.source_code, rules)
        return {
            "diff": preview.diff,
            "change_count": preview.change_count,
            "average_confidence": preview.average_confidence,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/generate-rules/diff")
async def generate_rules_from_diff(req: GenerateRulesDiffRequest):
    try:
        rules = _client.generate_rules_from_diff(req.old_code, req.new_code, req.module)
        return {"rules": [r.to_dict() for r in rules], "rule_count": len(rules)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/generate-rules/changelog")
async def generate_rules_from_changelog(req: GenerateRulesChangelogRequest):
    try:
        result = _client.generate_rules_from_changelog(
            req.changelog_text, req.library_name,
        )
        return {
            "version": result.version,
            "rules": [r.to_dict() for r in result.rules],
            "rule_count": len(result.rules),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
