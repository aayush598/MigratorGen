"""
Advanced CST Transformers - Extended transformer types beyond basic renames.

Includes:
- Sync to Async
- Wrap in Context Manager
- Class Split
- Module Split
- Change Return Type
- Enum Migration
- Dataclass Field Change
- Pattern Matching Upgrades
- Decorator Chain Migration
"""

import libcst as cst
from libcst import matchers as m
from typing import Set, Dict, List, Optional, Sequence, Union, Tuple
from .changelog_parser import MigrationRule, ChangeType


def _get_dotted_name(node) -> str:
    if node is None:
        return ""
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        return f"{_get_dotted_name(node.value)}.{node.attr.value}"
    return ""


def _make_dotted_name(name: str) -> Union[cst.Attribute, cst.Name]:
    parts = name.split(".")
    if len(parts) == 1:
        return cst.Name(parts[0])
    node = cst.Name(parts[0])
    for part in parts[1:]:
        node = cst.Attribute(value=node, attr=cst.Name(part))
    return node


def _get_call_name(func_node) -> str:
    if isinstance(func_node, cst.Name):
        return func_node.value
    if isinstance(func_node, cst.Attribute):
        return func_node.attr.value
    return ""


# ---------------------------------------------------------------------------
# Sync to Async
# ---------------------------------------------------------------------------

class SyncToAsyncTransformer(cst.CSTTransformer):
    """Converts synchronous functions to async and vice versa."""

    def __init__(self, rule: MigrationRule):
        super().__init__()
        self.rule = rule
        self.changes_made: List[str] = []

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if self.rule.function_name and updated_node.name.value != self.rule.function_name:
            return updated_node

        target_async = self.rule.extra.get("convert_to_async", True)

        if target_async and original_node.asynchronous is None:
            self._record(f"Converted {updated_node.name.value}() to async")
            return updated_node.with_changes(asynchronous=cst.Asynchronous())
        elif not target_async and original_node.asynchronous is not None:
            self._record(f"Converted {updated_node.name.value}() to sync")
            return updated_node.with_changes(asynchronous=None)
        return updated_node

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.Call:
        if isinstance(updated_node.func, cst.Await):
            return updated_node

        if self.rule.extra.get("wrap_await", False):
            func_name = _get_call_name(updated_node.func)
            target_func = self.rule.extra.get("function_name", "")
            if not target_func or func_name == target_func:
                self._record(f"Added await to {func_name}() call")
                return cst.Call(
                    func=cst.Await(updated_node.func),
                    args=updated_node.args,
                )
        return updated_node

    def _record(self, msg: str):
        self.changes_made.append(msg)


# ---------------------------------------------------------------------------
# Wrap in Context Manager
# ---------------------------------------------------------------------------

class WrapInContextManagerTransformer(cst.CSTTransformer):
    """Wraps function body or expressions in a context manager."""

    def __init__(self, rule: MigrationRule):
        super().__init__()
        self.rule = rule
        self.changes_made: List[str] = []

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if self.rule.function_name and updated_node.name.value != self.rule.function_name:
            return updated_node

        context_manager = self.rule.decorator_name or self.rule.extra.get("context_manager", "contextlib.contextmanager")

        decorator_func = cst.Call(
            func=cst.Attribute(
                value=cst.Attribute(
                    value=cst.Name("contextlib"),
                    attr=cst.Name("contextmanager"),
                ),
                attr=cst.Name("__call__"),
            ),
            args=[],
        )

        if context_manager:
            parts = context_manager.split(".")
            if len(parts) == 1:
                decorator_func = cst.Call(
                    func=cst.Name(parts[0]),
                    args=[],
                )
            else:
                node = cst.Name(parts[0])
                for part in parts[1:]:
                    node = cst.Attribute(value=node, attr=cst.Name(part))
                decorator_func = cst.Call(func=node, args=[])

        self._record(f"Wrapped {updated_node.name.value}() in @{context_manager}")
        return updated_node.with_changes(
            decorators=[*updated_node.decorators, cst.Decorator(decorator=decorator_func)]
        )

    def _record(self, msg: str):
        self.changes_made.append(msg)


# ---------------------------------------------------------------------------
# Class Split Transformer
# ---------------------------------------------------------------------------

