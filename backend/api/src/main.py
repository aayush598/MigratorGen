"""Minimal FastAPI application — lightweight entry point for containerised deployments.

Delegates all business logic to the SDK in local mode.  Use :mod:`server`
for the full-featured API with all endpoints.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from migrator_gen import MigrationClient, Rule

app = FastAPI(
    title="MigratorGen API",
    version="0.1.0",
    description="Migration infrastructure API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_client = MigrationClient(mode="local")


class MigrateCodeRequest(BaseModel):
    source_code: str
    rules: List[Dict[str, Any]]
    source_version: str = "1.0.0"
    target_version: str = "latest"
    dry_run: bool = False


class GenerateDiffRequest(BaseModel):
    old_code: str
    new_code: str
    module: str = ""


class GenerateChangelogRequest(BaseModel):
    changelog_text: str
    library_name: str = "unknown"


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "migration-api",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/migrate/code")
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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rules/generate-from-diff")
async def generate_rules_from_diff(req: GenerateDiffRequest):
    rules = _client.generate_rules_from_diff(req.old_code, req.new_code, req.module)
    return {"rules": [r.to_dict() for r in rules], "rule_count": len(rules)}


@app.post("/rules/generate-from-changelog")
async def generate_rules_from_changelog(req: GenerateChangelogRequest):
    result = _client.generate_rules_from_changelog(req.changelog_text, req.library_name)
    return {
        "version": result.version,
        "rules": [r.to_dict() for r in result.rules],
        "rule_count": len(result.rules),
    }


@app.get("/libraries")
async def list_libraries():
    libs = _client.list_libraries()
    return {"libraries": libs}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, workers=4)
