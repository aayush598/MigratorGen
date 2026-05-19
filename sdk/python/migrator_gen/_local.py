"""Local-mode execution engine wrapping the ``core`` package directly.

All libcst-dependent imports are deferred so the module loads
without raising ``ImportError`` even when libcst is not installed.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import models as m
from .exceptions import EngineError, MigrationParseError, MigrationValidationError

log = logging.getLogger(__name__)


def _require(missing_package: str, feature: str = "") -> None:
    """Raise an actionable ``EngineError`` for a missing optional dependency."""
    if not feature:
        feature = f"this operation ({missing_package})"
    raise EngineError(
        f"`{missing_package}` is required for {feature}. "
        f"Install it with: pip install \"migrator_gen[{missing_package}]\""
    )


class LocalEngine:
    """Executes migrations locally by importing the ``core`` package."""

    def __init__(self, config: Any) -> None:
        self._config = config
        self._core = _import_core()
        self._libraries: Optional[Dict[str, Any]] = None

    # ── Internals ───────────────────────────────────────────────────

    def _get_engine(self) -> Any:
        import core
        return core.MigrationEngine(
            transactional=getattr(self._config, 'transactional', True),
            interactive_approval=getattr(self._config, 'interactive_approval', False),
            idempotency_check=getattr(self._config, 'idempotency_check', True),
        )

    def _to_core_rule(self, rule: m.Rule) -> Any:
        from core.changelog_parser import MigrationRule
        return MigrationRule(
            id=rule.id,
            change_type=rule.change_type.value if hasattr(rule.change_type, 'value') else str(rule.change_type),
            version_introduced=rule.version_introduced,
            description=rule.description,
            old_name=rule.old_name,
            new_name=rule.new_name,
            function_name=rule.function_name,
            argument_name=rule.argument_name,
            new_argument_name=rule.new_argument_name,
            default_value=rule.default_value,
            new_argument_value=rule.new_argument_value,
            new_order=rule.new_order,
            old_module=rule.old_module,
            new_module=rule.new_module,
            source_module=rule.source_module,
            target_module=rule.target_module,
            decorator_name=rule.decorator_name,
            replacement=rule.replacement,
            safety=rule.safety,
            confidence_hint=rule.confidence_hint,
            when=rule.when.model_dump() if rule.when else None,
            priority=rule.priority,
        )

    def _to_sdk_rule(self, core_rule: Any) -> m.Rule:
        if hasattr(core_rule, 'model_dump'):
            data = core_rule.model_dump()
        elif hasattr(core_rule, 'dict'):
            data = core_rule.dict()
        else:
            data = dict(core_rule)
        return m.Rule.from_dict(data)

    def _from_core_result(
        self,
        result: Any,
        original: str = "",
        duration_ms: Optional[float] = None,
    ) -> m.MigrateResponse:
        changes = list(result.changes) if hasattr(result, 'changes') else []
        transformed = getattr(result, 'transformed_code', '') or ''
        return m.MigrateResponse(
            original_code=original or getattr(result, 'original_code', ''),
            transformed_code=transformed,
            changes=changes,
            rules_applied=[],
            average_confidence=getattr(result, 'average_confidence', 0.0) or 0.0,
            was_modified=len(changes) > 0,
            errors=list(getattr(result, 'errors', [])),
            duration_ms=duration_ms,
        )

    # ── Public API ──────────────────────────────────────────────────

    def migrate_code(
        self,
        source_code: str,
        rules: List[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        try:
            engine = self._get_engine()
        except Exception as exc:
            _require("libcst", "migrate_code")
            raise EngineError(f"Engine initialisation failed: {exc}") from exc

        core_rules = [self._to_core_rule(r) for r in rules]

        try:
            start = time.monotonic()
            result = engine.migrate_code(source_code, core_rules)
            duration_ms = (time.monotonic() - start) * 1000
        except Exception as exc:
            log.exception("Migration engine failure")
            raise EngineError(f"Migration failed: {exc}") from exc

        return self._from_core_result(result, original=source_code, duration_ms=duration_ms)

    def preview_migration(
        self,
        source_code: str,
        rules: List[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
    ) -> m.DiffPreview:
        try:
            engine = self._get_engine()
        except Exception as exc:
            _require("libcst", "preview_migration")
            raise EngineError(f"Engine initialisation failed: {exc}") from exc

        core_rules = [self._to_core_rule(r) for r in rules]

        try:
            result = engine.migrate_code(source_code, core_rules)
        except Exception as exc:
            log.exception("Preview migration failed")
            raise MigrationParseError(f"Preview failed: {exc}") from exc

        response = self._from_core_result(result, original=source_code)
        diff = _compute_diff(response.original_code, response.transformed_code)
        return m.DiffPreview(
            original_code=response.original_code,
            transformed_code=response.transformed_code,
            diff=diff,
            changes=response.changes,
            change_count=len(response.changes),
            average_confidence=response.average_confidence,
        )

    def validate_rules(self, rules_file_path: str) -> m.ValidationReport:
        try:
            from core.validation import validate_rules_from_file
        except Exception:
            _require("libcst", "validate_rules")
            raise

        try:
            report = validate_rules_from_file(rules_file_path)
        except Exception as exc:
            log.exception("Validation failed")
            raise MigrationValidationError(str(exc)) from exc

        return _convert_validation_report(report)

    def parse_changelog(self, file_path: str) -> m.MigrationFile:
        return _parse_changelog_file(file_path)

    def suggest_migrations(
        self,
        file_path: str,
        destination_library: str,
    ) -> m.AnalyzeResult:
        source_code = Path(file_path).read_text(encoding="utf-8")
        analysis = _analyze_source_code(source_code)
        suggestions: List[str] = []
        heuristic = _generate_suggestions(source_code, analysis, destination_library)
        seen = set()
        for h in heuristic:
            if h not in seen:
                suggestions.append(h)
                seen.add(h)

        return m.AnalyzeResult(
            imports=[m.AnalyzedImport(**i) for i in analysis.get("imports", [])],
            functions=[m.AnalyzedFunction(**f) for f in analysis.get("functions", [])],
            classes=[m.AnalyzedClass(**c) for c in analysis.get("classes", [])],
            suggested_migrations=suggestions,
        )

    def list_libraries(self) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        return result

    def generate_rules_from_diff(
        self,
        old_code: str,
        new_code: str,
        module: str = "",
    ) -> List[m.Rule]:
        try:
            from core.diff_analyzer import generate_from_git_diff
        except Exception:
            _require("libcst", "generate_rules_from_diff")
            raise
        try:
            rules = generate_from_git_diff(old_code, new_code, module)
            return [self._to_sdk_rule(r) for r in rules]
        except Exception as exc:
            raise MigrationParseError(f"Failed to generate rules from diff: {exc}") from exc

    def generate_rules_from_changelog(
        self,
        changelog_text: str,
        library_name: str = "unknown",
    ) -> m.VersionChangelog:
        try:
            from core.diff_analyzer import generate_from_changelog
        except Exception:
            _require("libcst", "generate_rules_from_changelog")
            raise
        try:
            result = generate_from_changelog(changelog_text, library_name)
            rules = [self._to_sdk_rule(r) for r in result.get("rules", [])]
            return m.VersionChangelog(
                version=result.get("version", "0.0.0"),
                release_date=result.get("release_date", ""),
                rules=rules,
            )
        except Exception as exc:
            raise MigrationParseError(
                f"Failed to generate rules from changelog: {exc}"
            ) from exc

    def resolve_path(
        self,
        source_version: str,
        target_version: str,
        library_name: str,
    ) -> m.ResolvedPath:
        try:
            from core import VersionResolver
        except Exception:
            raise EngineError("VersionResolver not available in core")

        try:
            resolver = VersionResolver(changelogs=[])
            path = resolver.resolve_path(source_version, target_version)
            steps = [
                m.MigrationStep(source=s[0], target=s[1], rules=[])
                for s in path.steps
            ]
            return m.ResolvedPath(
                source_version=path.source_version,
                target_version=path.target_version,
                steps=steps,
                is_upgrade=path.is_upgrade,
            )
        except Exception as exc:
            raise MigrationParseError(
                f"Could not resolve migration path for '{library_name}': {exc}"
            ) from exc

    def migrate_file(
        self,
        file_path: str,
        rules: List[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        source_code = Path(file_path).read_text(encoding="utf-8")
        result = self.migrate_code(
            source_code, rules,
            source_version=source_version,
            target_version=target_version,
            dry_run=dry_run,
        )
        if not dry_run and result.was_modified:
            backup = Path(file_path).with_suffix(Path(file_path).suffix + ".bak")
            Path(file_path).rename(backup)
            Path(file_path).write_text(result.transformed_code, encoding="utf-8")
        return result

    def generate_migrator_package(
        self,
        library_name: str,
        output_dir: str = ".",
    ) -> str:
        try:
            from core import MigratorGenerator
        except Exception:
            _require("libcst", "generate_migrator_package")
            raise
        try:
            gen = MigratorGenerator()
            out_path = gen.package(library_name, output_dir)
            return str(out_path)
        except Exception as exc:
            raise MigrationParseError(
                f"Failed to generate migrator package for '{library_name}': {exc}"
            ) from exc

    def health_check(self) -> m.HealthStatus:
        import core
        return m.HealthStatus(
            status="healthy",
            version=getattr(core, "__version__", "0.1.0"),
        )


def _import_core() -> Any:
    """Lazy-import the ``core`` package."""
    try:
        import core  # type: ignore[import-untyped]
    except ImportError as exc:
        raise EngineError(
            "Core engine not found, ensure `pip install migrator-gen[local]`"
        ) from exc
    return core


def _compute_diff(original: str, transformed: str) -> str:
    import difflib
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            transformed.splitlines(keepends=True),
            fromfile="original",
            tofile="transformed",
        )
    )


def _parse_changelog_file(file_path: str) -> m.MigrationFile:
    import json
    try:
        import yaml
    except ImportError:
        raise EngineError(
            "PyYAML is required to parse changelog files. "
            "Install it with: pip install PyYAML"
        )

    path = Path(file_path)
    raw = path.read_text(encoding="utf-8")

    if path.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(raw)
    elif path.suffix == ".json":
        data = json.loads(raw)
    else:
        try:
            data = yaml.safe_load(raw)
        except Exception:
            data = json.loads(raw)

    mf = m.MigrationFile(
        library=data.get("library", "unknown"),
        schema_version=data.get("schema_version", "1.0"),
    )
    for v in data.get("versions", []):
        rules = [m.Rule(**r) for r in v.get("rules", [])]
        mf.versions.append(
            m.VersionChangelog(
                version=v.get("version", "0.0.0"),
                release_date=v.get("release_date"),
                rules=rules,
            )
        )
    return mf


def _analyze_source_code(source_code: str) -> Dict[str, Any]:
    import ast
    result: Dict[str, Any] = {"imports": [], "functions": [], "classes": []}
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return result
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append({"module": "", "name": alias.asname or alias.name})
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                result["imports"].append({"module": module, "name": alias.asname or alias.name})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [a.arg for a in node.args.args]
            decorators = [d.id for d in node.decorator.list if isinstance(d, ast.Name)] if hasattr(node, 'decorator') else []
            result["functions"].append({"name": node.name, "line": node.lineno or 0, "params": params, "decorators": decorators})
        elif isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({"name": item.name, "line": item.lineno or 0, "params": [a.arg for a in item.args.args], "decorators": []})
            result["classes"].append({"name": node.name, "line": node.lineno or 0, "bases": [b.id for b in node.bases if isinstance(b, ast.Name)], "methods": methods})
    return result


def _generate_suggestions(
    source_code: str,
    analysis: Dict[str, Any],
    destination_library: str,
) -> List[str]:
    suggestions: List[str] = []
    imports_found = {imp["name"] for imp in analysis.get("imports", [])}
    if destination_library in imports_found or destination_library.lower() in {i.lower() for i in imports_found}:
        suggestions.append(f"Library '{destination_library}' detected — consider migrating to latest version")
    return suggestions


def _convert_validation_report(core_report: Any) -> m.ValidationReport:
    errors: List[m.RuleValidationMessage] = []
    warnings: List[m.RuleValidationMessage] = []
    info: List[m.RuleValidationMessage] = []

    items = core_report
    if hasattr(core_report, "model_dump"):
        items = core_report.model_dump()
    elif hasattr(core_report, "dict"):
        items = core_report.dict()

    if isinstance(items, dict):
        for msg_list, severity in [
            (items.get("errors", []), "error"),
            (items.get("warnings", []), "warning"),
            (items.get("info", []), "info"),
        ]:
            for msg in msg_list:
                entry = m.RuleValidationMessage(
                    rule_id=msg.get("rule_id", ""),
                    message=msg.get("message", ""),
                    field=msg.get("field"),
                    severity=severity,
                )
                if severity == "error":
                    errors.append(entry)
                elif severity == "warning":
                    warnings.append(entry)
                else:
                    info.append(entry)

    return m.ValidationReport(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        info=info,
    )
