import ast
import json
from pathlib import Path

from pydantic import BaseModel

from .changelog_parser import ChangeType, MigrationRule


def validate_rules_from_file(rules_file_path: str) -> ValidationReport:
    """Load a rules file and validate all rules, returning a ValidationReport."""
    path = Path(rules_file_path)
    raw = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required to load .yaml files")
        data = yaml.safe_load(raw)
    else:
        data = json.loads(raw)

    rules: list[MigrationRule] = []
    for v in data.get("versions", []):
        for r in v.get("rules", []):
            rules.append(MigrationRule(**r))

    validator = RuleValidator()
    return validator.validate_rules(rules)


class ValidationMessage(BaseModel):
    rule_id: str
    message: str
    field: str | None = None
    severity: str = "error"


class ValidationReport(BaseModel):
    valid: bool = True
    errors: list[ValidationMessage] = []
    warnings: list[ValidationMessage] = []
    info: list[ValidationMessage] = []

    def to_dict(self):
        return self.model_dump()


class BaseRuleValidator:
    required_fields: set[str] = set()
    forbidden_fields: set[str] = set()
    reversible: bool = True

    def validate(self, rule: MigrationRule, report: ValidationReport):
        rule_dict = rule.model_dump(exclude_none=True)

        for field in self.required_fields:
            if field not in rule_dict or rule_dict[field] == "":
                report.errors.append(
                    ValidationMessage(
                        rule_id=rule.id,
                        message=f"Missing required field: {field}",
                        field=field,
                    )
                )

        for field in self.forbidden_fields:
            if field in rule_dict and rule_dict[field] is not None:
                report.errors.append(
                    ValidationMessage(
                        rule_id=rule.id,
                        message=f"Forbidden field for {rule.change_type.value}: {field}",
                        field=field,
                    )
                )

        self.custom_validate(rule, report)

    def custom_validate(self, rule: MigrationRule, report: ValidationReport):
        pass


class RenameFunctionValidator(BaseRuleValidator):
    required_fields: set[str] = {"old_name", "new_name"}
    forbidden_fields: set[str] = {
        "old_module",
        "new_module",
        "decorator_name",
        "function_name",
        "argument_name",
        "new_argument_name",
        "default_value",
        "argument_position",
        "new_order",
        "replacement",
        "removal_version",
        "source_module",
        "target_module",
    }

    def custom_validate(self, rule: MigrationRule, report: ValidationReport):
        if rule.old_name == rule.new_name:
            report.warnings.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message="old_name and new_name are identical",
                )
            )

        builtins = {"open", "print", "len", "list", "dict", "set", "str", "int", "float", "bool"}
        if rule.old_name in builtins:
            report.warnings.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message=f"Renaming builtin function '{rule.old_name}' is dangerous",
                )
            )

        self._validate_identifier(rule.old_name, "old_name", rule, report)
        self._validate_identifier(rule.new_name, "new_name", rule, report)

    def _validate_identifier(
        self, value: str | None, field: str, rule: MigrationRule, report: ValidationReport
    ):
        if value and not value.replace("_", "").isalnum():
            report.errors.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message=f"Invalid Python identifier in {field}: {value}",
                    field=field,
                )
            )


class AddArgumentValidator(BaseRuleValidator):
    required_fields: set[str] = {"function_name", "argument_name"}
    forbidden_fields: set[str] = {
        "old_name",
        "new_name",
        "old_module",
        "new_module",
        "decorator_name",
        "new_argument_name",
        "new_order",
        "replacement",
        "removal_version",
        "source_module",
        "target_module",
    }

    def custom_validate(self, rule: MigrationRule, report: ValidationReport):
        if rule.default_value is not None:
            try:
                ast.parse(rule.default_value, mode="eval")
            except Exception:
                report.errors.append(
                    ValidationMessage(
                        rule_id=rule.id,
                        message=f"Invalid Python expression in default_value: {rule.default_value}",
                        field="default_value",
                    )
                )


class RemoveArgumentValidator(BaseRuleValidator):
    required_fields: set[str] = {"function_name", "argument_name"}
    forbidden_fields: set[str] = {
        "old_name",
        "new_name",
        "old_module",
        "new_module",
        "decorator_name",
        "new_argument_name",
        "default_value",
        "new_order",
        "replacement",
        "removal_version",
        "source_module",
        "target_module",
    }
    reversible = False