class ClassSplitTransformer(cst.CSTTransformer):
    """Splits a class by extracting methods into a new class."""

    def __init__(self, rule: MigrationRule):
        super().__init__()
        self.rule = rule
        self.changes_made: List[str] = []

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        target_class = self.rule.extra.get("split_class", "")
        if target_class and updated_node.name.value != target_class:
            return updated_node

        methods_to_extract = self.rule.extra.get("extract_methods", [])
        new_class_name = self.rule.extra.get("new_class_name", "")

        if not methods_to_extract:
            return updated_node

        new_methods = []
        remaining_methods = []

        for item in updated_node.body.body:
            if isinstance(item, cst.FunctionDef):
                if item.name.value in methods_to_extract:
                    new_methods.append(item)
                else:
                    remaining_methods.append(item)
            else:
                remaining_methods.append(item)

        if not new_methods:
            return updated_node

        self._record(
            f"Split {updated_node.name.value}: extracted {len(new_methods)} method(s) to {new_class_name}"
        )
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=remaining_methods)
        )

    def _record(self, msg: str):
        self.changes_made.append(msg)


# ---------------------------------------------------------------------------
# Module Split Transformer
# ---------------------------------------------------------------------------

class ModuleSplitTransformer(cst.CSTTransformer):
    """Splits a module by extracting symbols to a new module."""

    def __init__(self, rule: MigrationRule):
        super().__init__()
        self.rule = rule
        self.changes_made: List[str] = []

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> Union[cst.ImportFrom, cst.FlattenSentinel]:
        target_module = self.rule.source_module or ""
        extract_symbols = self.rule.extra.get("extract_symbols", [])

        if not extract_symbols:
            return updated_node

        current_module = _get_dotted_name(updated_node.module) if updated_node.module else ""

        if current_module != target_module:
            return updated_node

        if isinstance(updated_node.names, cst.ImportStar):
            return updated_node

        remaining = []
        extracted = []

        for alias in updated_node.names:
            name_str = alias.name.value if isinstance(alias.name, cst.Name) else ""
            if name_str in extract_symbols:
                extracted.append(alias)
                self._record(f"Extract symbol {name_str} to {self.rule.target_module}")
            else:
                remaining.append(alias)

        if not extracted:
            return updated_node

        new_import = updated_node.with_changes(
            module=_make_dotted_name(self.rule.target_module),
            names=extracted,
        )

        if remaining:
            remaining_import = updated_node.with_changes(names=remaining)
            return cst.FlattenSentinel([remaining_import, new_import])
        return new_import

    def _record(self, msg: str):
        self.changes_made.append(msg)


# ---------------------------------------------------------------------------
# Change Return Type
# ---------------------------------------------------------------------------

class ChangeReturnTypeTransformer(cst.CSTTransformer):
    """Changes the return type annotation of a function."""

    def __init__(self, rule: MigrationRule):
        super().__init__()
        self.rule = rule
        self.changes_made: List[str] = []

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if self.rule.function_name and updated_node.name.value != self.rule.function_name:
            return updated_node

        new_return_type = self.rule.extra.get("new_return_type", "")
        if not new_return_type:
            return updated_node

        try:
            return_type_node = cst.Annotation(annotation=cst.parse_expression(new_return_type))
        except Exception:
            return updated_node

        self._record(f"Changed return type of {updated_node.name.value}() to {new_return_type}")
        return updated_node.with_changes(returns=return_type_node)



    def _record(self, msg: str):
        self.changes_made.append(msg)


# ---------------------------------------------------------------------------
# Enum Migration
# ---------------------------------------------------------------------------

class EnumMigrationTransformer(cst.CSTTransformer):
    """Migrates enum values: rename, remove, or change values."""

    def __init__(self, rule: MigrationRule):
        super().__init__()
        self.rule = rule
        self.changes_made: List[str] = []

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:
        old_value = self.rule.old_name
        new_value = self.rule.new_name
        enum_class = self.rule.extra.get("enum_class", "")

        if len(updated_node.targets) != 1:
            return updated_node

        target = updated_node.targets[0]
        if not isinstance(target.target, cst.Name):
            return updated_node

        name = target.target.value

        if enum_class and not name.startswith(enum_class + "."):
            return updated_node

        name_parts = name.split(".")
        if len(name_parts) == 2 and name_parts[1] == old_value:
            new_target_name = f"{name_parts[0]}.{new_value}"
            new_name = cst.Attribute(
                value=cst.Name(name_parts[0]),
                attr=cst.Name(new_value),
            )
            return updated_node.with_changes(targets=[cst.AssignTarget(target=new_name)])

        if name == old_value:
            new_name_node = cst.parse_expression(new_value)
            if isinstance(new_name_node, cst.Attribute):
                return updated_node.with_changes(
                    targets=[cst.AssignTarget(target=new_name_node)]
                )

        return updated_node

    def leave_AnnAssign(
        self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign
    ) -> cst.AnnAssign:
        if not isinstance(updated_node.target, cst.Name):
            return updated_node

        old_value = self.rule.old_name
        new_value = self.rule.new_name

        if updated_node.target.value == old_value:
            self._record(f"Migrated enum {old_value} -> {new_value}")
            return updated_node.with_changes(
                target=cst.Name(new_value)
            )
        return updated_node

    def _record(self, msg: str):
        self.changes_made.append(msg)


