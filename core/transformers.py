"""
CST Transformers - LibCST-based code transformers for each ChangeType.
Each transformer handles one specific type of migration rule.
"""

import libcst as cst
from libcst import matchers as m
from typing import Set, Dict, List, Optional, Sequence, Union
from .changelog_parser import MigrationRule, ChangeType


# ---------------------------------------------------------------------------
# Base transformer
# ---------------------------------------------------------------------------

class BaseTransformer(cst.CSTTransformer):
    """Base class for all migrator transformers."""

    def __init__(self, rule: MigrationRule):
        self.rule = rule
        self.changes_made: List[str] = []

    def _record(self, msg: str):
        self.changes_made.append(msg)


# ---------------------------------------------------------------------------
# 1. Rename Function Call / Definition
# ---------------------------------------------------------------------------

class RenameFunctionTransformer(BaseTransformer):
    """Renames function calls and definitions from old_name to new_name."""

    def leave_Name(
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.Name:
        if updated_node.value == self.rule.old_name:
            self._record(f"Renamed function: {self.rule.old_name} -> {self.rule.new_name}")
            return updated_node.with_changes(value=self.rule.new_name)
        return updated_node


# ---------------------------------------------------------------------------
# 2. Rename Class
# ---------------------------------------------------------------------------

class RenameClassTransformer(BaseTransformer):
    """Renames class references from old_name to new_name."""

    def leave_Name(
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.Name:
        if updated_node.value == self.rule.old_name:
            self._record(f"Renamed class: {self.rule.old_name} -> {self.rule.new_name}")
            return updated_node.with_changes(value=self.rule.new_name)
        return updated_node


# ---------------------------------------------------------------------------
# 3. Rename Attribute Access  (obj.old_attr -> obj.new_attr)
# ---------------------------------------------------------------------------

class RenameAttributeTransformer(BaseTransformer):
    """Renames attribute accesses."""

    def leave_Attribute(
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        if (
            isinstance(updated_node.attr, cst.Name)
            and updated_node.attr.value == self.rule.old_name
        ):
            self._record(
                f"Renamed attribute: .{self.rule.old_name} -> .{self.rule.new_name}"
            )
            return updated_node.with_changes(
                attr=cst.Name(self.rule.new_name)
            )
        return updated_node


# ---------------------------------------------------------------------------
# 4. Rename Import
# ---------------------------------------------------------------------------

class RenameImportTransformer(BaseTransformer):
    """
    Handles:
    - from old_module import old_name  ->  from new_module import new_name
    - import old_module  ->  import new_module
    """

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> Union[cst.ImportFrom, cst.RemovalSentinel]:
        # Get module name
        module_name = _get_dotted_name(updated_node.module) if updated_node.module else ""

        old_module = self.rule.old_module or ""
        new_module = self.rule.new_module or ""
        old_name = self.rule.old_name or ""
        new_name = self.rule.new_name or ""

        if module_name != old_module:
            return updated_node

        # Update module
        new_module_node = _make_dotted_name(new_module) if new_module else updated_node.module

        if isinstance(updated_node.names, cst.ImportStar):
            return updated_node.with_changes(module=new_module_node)

        new_names = []
        changed = False
        for alias in updated_node.names:
            name_str = _get_dotted_name(alias.name)
            if name_str == old_name and new_name:
                new_names.append(alias.with_changes(name=cst.Name(new_name)))
                changed = True
                self._record(
                    f"Renamed import: from {old_module} import {old_name} "
                    f"-> from {new_module} import {new_name}"
                )
            else:
                new_names.append(alias)

        if not changed and old_name:
            return updated_node

        return updated_node.with_changes(
            module=new_module_node,
            names=new_names,
        )

    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.Import:
        return updated_node


# ---------------------------------------------------------------------------
# 5. Add Argument to Function Call
# ---------------------------------------------------------------------------

class AddArgumentTransformer(BaseTransformer):
    """
    Adds a keyword argument to specific function calls.
    E.g., foo() -> foo(new_arg=default_value)
    """

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.Call:
        func_name = _get_call_name(updated_node.func)
        if func_name != self.rule.function_name:
            return updated_node

        # Check if argument already exists
        for arg in updated_node.args:
            if arg.keyword and arg.keyword.value == self.rule.argument_name:
                return updated_node  # Already present

        default_val = self.rule.default_value or "None"
        new_arg = cst.Arg(
            keyword=cst.Name(self.rule.argument_name),
            value=cst.parse_expression(default_val),
            equal=cst.AssignEqual(
                whitespace_before=cst.SimpleWhitespace(""),
                whitespace_after=cst.SimpleWhitespace(""),
            ),
        )

        # Add comma to last existing arg if needed
        existing_args = list(updated_node.args)
        if existing_args:
            last = existing_args[-1]
            existing_args[-1] = last.with_changes(
                comma=cst.MaybeSentinel.DEFAULT
            )
            existing_args.append(new_arg)
        else:
            existing_args = [new_arg]

        self._record(
            f"Added argument '{self.rule.argument_name}={default_val}' to {func_name}()"
        )
        return updated_node.with_changes(args=existing_args)


# ---------------------------------------------------------------------------
# 6. Remove Argument from Function Call
# ---------------------------------------------------------------------------

class RemoveArgumentTransformer(BaseTransformer):
    """Removes a specific argument from function calls."""

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.Call:
        func_name = _get_call_name(updated_node.func)
        if func_name != self.rule.function_name:
            return updated_node

        new_args = [
            arg for arg in updated_node.args
            if not (arg.keyword and arg.keyword.value == self.rule.argument_name)
        ]

        if len(new_args) < len(updated_node.args):
            # Fix trailing comma
            if new_args:
                new_args[-1] = new_args[-1].with_changes(
                    comma=cst.MaybeSentinel.DEFAULT
                )
            self._record(
                f"Removed argument '{self.rule.argument_name}' from {func_name}()"
            )
            return updated_node.with_changes(args=new_args)

        return updated_node


# ---------------------------------------------------------------------------
# 7. Change Argument Default Value
# ---------------------------------------------------------------------------

class ChangeArgumentDefaultTransformer(BaseTransformer):
    """Changes the default value of a parameter in function definitions."""

    def leave_Param(
        self, original_node: cst.Param, updated_node: cst.Param
    ) -> cst.Param:
        if updated_node.name.value != self.rule.argument_name:
            return updated_node

        new_default = self.rule.default_value
        if new_default is None:
            return updated_node

        self._record(
            f"Changed default for '{self.rule.argument_name}' to {new_default}"
        )
        return updated_node.with_changes(
            default=cst.parse_expression(new_default)
        )


# ---------------------------------------------------------------------------
# 8. Reorder Arguments in Function Definition
# ---------------------------------------------------------------------------

class ReorderArgumentsTransformer(BaseTransformer):
    """Reorders parameters in a function definition."""

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if updated_node.name.value != self.rule.function_name:
            return updated_node

        if not self.rule.new_order:
            return updated_node

        params = updated_node.params
        param_map = {p.name.value: p for p in params.params}

        new_params = []
        for name in self.rule.new_order:
            if name in param_map:
                new_params.append(param_map[name])

        # Keep params not in new_order at the end
        mentioned = set(self.rule.new_order)
        for p in params.params:
            if p.name.value not in mentioned:
                new_params.append(p)

        # Fix commas
        fixed = []
        for i, p in enumerate(new_params):
            if i < len(new_params) - 1:
                fixed.append(p.with_changes(comma=cst.MaybeSentinel.DEFAULT))
            else:
                fixed.append(p.with_changes(comma=cst.MaybeSentinel.DEFAULT))

        self._record(f"Reordered parameters of {self.rule.function_name}()")
        return updated_node.with_changes(
            params=params.with_changes(params=fixed)
        )


# ---------------------------------------------------------------------------
# 9. Deprecate / Warn on Function Use
# ---------------------------------------------------------------------------

class DeprecateFunctionTransformer(BaseTransformer):
    """
    Inserts a deprecation warning comment above deprecated function calls.
    """

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> Union[cst.SimpleStatementLine, cst.FlattenSentinel]:
        for stmt in updated_node.body:
            if isinstance(stmt, cst.Expr) and isinstance(stmt.value, cst.Call):
                func_name = _get_call_name(stmt.value.func)
                if func_name == self.rule.old_name:
                    replacement = self.rule.replacement or "N/A"
                    comment_line = cst.EmptyLine(
                        comment=cst.Comment(
                            f"# DEPRECATED: {func_name}() is deprecated. Use {replacement} instead."
                        )
                    )
                    self._record(f"Marked {func_name}() as deprecated")
                    return updated_node.with_changes(
                        leading_lines=[*updated_node.leading_lines, comment_line]
                    )
        return updated_node


# ---------------------------------------------------------------------------
# 10. Move to Module (update imports)
# ---------------------------------------------------------------------------

class MoveToModuleTransformer(BaseTransformer):
    """
    Updates imports when a symbol is moved from one module to another.
    from old_module import Symbol -> from new_module import Symbol
    """

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        module_name = _get_dotted_name(updated_node.module) if updated_node.module else ""

        if module_name != self.rule.source_module:
            return updated_node

        if isinstance(updated_node.names, cst.ImportStar):
            return updated_node

        symbol = self.rule.old_name
        new_module = self.rule.target_module

        for alias in updated_node.names:
            if _get_dotted_name(alias.name) == symbol:
                self._record(
                    f"Moved import: {symbol} from {self.rule.source_module} to {new_module}"
                )
                return updated_node.with_changes(
                    module=_make_dotted_name(new_module)
                )

        return updated_node


# ---------------------------------------------------------------------------
# 11. Add Decorator
# ---------------------------------------------------------------------------

class AddDecoratorTransformer(BaseTransformer):
    """Adds a decorator to a specific function or class definition."""

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if updated_node.name.value != self.rule.function_name:
            return updated_node

        dec_name = self.rule.decorator_name
        # Check if already present
        for dec in updated_node.decorators:
            if isinstance(dec.decorator, cst.Name) and dec.decorator.value == dec_name:
                return updated_node

        new_decorator = cst.Decorator(
            decorator=cst.Name(dec_name),
            leading_lines=[],
        )
        self._record(f"Added @{dec_name} to {self.rule.function_name}()")
        return updated_node.with_changes(
            decorators=[*updated_node.decorators, new_decorator]
        )


# ---------------------------------------------------------------------------
# 12. Remove Decorator
# ---------------------------------------------------------------------------

class RemoveDecoratorTransformer(BaseTransformer):
    """Removes a specific decorator from functions."""

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if updated_node.name.value != self.rule.function_name:
            return updated_node

        dec_name = self.rule.decorator_name
        new_decorators = [
            d for d in updated_node.decorators
            if not (isinstance(d.decorator, cst.Name) and d.decorator.value == dec_name)
        ]

        if len(new_decorators) < len(updated_node.decorators):
            self._record(f"Removed @{dec_name} from {self.rule.function_name}()")
            return updated_node.with_changes(decorators=new_decorators)

        return updated_node


# ---------------------------------------------------------------------------
# 13. Replace Function Call with Property Access
# ---------------------------------------------------------------------------

class ReplaceWithPropertyTransformer(BaseTransformer):
    """
    Replaces obj.method() with obj.property
    E.g., obj.get_name() -> obj.name
    """

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> Union[cst.Call, cst.Attribute, cst.Name]:
        func = updated_node.func
        if not isinstance(func, cst.Attribute):
            return updated_node

        if func.attr.value != self.rule.old_name:
            return updated_node

        # Only replace if no arguments
        if updated_node.args:
            return updated_node

        self._record(
            f"Replaced {self.rule.old_name}() with property {self.rule.new_name}"
        )
        return func.with_changes(attr=cst.Name(self.rule.new_name))


# ---------------------------------------------------------------------------
# 14. Rename keyword argument in calls
# ---------------------------------------------------------------------------

class RenameArgumentTransformer(BaseTransformer):
    """Renames a keyword argument in specific function calls."""

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.Call
    ) -> cst.Call:
        func_name = _get_call_name(updated_node.func)
        if func_name != self.rule.function_name:
            return updated_node

        new_args = []
        changed = False
        for arg in updated_node.args:
            if arg.keyword and arg.keyword.value == self.rule.argument_name:
                new_args.append(
                    arg.with_changes(keyword=cst.Name(self.rule.new_argument_name))
                )
                changed = True
            else:
                new_args.append(arg)

        if changed:
            self._record(
                f"Renamed arg '{self.rule.argument_name}' -> "
                f"'{self.rule.new_argument_name}' in {func_name}()"
            )
            return updated_node.with_changes(args=new_args)

        return updated_node


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

TRANSFORMER_MAP = {
    ChangeType.RENAME_FUNCTION: RenameFunctionTransformer,
    ChangeType.RENAME_CLASS: RenameClassTransformer,
    ChangeType.RENAME_ATTRIBUTE: RenameAttributeTransformer,
    ChangeType.RENAME_IMPORT: RenameImportTransformer,
    ChangeType.ADD_ARGUMENT: AddArgumentTransformer,
    ChangeType.REMOVE_ARGUMENT: RemoveArgumentTransformer,
    ChangeType.CHANGE_ARGUMENT_DEFAULT: ChangeArgumentDefaultTransformer,
    ChangeType.REORDER_ARGUMENTS: ReorderArgumentsTransformer,
    ChangeType.DEPRECATE_FUNCTION: DeprecateFunctionTransformer,
    ChangeType.REMOVE_FUNCTION: DeprecateFunctionTransformer,  # warn, can't auto-remove
    ChangeType.MOVE_TO_MODULE: MoveToModuleTransformer,
    ChangeType.ADD_DECORATOR: AddDecoratorTransformer,
    ChangeType.REMOVE_DECORATOR: RemoveDecoratorTransformer,
    ChangeType.REPLACE_WITH_PROPERTY: ReplaceWithPropertyTransformer,
}


def get_transformer(rule: MigrationRule) -> Optional[BaseTransformer]:
    """Get the appropriate transformer for a rule."""
    cls = TRANSFORMER_MAP.get(rule.change_type)
    if cls:
        return cls(rule)
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_dotted_name(node) -> str:
    """Extract dotted name string from a CST node."""
    if node is None:
        return ""
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        return f"{_get_dotted_name(node.value)}.{node.attr.value}"
    return ""


def _make_dotted_name(name: str) -> Union[cst.Attribute, cst.Name]:
    """Create a CST node from a dotted name string."""
    parts = name.split(".")
    if len(parts) == 1:
        return cst.Name(parts[0])
    node = cst.Name(parts[0])
    for part in parts[1:]:
        node = cst.Attribute(value=node, attr=cst.Name(part))
    return node


def _get_call_name(func_node) -> str:
    """Extract function name from a Call node's func attribute."""
    if isinstance(func_node, cst.Name):
        return func_node.value
    if isinstance(func_node, cst.Attribute):
        return func_node.attr.value
    return ""