class RenameClassValidator(BaseRuleValidator):
    required_fields: set[str] = {"old_name", "new_name"}
    forbidden_fields: set[str] = {
        "old_module",
        "new_module",
        "decorator_name",
        "function_name",
        "argument_name",
        "new_argument_name",
        "default_value",
        "new_order",
        "replacement",
        "removal_version",
        "source_module",
        "target_module",
    }

    def custom_validate(self, rule: MigrationRule, report: ValidationReport):
        if rule.old_name == rule.new_name:
            report.warnings.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message="old_name and new_name are identical",
                )
            )


class RenameAttributeValidator(BaseRuleValidator):
    required_fields: set[str] = {"old_name", "new_name"}
    forbidden_fields: set[str] = {
        "old_module",
        "new_module",
        "decorator_name",
        "function_name",
        "argument_name",
        "new_argument_name",
        "default_value",
        "new_order",
        "replacement",
        "removal_version",
        "source_module",
        "target_module",
    }


class RenameImportValidator(BaseRuleValidator):
    required_fields: set[str] = {"old_name", "new_name", "old_module", "new_module"}
    forbidden_fields: set[str] = {
        "decorator_name",
        "function_name",
        "argument_name",
        "new_argument_name",
        "default_value",
        "new_order",
        "replacement",
        "removal_version",
        "source_module",
        "target_module",
    }

    def custom_validate(self, rule: MigrationRule, report: ValidationReport):
        self._validate_module_path(rule.old_module, "old_module", rule, report)
        self._validate_module_path(rule.new_module, "new_module", rule, report)

    def _validate_module_path(
        self, value: str | None, field: str, rule: MigrationRule, report: ValidationReport
    ):
        if value and (".." in value or value.startswith(".")):
            report.errors.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message=f"Invalid module path in {field}: {value}",
                    field=field,
                )
            )


class ChangeArgumentDefaultValidator(BaseRuleValidator):
    required_fields: set[str] = {"argument_name"}
    forbidden_fields: set[str] = {
        "old_name",
        "new_name",
        "old_module",
        "new_module",
        "decorator_name",
        "new_argument_name",
        "new_order",
        "replacement",
        "removal_version",
        "source_module",
        "target_module",
    }

    def custom_validate(self, rule: MigrationRule, report: ValidationReport):
        if rule.default_value is None:
            report.errors.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message="Missing required field: default_value",
                    field="default_value",
                )
            )
        else:
            try:
                ast.parse(rule.default_value, mode="eval")
            except Exception:
                report.errors.append(
                    ValidationMessage(
                        rule_id=rule.id,
                        message=f"Invalid Python expression in default_value: {rule.default_value}",
                        field="default_value",
                    )
                )


class ReorderArgumentsValidator(BaseRuleValidator):
    required_fields: set[str] = {"function_name", "new_order"}
    forbidden_fields: set[str] = {
        "old_name",
        "new_name",
        "old_module",
        "new_module",
        "decorator_name",
        "argument_name",
        "new_argument_name",
        "default_value",
        "replacement",
        "removal_version",
        "source_module",
        "target_module",
    }

    def custom_validate(self, rule: MigrationRule, report: ValidationReport):
        if rule.new_order and len(rule.new_order) != len(set(rule.new_order)):
            report.errors.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message="new_order contains duplicate parameter names",
                    field="new_order",
                )
            )


class DeprecateFunctionValidator(BaseRuleValidator):
    required_fields: set[str] = {"old_name"}
    forbidden_fields: set[str] = {
        "new_name",
        "old_module",
        "new_module",
        "decorator_name",
        "function_name",
        "argument_name",
        "new_argument_name",
        "default_value",
        "new_order",
        "source_module",
        "target_module",
    }


class RemoveFunctionValidator(BaseRuleValidator):
    required_fields: set[str] = {"old_name"}
    forbidden_fields: set[str] = {
        "new_name",
        "old_module",
        "new_module",
        "decorator_name",
        "function_name",
        "argument_name",
        "new_argument_name",
        "default_value",
        "new_order",
        "source_module",
        "target_module",
    }
    reversible = False