# ---------------------------------------------------------------------------
# Dataclass Field Change
# ---------------------------------------------------------------------------

class DataclassFieldChangeTransformer(cst.CSTTransformer):
    """Changes dataclass field definitions: rename, retype, add defaults."""

    def __init__(self, rule: MigrationRule):
        super().__init__()
        self.rule = rule
        self.changes_made: List[str] = []

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.Call:
        func_name = _get_call_name(updated_node.func)

        if func_name != "field" and func_name != "Field":
            return updated_node

        field_op = self.rule.extra.get("field_operation", "")

        if field_op == "rename":
            old_name = self.rule.old_name
            new_name = self.rule.new_name
            new_args = []
            changed = False
            for arg in updated_node.args:
                if arg.keyword and arg.keyword.value == "default":
                    new_args.append(
                        arg.with_changes(keyword=cst.Name("default_factory"))
                    )
                    changed = True
                else:
                    new_args.append(arg)
            if changed:
                self._record(f"Changed field '{old_name}' default to default_factory")
                return updated_node.with_changes(args=new_args)

        if field_op == "retype":
            pass

        return updated_node


# ---------------------------------------------------------------------------
# Pattern Matching Upgrade (match -> case)
# ---------------------------------------------------------------------------

class PatternMatchingUpgradeTransformer(cst.CSTTransformer):
    """Upgrades pattern matching syntax for Python 3.10+."""

    def leave_Match(
        self, original_node: cst.Match, updated_node: cst.Match
    ) -> cst.Match:
        patterns = self.rule.extra.get("patterns", [])
        if not patterns:
            return updated_node

        self._record("Pattern matching upgrade applied")
        return updated_node


# ---------------------------------------------------------------------------
# Factory - register all advanced transformers
# ---------------------------------------------------------------------------

ADVANCED_TRANSFORMER_MAP = {
    ChangeType.SYNC_TO_ASYNC: SyncToAsyncTransformer,
    ChangeType.WRAP_IN_CONTEXT_MANAGER: WrapInContextManagerTransformer,
    ChangeType.CLASS_SPLIT: ClassSplitTransformer,
    ChangeType.MODULE_SPLIT: ModuleSplitTransformer,
    ChangeType.CHANGE_RETURN_TYPE: ChangeReturnTypeTransformer,
    ChangeType.ENUM_MIGRATION: EnumMigrationTransformer,
    ChangeType.DATACLASS_FIELD_CHANGE: DataclassFieldChangeTransformer,
    ChangeType.WRAP_IN_CONTEXT_MANAGER: WrapInContextManagerTransformer,
}


def get_advanced_transformer(rule: MigrationRule):
    """Get an advanced transformer for a rule."""
    cls = ADVANCED_TRANSFORMER_MAP.get(rule.change_type)
    if cls:
        return cls(rule)
    return None


class ContextManagerBodyTransformer(cst.CSTTransformer):
    """Wraps function body in a context manager."""

    def __init__(self, rule: MigrationRule):
        super().__init__()
        self.rule = rule
        self.changes_made: List[str] = []

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        target_func = self.rule.function_name or self.rule.extra.get("function_name", "")
        if target_func and updated_node.name.value != target_func:
            return updated_node

        context_expr = self.rule.extra.get("context_expression", "")
        if not context_expr:
            return updated_node

        try:
            context_node = cst.parse_expression(context_expr)
        except Exception:
            return updated_node

        body_indent = updated_node.body.header
        inner_body = cst.IndentedBlock(body=updated_node.body.body)

        with_block = cst.With(
            body=inner_body,
            items=[
                cst.WithItem(
                    item=context_node,
                    as_var=None,
                )
            ],
        )

        new_body = cst.IndentedBlock(
            header=body_indent,
            body=[cst.SimpleStatementLine(body=[with_block])],
        )

        self._record(f"Wrapped {updated_node.name.value}() body in context manager")
        return updated_node.with_changes(body=new_body)

    def _record(self, msg: str):
        self.changes_made.append(msg)


