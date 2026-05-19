from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from ..config import SDKConfig
from ..core import models as m
from ..exceptions import EngineError, MigrationParseError, MigrationValidationError
from ..utils.serialization import compute_diff, read_file

log = logging.getLogger(__name__)


def _require(feature: str = "") -> None:
    if not feature:
        feature = "this operation"
    raise EngineError(
        f"`libcst` is required for {feature}. "
        'Install it with: pip install "migrator-gen[local]"'
    )


def _check_libcst() -> None:
    try:
        import libcst  # noqa: F401
    except ImportError:
        raise EngineError(
            '`libcst` is required for local mode. '
            'Install with: pip install "migrator-gen[local]"'
        )


class LocalMigrationService:
    def __init__(self, config: SDKConfig) -> None:
        self._config = config
        _check_libcst()

    def _get_engine(self) -> Any:
        from ..core.migration_engine import TransactionalMigrationEngine

        return TransactionalMigrationEngine(
            transactional=getattr(self._config, "transactional", True),
            interactive_approval=getattr(self._config, "interactive_approval", False),
            idempotency_check=getattr(self._config, "idempotency_check", True),
        )

    def _to_core_rule(self, rule: m.Rule) -> Any:
        from ..core.changelog_parser import MigrationRule as CoreRule

        return CoreRule(
            id=rule.id,
            change_type=rule.change_type.value if hasattr(rule.change_type, "value") else str(rule.change_type),
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
        if hasattr(core_rule, "model_dump"):
            data = core_rule.model_dump()
        elif hasattr(core_rule, "dict"):
            data = core_rule.dict()
        else:
            data = dict(core_rule)
        return m.Rule.from_dict(data)

    def _from_core_result(
        self,
        result: Any,
        original: str = "",
        duration_ms: float | None = None,
    ) -> m.MigrateResponse:
        changes = list(result.changes) if hasattr(result, "changes") else []
        transformed = getattr(result, "transformed_code", "") or ""
        return m.MigrateResponse(
            original_code=original or getattr(result, "original_code", ""),
            transformed_code=transformed,
            changes=changes,
            rules_applied=[],
            average_confidence=getattr(result, "average_confidence", 0.0) or 0.0,
            was_modified=len(changes) > 0,
            errors=list(getattr(result, "errors", [])),
            duration_ms=duration_ms,
        )

    def migrate_code(
        self,
        source_code: str,
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        try:
            engine = self._get_engine()
        except Exception as exc:
            _require("migrate_code")
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
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
    ) -> m.DiffPreview:
        try:
            engine = self._get_engine()
        except Exception as exc:
            _require("preview_migration")
            raise EngineError(f"Engine initialisation failed: {exc}") from exc
        core_rules = [self._to_core_rule(r) for r in rules]
        try:
            result = engine.migrate_code(source_code, core_rules)
        except Exception as exc:
            log.exception("Preview migration failed")
            raise MigrationParseError(f"Preview failed: {exc}") from exc
        response = self._from_core_result(result, original=source_code)
        diff = compute_diff(response.original_code, response.transformed_code)
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
            from ..core.validation import validate_rules_from_file
        except Exception:
            _require("validate_rules")
            raise
        try:
            report = validate_rules_from_file(rules_file_path)
            return _convert_validation_report(report)
        except Exception as exc:
            log.exception("Validation failed")
            raise MigrationValidationError(str(exc)) from exc

    def parse_changelog(self, file_path: str) -> m.MigrationFile:
        return _parse_changelog_file(file_path)

    def suggest_migrations(self, file_path: str, destination_library: str) -> Any:
        source_code = Path(file_path).read_text(encoding="utf-8")
        analysis = _analyze_source_code(source_code)
        suggestions: list[str] = []
        imports_found = {imp["name"] for imp in analysis.get("imports", [])}
        if destination_library in imports_found or destination_library.lower() in {i.lower() for i in imports_found}:
            suggestions.append(f"Library '{destination_library}' detected")
        return type("AnalyzeResult", (), {
            "imports": [type("Imp", (), {"module": i.get("module", ""), "name": i.get("name", ""), "alias": None}) for i in analysis.get("imports", [])],
            "functions": [type("Fn", (), {"name": i.get("name", ""), "line": i.get("line", 0), "params": i.get("params", []), "decorators": i.get("decorators", [])}) for i in analysis.get("functions", [])],
            "classes": [type("Cls", (), {"name": i.get("name", ""), "line": i.get("line", 0), "bases": i.get("bases", []), "methods": []}) for i in analysis.get("classes", [])],
            "suggested_migrations": suggestions,
        })()

    def list_libraries(self) -> dict[str, dict[str, Any]]:
        return {}

    def generate_rules_from_diff(self, old_code: str, new_code: str, module: str = "") -> list[m.Rule]:
        try:
            from ..core.diff_analyzer import generate_from_git_diff
        except Exception:
            _require("generate_rules_from_diff")
            raise
        try:
            rules = generate_from_git_diff(old_code, new_code, module)
            return [self._to_sdk_rule(r) for r in rules]
        except Exception as exc:
            raise MigrationParseError(f"Failed to generate rules from diff: {exc}") from exc

    def generate_rules_from_changelog(self, changelog_text: str, library_name: str = "unknown") -> m.VersionChangelog:
        try:
            from ..core.diff_analyzer import generate_from_changelog
        except Exception:
            _require("generate_rules_from_changelog")
            raise
        try:
            result = generate_from_changelog(changelog_text, library_name)
            rules = [self._to_sdk_rule(r) for r in result.get("rules", [])]
            return m.VersionChangelog(version=result.get("version", "0.0.0"), release_date=result.get("release_date", ""), rules=rules)
        except Exception as exc:
            raise MigrationParseError(f"Failed to generate rules from changelog: {exc}") from exc

    def resolve_path(self, source_version: str, target_version: str, library_name: str) -> m.ResolvedPath:
        try:
            from ..core.version_resolver import VersionResolver
        except Exception:
            raise EngineError("VersionResolver not available in core")
        try:
            resolver = VersionResolver(changelogs=[])
            path = resolver.resolve_path(source_version, target_version)
            steps = [m.MigrationStep(source=s[0], target=s[1], rules=[]) for s in path.steps]
            return m.ResolvedPath(source_version=path.source_version, target_version=path.target_version, steps=steps)
        except Exception as exc:
            raise MigrationParseError(f"Could not resolve migration path: {exc}") from exc

    def migrate_file(
        self,
        file_path: str,
        rules: list[m.Rule],
        source_version: str = "1.0.0",
        target_version: str = "latest",
        dry_run: bool = False,
    ) -> m.MigrateResponse:
        source_code = read_file(file_path)
        result = self.migrate_code(source_code, rules, source_version=source_version, target_version=target_version, dry_run=dry_run)
        if not dry_run and result.was_modified:
            backup = Path(file_path).with_suffix(Path(file_path).suffix + ".bak")
            Path(file_path).rename(backup)
            Path(file_path).write_text(result.transformed_code, encoding="utf-8")
        return result

    def generate_migrator_package(self, library_name: str, output_dir: str = ".") -> str:
        try:
            from ..core.migrator_generator import MigratorGenerator
        except Exception:
            _require("generate_migrator_package")
            raise
        try:
            gen = MigratorGenerator()
            return str(gen.package(library_name, output_dir))
        except Exception as exc:
            raise MigrationParseError(f"Failed to generate migrator package: {exc}") from exc

    def health_check(self) -> m.HealthStatus:
        from .._version import __version__

        return m.HealthStatus(status="healthy", version=__version__)


def _parse_changelog_file(file_path: str) -> m.MigrationFile:
    import json

    try:
        import yaml
    except ImportError:
        raise EngineError("PyYAML is required. Install with: pip install PyYAML")
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
    from ..core.models import MigrationFile as MF
    from ..core.models import Rule
    from ..core.models import VersionChangelog as VC

    mf = MF(library=data.get("library", "unknown"), schema_version=data.get("schema_version", "1.0"))
    for v in data.get("versions", []):
        rules = [Rule(**r) for r in v.get("rules", [])]
        mf.versions.append(VC(version=v.get("version", "0.0.0"), release_date=v.get("release_date"), rules=rules))
    return mf


def _analyze_source_code(source_code: str) -> dict:
    import ast

    result: dict = {"imports": [], "functions": [], "classes": []}
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
            decorators = [d.id for d in node.decorator.list if isinstance(d, ast.Name)] if hasattr(node, "decorator") else []
            result["functions"].append({"name": node.name, "line": node.lineno or 0, "params": params, "decorators": decorators})
        elif isinstance(node, ast.ClassDef):
            methods: list = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({"name": item.name, "line": item.lineno or 0, "params": [a.arg for a in item.args.args], "decorators": []})
            result["classes"].append({"name": node.name, "line": node.lineno or 0, "bases": [b.id for b in node.bases if isinstance(b, ast.Name)], "methods": methods})
    return result


def _convert_validation_report(core_report: Any) -> m.ValidationReport:
    errors: list = []
    warnings: list = []
    info: list = []
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
                entry = {"rule_id": msg.get("rule_id", ""), "message": msg.get("message", ""), "field": msg.get("field"), "severity": severity}
                if severity == "error":
                    errors.append(entry)
                elif severity == "warning":
                    warnings.append(entry)
                else:
                    info.append(entry)
    return m.ValidationReport(valid=len(errors) == 0, errors=errors, warnings=warnings, info=info)