class RemoveClassValidator(BaseRuleValidator):
    required_fields: set[str] = {"old_name"}
    forbidden_fields: set[str] = {
        "new_name",
        "old_module",
        "new_module",
        "decorator_name",
        "function_name",
        "argument_name",
        "new_argument_name",
        "default_value",
        "new_order",
        "source_module",
        "target_module",
    }
    reversible = False


class MoveToModuleValidator(BaseRuleValidator):
    required_fields: set[str] = {"old_name", "source_module", "target_module"}
    forbidden_fields: set[str] = {
        "new_name",
        "old_module",
        "new_module",
        "decorator_name",
        "function_name",
        "argument_name",
        "new_argument_name",
        "default_value",
        "new_order",
        "replacement",
        "removal_version",
    }

    def custom_validate(self, rule: MigrationRule, report: ValidationReport):
        if rule.source_module == rule.target_module:
            report.warnings.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message="source_module and target_module are identical",
                )
            )


class AddDecoratorValidator(BaseRuleValidator):
    required_fields: set[str] = {"function_name", "decorator_name"}
    forbidden_fields: set[str] = {
        "old_name",
        "new_name",
        "old_module",
        "new_module",
        "argument_name",
        "new_argument_name",
        "default_value",
        "new_order",
        "replacement",
        "removal_version",
        "source_module",
        "target_module",
    }


class RemoveDecoratorValidator(BaseRuleValidator):
    required_fields: set[str] = {"function_name", "decorator_name"}
    forbidden_fields: set[str] = {
        "old_name",
        "new_name",
        "old_module",
        "new_module",
        "argument_name",
        "new_argument_name",
        "default_value",
        "new_order",
        "replacement",
        "removal_version",
        "source_module",
        "target_module",
    }
    reversible = False


class ReplaceWithPropertyValidator(BaseRuleValidator):
    required_fields: set[str] = {"old_name", "new_name"}
    forbidden_fields: set[str] = {
        "old_module",
        "new_module",
        "decorator_name",
        "function_name",
        "argument_name",
        "new_argument_name",
        "default_value",
        "new_order",
        "replacement",
        "removal_version",
        "source_module",
        "target_module",
    }


class RenameArgumentValidator(BaseRuleValidator):
    required_fields: set[str] = {"function_name", "argument_name", "new_argument_name"}
    forbidden_fields: set[str] = {
        "old_name",
        "new_name",
        "old_module",
        "new_module",
        "decorator_name",
        "default_value",
        "new_order",
        "replacement",
        "removal_version",
        "source_module",
        "target_module",
    }


CAPABILITIES: dict[ChangeType, BaseRuleValidator] = {
    ChangeType.RENAME_FUNCTION: RenameFunctionValidator(),
    ChangeType.RENAME_CLASS: RenameClassValidator(),
    ChangeType.RENAME_ATTRIBUTE: RenameAttributeValidator(),
    ChangeType.RENAME_IMPORT: RenameImportValidator(),
    ChangeType.ADD_ARGUMENT: AddArgumentValidator(),
    ChangeType.REMOVE_ARGUMENT: RemoveArgumentValidator(),
    ChangeType.CHANGE_ARGUMENT_DEFAULT: ChangeArgumentDefaultValidator(),
    ChangeType.REORDER_ARGUMENTS: ReorderArgumentsValidator(),
    ChangeType.DEPRECATE_FUNCTION: DeprecateFunctionValidator(),
    ChangeType.REMOVE_FUNCTION: RemoveFunctionValidator(),
    ChangeType.REMOVE_CLASS: RemoveClassValidator(),
    ChangeType.MOVE_TO_MODULE: MoveToModuleValidator(),
    ChangeType.ADD_DECORATOR: AddDecoratorValidator(),
    ChangeType.REMOVE_DECORATOR: RemoveDecoratorValidator(),
    ChangeType.REPLACE_WITH_PROPERTY: ReplaceWithPropertyValidator(),
    ChangeType.RENAME_ARGUMENT: RenameArgumentValidator(),
    ChangeType.CHANGE_RETURN_TYPE: BaseRuleValidator(),
    ChangeType.WRAP_IN_CONTEXT_MANAGER: BaseRuleValidator(),
    ChangeType.SYNC_TO_ASYNC: BaseRuleValidator(),
    ChangeType.CLASS_SPLIT: BaseRuleValidator(),
    ChangeType.MODULE_SPLIT: BaseRuleValidator(),
    ChangeType.ENUM_MIGRATION: BaseRuleValidator(),
    ChangeType.DATACLASS_FIELD_CHANGE: BaseRuleValidator(),
}