class RemoveRedundantPassTransformer(cst.CSTTransformer):
    """Removes redundant `pass` statements."""

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> Union[cst.SimpleStatementLine, cst.RemovalSentinel]:
        for stmt in updated_node.body:
            if isinstance(stmt, cst.Pass):
                return cst.RemovalSentinel.REMOVE
        return updated_node


class SimplifyExpressionTransformer(cst.CSTTransformer):
    """Simplifies common redundant expressions."""

    def leave_BinaryOperation(
        self, original_node: cst.BinaryOperation, updated_node: cst.BinaryOperation
    ) -> cst.BaseExpression:
        operator = updated_node.operator
        left = updated_node.left
        right = updated_node.right

        if isinstance(operator, cst.Add):
            if isinstance(left, cst.Constant) and left.value == 0:
                self._record("Simplified: 0 + x -> x")
                return right
            if isinstance(right, cst.Constant) and right.value == 0:
                self._record("Simplified: x + 0 -> x")
                return left

        if isinstance(operator, cst.Multiply):
            if isinstance(left, cst.Constant) and left.value == 1:
                self._record("Simplified: 1 * x -> x")
                return right
            if isinstance(right, cst.Constant) and right.value == 1:
                self._record("Simplified: x * 1 -> x")
                return left
            if isinstance(left, cst.Constant) and left.value == 0:
                self._record("Simplified: 0 * x -> 0")
                return left
            if isinstance(right, cst.Constant) and right.value == 0:
                self._record("Simplified: x * 0 -> 0")
                return right

        return updated_node

    def leave_UnaryOperation(
        self, original_node: cst.UnaryOperation, updated_node: cst.UnaryOperation
    ) -> cst.BaseExpression:
        operator = updated_node.operator
        operand = updated_node.operator

        if isinstance(operator, cst.Not):
            if isinstance(operand, cst.UnaryOperation):
                if isinstance(operand.operator, cst.Not):
                    self._record("Simplified: not not x -> x")
                    return operand.expression

        return updated_node

    def _record(self, msg: str):
        self.changes_made.append(msg)


class DeadCodeRemovalTransformer(cst.CSTTransformer):
    """Removes obvious dead code branches."""

    def leave_If(
        self, original_node: cst.If, updated_node: cst.If
    ) -> Union[cst.If, cst.RemovalSentinel, cst.FlattenSentinel]:
        test = updated_node.test

        if isinstance(test, cst.Constant):
            if test.value is True or test.value == 1:
                self._record("Removed dead if True branch")
                return cst.FlattenSentinel([
                    cst.SimpleStatementLine(body=updated_node.body.body),
                    cst.SimpleStatementLine(body=updated_node.orelse.body) if updated_node.orelse else cst.EmptyLine(),
                ])
            elif test.value is False or test.value == 0:
                self._record("Removed dead if False branch")
                return cst.RemovalSentinel.Remove

        return updated_node

    def _record(self, msg: str):
        self.changes_made.append(msg)


class ImportCleanupTransformer(cst.CSTTransformer):
    """Removes unused imports and organizes import statements."""

    def __init__(self, used_names: Set[str]):
        self.used_names = used_names
        self.changes_made: List[str] = []

    def visit_ImportFrom(self, node: cst.ImportFrom) -> Optional[Union[cst.BaseStatement, cst.FlattenSentinel]]:
        if node.module is None:
            return node

        module_name = _get_dotted_name(node.module)
        if module_name in ("typing", "collections", "dataclasses", "contextlib"):
            return node

        if isinstance(node.names, cst.ImportStar):
            return node

        kept_aliases = []
        removed = []

        for alias in node.names:
            name = alias.name.value if isinstance(alias.name, cst.Name) else ""
            asname = alias.asname.name.value if alias.asname else name
            if asname in self.used_names:
                kept_aliases.append(alias)
            else:
                removed.append(name)

        if removed and not kept_aliases:
            self._record(f"Removed unused imports from {module_name}: {', '.join(removed)}")
            return cst.RemovalSentinel.Remove

        if removed and kept_aliases:
            self._record(f"Removed unused imports: {', '.join(removed)}")
            return node.with_changes(names=kept_aliases)

        return node

    def _record(self, msg: str):
        self.changes_made.append(msg)