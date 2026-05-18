"""Migration worker FastAPI application."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys as _sys

_sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.requests import Request

from core.changelog_parser import ChangelogParser, MigrationRule, ChangeType
from core.version_resolver import VersionResolver
from core.migration_engine import TransactionalMigrationEngine
from core.validation import RuleValidator, ValidationReport, IdempotencyChecker
from core.diff_analyzer import GitDiffAnalyzer, ChangelogToRulesConverter

logger = logging.getLogger(__name__)


class MigrateCodeRequest(BaseModel):
    source_code: str = Field(..., description="Source code to migrate")
    rules: List[Dict[str, Any]] = Field(..., description="Migration rules")
    source_version: str = Field(..., description="Source version")
    target_version: str = Field(default="latest")
    dry_run: bool = Field(default=False)


class ValidateRulesRequest(BaseModel):
    rules: List[Dict[str, Any]] = Field(...)


class GenerateRulesDiffRequest(BaseModel):
    old_code: str = Field(...)
    new_code: str = Field(...)


class GenerateRulesChangelogRequest(BaseModel):
    changelog_text: str = Field(...)
    version: str = Field(...)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Migration worker starting", port=os.environ.get("PORT", 8001))
    yield
    logger.info("Migration worker shutting down")


app = FastAPI(
    title="MigratorGen Migration Worker",
    version="0.1.0",
    description="Background migration processing service",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "migration-worker",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/migrate/code")
async def migrate_code(request: MigrateCodeRequest):
    """Migrate source code using provided rules."""
    try:
        rules = [MigrationRule.from_dict(r) for r in request.rules]
        engine = TransactionalMigrationEngine(transactional=not request.dry_run)
        result = engine.migrate_code(
            request.source_code,
            rules,
            dry_run=request.dry_run,
        )
        return {
            "transformed_code": result.transformed_code,
            "was_modified": result.was_modified,
            "changes": result.changes,
            "confidence": result.overall_confidence,
            "safety": result.safety_level.value if result.safety_level else "unknown",
        }
    except Exception as e:
        logger.exception("Migration failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate")
async def validate_rules(request: ValidateRulesRequest):
    """Validate migration rules."""
    try:
        rules = [MigrationRule.from_dict(r) for r in request.rules]
        validator = RuleValidator()
        report = validator.validate_rules(rules)
        return report.to_dict()
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/generate-rules-from-diff")
async def generate_rules_from_diff(request: GenerateRulesDiffRequest):
    """Auto-generate rules from code diff."""
    analyzer = GitDiffAnalyzer(request.old_code, request.new_code)
    rules = analyzer.analyze()
    return {"rules": rules, "count": len(rules)}


@app.post("/generate-rules-from-changelog")
async def generate_rules_from_changelog(request: GenerateRulesChangelogRequest):
    """Generate rules from changelog text."""
    converter = ChangelogToRulesConverter(request.changelog_text, request.version)
    rules = converter.convert()
    return {"rules": rules, "count": len(rules)}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(
        "services.migration.app:app",
        host="0.0.0.0",
        port=port,
        log_level=os.environ.get("LOG_LEVEL", "info"),
    )