class RuleValidator:
    def validate_rule(self, rule: MigrationRule, report: ValidationReport):
        if rule.change_type not in CAPABILITIES:
            report.errors.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message=f"No capability validator registered for: {rule.change_type.value}",
                )
            )
            return

        validator = CAPABILITIES[rule.change_type]
        validator.validate(rule, report)

        from .transformers import TRANSFORMER_MAP

        if rule.change_type not in TRANSFORMER_MAP:
            report.errors.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message=f"No transformer registered for: {rule.change_type.value}",
                )
            )

        if not validator.reversible and rule.reversible:
            report.warnings.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message="Rule is marked reversible but its type is typically not",
                    severity="warning",
                )
            )

        if not validator.reversible and not rule.reversible:
            report.info.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message="Rule is not reversible",
                )
            )

        self._validate_conditions(rule, report)
        self._validate_dependencies(rule, report)
        self._validate_priority(rule, report)

    def _validate_conditions(self, rule: MigrationRule, report: ValidationReport):
        if rule.when is None:
            return
        cond = rule.when
        if cond.imported_from and cond.not_imported_from:
            if cond.imported_from == cond.not_imported_from:
                report.warnings.append(
                    ValidationMessage(
                        rule_id=rule.id,
                        message="imported_from and not_imported_from are mutually exclusive",
                        field="when",
                    )
                )
        if cond.inside_class and cond.outside_class:
            report.warnings.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message="inside_class and outside_class are mutually exclusive",
                    field="when",
                )
            )
        if cond.custom_condition:
            try:
                ast.parse(cond.custom_condition, mode="eval")
            except Exception:
                report.errors.append(
                    ValidationMessage(
                        rule_id=rule.id,
                        message=f"Invalid Python expression in custom_condition: {cond.custom_condition}",
                        field="when.custom_condition",
                    )
                )

    def _validate_dependencies(self, rule: MigrationRule, report: ValidationReport):
        for dep_id in rule.depends_on:
            if dep_id == rule.id:
                report.errors.append(
                    ValidationMessage(
                        rule_id=rule.id,
                        message="Rule cannot depend on itself",
                        field="depends_on",
                    )
                )
        for conflict_id in rule.conflicts_with:
            if conflict_id == rule.id:
                report.errors.append(
                    ValidationMessage(
                        rule_id=rule.id,
                        message="Rule cannot conflict with itself",
                        field="conflicts_with",
                    )
                )
            if conflict_id in rule.depends_on:
                report.warnings.append(
                    ValidationMessage(
                        rule_id=rule.id,
                        message=f"Rule depends on {conflict_id} which it also conflicts with",
                        field="depends_on",
                    )
                )

    def _validate_priority(self, rule: MigrationRule, report: ValidationReport):
        if rule.priority < 0 or rule.priority > 1000:
            report.errors.append(
                ValidationMessage(
                    rule_id=rule.id,
                    message=f"Priority must be 0-1000, got: {rule.priority}",
                    field="priority",
                )
            )

    def validate_rules(self, rules: list[MigrationRule]) -> ValidationReport:
        report = ValidationReport()

        seen_rules = {}
        seen_ids = {}

        for rule in rules:
            self.validate_rule(rule, report)

            if rule.id in seen_ids:
                report.errors.append(
                    ValidationMessage(
                        rule_id=rule.id,
                        message=f"Duplicate rule ID: {rule.id} (first seen in {seen_ids[rule.id]})",
                    )
                )
            seen_ids[rule.id] = rule.id

            key_items = [rule.change_type]
            for attr in ["old_name", "function_name", "old_module"]:
                val = getattr(rule, attr, None)
                if val:
                    key_items.append(val)
            key = tuple(key_items)

            if key in seen_rules and key != (rule.change_type,):
                conflicting_id = seen_rules[key]
                report.warnings.append(
                    ValidationMessage(
                        rule_id=rule.id,
                        message=f"Rule may duplicate or conflict with existing rule: {conflicting_id}",
                    )
                )
            else:
                seen_rules[key] = rule.id

            for field in ["old_name", "new_name", "function_name", "argument_name"]:
                val = getattr(rule, field, None)
                if val and isinstance(val, str):
                    parts = val.split(".")
                    if not all(p.isidentifier() for p in parts if p):
                        report.errors.append(
                            ValidationMessage(
                                rule_id=rule.id,
                                message=f"Invalid identifier in {field}: {val}",
                                field=field,
                            )
                        )

            for field in ["old_module", "new_module", "source_module", "target_module"]:
                val = getattr(rule, field, None)
                if val and isinstance(val, str):
                    if ".." in val or val.startswith("."):
                        report.errors.append(
                            ValidationMessage(
                                rule_id=rule.id,
                                message=f"Invalid module path in {field}: {val}",
                                field=field,
                            )
                        )

        if report.errors:
            report.valid = False

        return report


class RuleDependencyGraph:
    """
    Builds and validates a dependency graph from migration rules.
    Used to determine correct execution order.
    """

    def __init__(self, rules: list[MigrationRule]):
        self.rules = {r.id: r for r in rules}
        self.graph: dict[str, set[str]] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        for rule in self.rules.values():
            self.graph[rule.id] = set()

        for rule in self.rules.values():
            for dep_id in rule.depends_on:
                if dep_id in self.graph:
                    self.graph[dep_id].add(rule.id)
                else:
                    pass

            for after_id in rule.run_after:
                if after_id in self.graph:
                    self.graph[after_id].add(rule.id)
                else:
                    pass

            if rule.change_type == ChangeType.MOVE_TO_MODULE:
                pass

    def resolve_order(self) -> list[str]:
        """Return rule IDs in topologically sorted order."""
        visited = set()
        order = []
        stack = list(self.rules.keys())

        def dfs(node_id: str, path: set[str]):
            if node_id in path:
                return
            if node_id in visited:
                return
            visited.add(node_id)
            path.add(node_id)
            for dep in self.graph.get(node_id, []):
                dfs(dep, path)
            path.discard(node_id)
            order.insert(0, node_id)

        for rule_id in list(self.rules.keys()):
            dfs(rule_id, set())

        return order

    def get_execution_order(self, rule_ids: list[str]) -> list[str]:
        """Get topologically sorted order for a subset of rules."""
        subgraph = {rid: self.rules[rid] for rid in rule_ids if rid in self.rules}
        graph = RuleDependencyGraph(list(subgraph.values()))
        return graph.resolve_order()

    def has_conflicts(self, rule_ids: list[str]) -> list[tuple[str, str]]:
        """Check for rule conflicts."""
        conflicts = []
        for rule_id in rule_ids:
            rule = self.rules[rule_id]
            for conflict_id in rule.conflicts_with:
                if conflict_id in rule_ids:
                    conflicts.append((rule_id, conflict_id))
        return conflicts


class IdempotencyChecker:
    """Checks if a migration is idempotent."""

    @staticmethod
    def check_rule_idempotency(rule: MigrationRule, code: str, transformer_cls) -> bool:
        """Check if applying the same rule twice produces the same output."""
        import libcst as cst

        from .transformers import get_transformer

        t1 = get_transformer(rule)
        if t1 is None:
            return True

        try:
            tree1 = cst.parse_module(code)
            new1 = tree1.visit(t1)
            code1 = new1.code

            t2 = get_transformer(rule)
            tree2 = cst.parse_module(code1)
            new2 = tree2.visit(t2)
            code2 = new2.code

            return code1 == code2
        except Exception:
            return False

    @staticmethod
    def compute_fingerprint(rules: list[MigrationRule]) -> str:
        """Compute a fingerprint hash for a set of rules."""
        import hashlib

        parts = []
        for r in sorted(rules, key=lambda x: x.id):
            parts.append(f"{r.id}:{r.change_type.value}")
            if r.old_name:
                parts.append(f"old={r.old_name}")
            if r.new_name:
                parts.append(f"new={r.new_name}")
            if r.function_name:
                parts.append(f"fn={r.function_name}")
        content = "|".join(parts)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
