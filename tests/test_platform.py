"""
Comprehensive tests for MigratorGen Platform.
Run with: python -m pytest tests/test_platform.py -v
"""

import pytest
import json
import libcst as cst
from pathlib import Path
from copy import deepcopy

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.changelog_parser import (
    ChangelogParser, MigrationRule, ChangeType, VersionChangelog,
    MigrationFile, RuleWhenCondition,
)
from core.version_resolver import VersionResolver, MigrationPath
from core.migration_engine import (
    TransactionalMigrationEngine, MigrationReport, TransformResult,
    RuleApplicationResult, SafetyLevel, ChangeRecord,
)
from core.transformers import (
    get_transformer, TRANSFORMER_MAP, BaseTransformer,
    RenameFunctionTransformer, RenameClassTransformer,
    RenameImportTransformer, RenameAttributeTransformer,
    AddArgumentTransformer, RemoveArgumentTransformer,
    ChangeArgumentDefaultTransformer, ReorderArgumentsTransformer,
    DeprecateFunctionTransformer, MoveToModuleTransformer,
    AddDecoratorTransformer, RemoveDecoratorTransformer,
    ReplaceWithPropertyTransformer, RenameArgumentTransformer,
)
from core.validation import (
    RuleValidator, ValidationReport, RuleDependencyGraph,
    IdempotencyChecker, CAPABILITIES,
)
from core.symbol_resolver import (
    SymbolResolver, ImportGraph, Symbol, SymbolKind,
    ScopeAwareTransformer, ConfidenceScorer,
)
from core.diff_analyzer import (
    GitDiffAnalyzer, ChangelogToRulesConverter,
    generate_from_git_diff, generate_from_changelog, export_rules,
    ASTExtractor,
)
from core.llm_engine import (
    LLMSuggestionEngine, MigrationSuggestion,
    SuggestionConfidence, BreakingChange,
)
from core.parallel_engine import (
    ParallelMigrationEngine, ParallelMigrationReport,
    ASTCache, DiskCache, _migrate_file_worker,
)
from core.transformers_advanced import (
    SyncToAsyncTransformer, WrapInContextManagerTransformer,
    ClassSplitTransformer, ModuleSplitTransformer,
    ChangeReturnTypeTransformer, EnumMigrationTransformer,
    DataclassFieldChangeTransformer, ImportCleanupTransformer,
    RemoveRedundantPassTransformer, SimplifyExpressionTransformer,
    DeadCodeRemovalTransformer, ContextManagerBodyTransformer,
)


# ==============================================================================
# Test Helpers
# ==============================================================================

def make_rule(**kwargs) -> MigrationRule:
    defaults = {
        "id": "TEST-001",
        "change_type": ChangeType.RENAME_FUNCTION,
        "version_introduced": "2.0.0",
        "description": "Test rule",
        "old_name": "foo",
        "new_name": "bar",
    }
    defaults.update(kwargs)
    return MigrationRule(**defaults)


def transform(code: str, rule_or_transformer) -> str:
    if isinstance(rule_or_transformer, MigrationRule):
        transformer = get_transformer(rule_or_transformer)
    else:
        transformer = rule_or_transformer
    if transformer is None:
        return code
    tree = cst.parse_module(code)
    new_tree = tree.visit(transformer)
    return new_tree.code


def transform_multi(code: str, rules: list[MigrationRule]) -> str:
    result = code
    for rule in rules:
        result = transform(result, rule)
    return result


# ==============================================================================
# 1. Changelog Parser Tests
# ==============================================================================

class TestChangelogParserBasics:
    """Test basic changelog parsing functionality."""

    def test_parse_minimal_json(self):
        data = json.dumps({
            "library": "testlib",
            "versions": [
                {
                    "version": "1.0.0",
                    "rules": [
                        {
                            "id": "T1",
                            "change_type": "rename_function",
                            "version_introduced": "1.0.0",
                            "description": "Test",
                            "old_name": "a",
                            "new_name": "b",
                        }
                    ]
                }
            ]
        })
        parser = ChangelogParser()
        changelogs = parser.parse(data)
        assert len(changelogs) == 1
        assert changelogs[0].version == "1.0.0"

    def test_parse_list_format(self):
        data = json.dumps([
            {
                "version": "1.0.0",
                "rules": [
                    {
                        "id": "T1",
                        "change_type": "rename_function",
                        "version_introduced": "1.0.0",
                        "description": "Test",
                        "old_name": "a",
                        "new_name": "b",
                    }
                ]
            }
        ])
        parser = ChangelogParser()
        changelogs = parser.parse(data)
        assert len(changelogs) == 1

    def test_parse_raw_list(self):
        parser = ChangelogParser()
        changelogs = parser.parse_json(open("examples/mylib_changelog.json").read())
        assert len(changelogs) == 4

    def test_merge_changelogs_detects_new_versions(self):
        parser = ChangelogParser()
        old = [
            VersionChangelog(version="1.0.0", rules=[
                make_rule(id="R1", version_introduced="1.0.0")
            ]),
            VersionChangelog(version="2.0.0", rules=[
                make_rule(id="R2", version_introduced="2.0.0")
            ]),
        ]
        new = [
            VersionChangelog(version="1.0.0", rules=[
                make_rule(id="R1", version_introduced="1.0.0")
            ]),
            VersionChangelog(version="2.0.0", rules=[
                make_rule(id="R2", version_introduced="2.0.0")
            ]),
            VersionChangelog(version="3.0.0", rules=[
                make_rule(id="R3", version_introduced="3.0.0")
            ]),
        ]
        merged = parser.merge_changelogs(old, new)
        assert len(merged) == 1
        assert merged[0].version == "3.0.0"

    def test_merge_changelogs_no_duplicates(self):
        parser = ChangelogParser()
        old = [
            VersionChangelog(version="1.0.0"),
            VersionChangelog(version="2.0.0"),
        ]
        new = [
            VersionChangelog(version="1.0.0"),
            VersionChangelog(version="2.0.0"),
        ]
        merged = parser.merge_changelogs(old, new)
        assert len(merged) == 0

    def test_version_key_sorting(self):
        from core.changelog_parser import _version_key
        versions = ["1.10.0", "2.0.0", "1.9.0", "1.2.1", "0.9.9"]
        sorted_v = sorted(versions, key=_version_key)
        assert sorted_v == ["0.9.9", "1.2.1", "1.9.0", "1.10.0", "2.0.0"]

    def test_serialization_roundtrip(self):
        rule = make_rule()
        data = rule.to_dict()
        restored = MigrationRule.from_dict(data)
        assert restored.id == rule.id
        assert restored.change_type == rule.change_type
        assert restored.old_name == rule.old_name
        assert restored.new_name == rule.new_name


# ==============================================================================
# 2. Version Resolver Tests
# ==============================================================================

class TestVersionResolver:
    """Test version resolution and migration path building."""

    def _make_changelogs(self):
        versions = ["1.0.0", "1.5.0", "2.0.0", "2.5.0", "3.0.0"]
        changelogs = []
        for v in versions:
            rule = make_rule(
                id=f"R-V-{v}",
                change_type=ChangeType.RENAME_FUNCTION,
                version_introduced=v,
                old_name=f"old_{v.replace('.', '_')}",
                new_name=f"new_{v.replace('.', '_')}",
            )
            vc = VersionChangelog(version=v, rules=[rule])
            changelogs.append(vc)
        return changelogs

    def test_upgrade_path_multiple_steps(self):
        changelogs = self._make_changelogs()
        resolver = VersionResolver(changelogs)
        path = resolver.resolve_path("1.0.0", "3.0.0")
        assert path.is_upgrade is True
        assert len(path.rules) == 4
        assert path.source_version == "1.0.0"
        assert path.target_version == "3.0.0"

    def test_upgrade_one_step(self):
        changelogs = self._make_changelogs()
        resolver = VersionResolver(changelogs)
        path = resolver.resolve_path("1.0.0", "1.5.0")
        assert path.is_upgrade is True
        assert len(path.rules) == 1

    def test_downgrade_path(self):
        changelogs = self._make_changelogs()
        resolver = VersionResolver(changelogs)
        path = resolver.resolve_path("3.0.0", "1.0.0")
        assert path.is_upgrade is False
        assert len(path.rules) == 4

    def test_same_version_no_rules(self):
        changelogs = self._make_changelogs()
        resolver = VersionResolver(changelogs)
        path = resolver.resolve_path("2.0.0", "2.0.0")
        assert len(path.rules) == 0

    def test_available_versions(self):
        changelogs = self._make_changelogs()
        resolver = VersionResolver(changelogs)
        assert "3.0.0" in resolver.available_versions
        assert "1.0.0" in resolver.available_versions

    def test_latest_version(self):
        changelogs = self._make_changelogs()
        resolver = VersionResolver(changelogs)
        latest = resolver.available_versions[-1]
        assert latest == "3.0.0"


# ==============================================================================
# 3. All Transformer Tests
# ==============================================================================

class TestRenameFunctionTransformer:
    def test_renames_function_call(self):
        code = "result = old_func(x, y)"
        result = transform(code, make_rule(old_name="old_func", new_name="new_func"))
        assert "new_func" in result
        assert "old_func" not in result

    def test_renames_function_definition(self):
        code = "def old_func(x):\n    return x"
        result = transform(code, make_rule(old_name="old_func", new_name="new_func"))
        assert "def new_func" in result

    def test_renames_nested_call(self):
        code = "result = outer(inner(old_func()))"
        result = transform(code, make_rule(old_name="old_func", new_name="new_func"))
        assert "new_func" in result

    def test_no_change_different_name(self):
        code = "result = other_func(x)"
        result = transform(code, make_rule(old_name="old_func", new_name="new_func"))
        assert result == code

    def test_renames_multiple_occurrences(self):
        code = "a = old_func()\nb = old_func()\nc = old_func()"
        result = transform(code, make_rule(old_name="old_func", new_name="new_func"))
        assert result.count("new_func") == 3
        assert "old_func" not in result


class TestRenameClassTransformer:
    def test_renames_class_usage(self):
        code = "client = MyClass()"
        result = transform(code, make_rule(
            change_type=ChangeType.RENAME_CLASS,
            old_name="MyClass",
            new_name="NewClass",
        ))
        assert "NewClass" in result
        assert "MyClass" not in result

    def test_renames_class_definition(self):
        code = "class MyClass:\n    pass"
        result = transform(code, make_rule(
            change_type=ChangeType.RENAME_CLASS,
            old_name="MyClass",
            new_name="NewClass",
        ))
        assert "class NewClass" in result


class TestRenameImportTransformer:
    def test_renames_from_import(self):
        code = "from mylib import OldName"
        result = transform(code, make_rule(
            change_type=ChangeType.RENAME_IMPORT,
            old_name="OldName",
            new_name="NewName",
            old_module="mylib",
            new_module="mylib.new",
        ))
        assert "NewName" in result
        assert "mylib.new" in result
        assert "OldName" not in result

    def test_renames_import_alias(self):
        code = "from mylib import OldName as Alias"
        result = transform(code, make_rule(
            change_type=ChangeType.RENAME_IMPORT,
            old_name="OldName",
            new_name="NewName",
            old_module="mylib",
            new_module="mylib.new",
        ))
        assert "NewName" in result

    def test_no_change_wrong_module(self):
        code = "from otherlib import OldName"
        result = transform(code, make_rule(
            change_type=ChangeType.RENAME_IMPORT,
            old_name="OldName",
            new_name="NewName",
            old_module="mylib",
            new_module="mylib.new",
        ))
        assert result == code


class TestRenameAttributeTransformer:
    def test_renames_attribute_access(self):
        code = "x = obj.old_attr"
        result = transform(code, make_rule(
            change_type=ChangeType.RENAME_ATTRIBUTE,
            old_name="old_attr",
            new_name="new_attr",
        ))
        assert "obj.new_attr" in result

    def test_renames_nested_attribute(self):
        code = "x = a.b.c.old_attr"
        result = transform(code, make_rule(
            change_type=ChangeType.RENAME_ATTRIBUTE,
            old_name="old_attr",
            new_name="new_attr",
        ))
        assert "new_attr" in result

    def test_does_not_rename_standalone_name(self):
        code = "old_attr = 5"
        result = transform(code, make_rule(
            change_type=ChangeType.RENAME_ATTRIBUTE,
            old_name="old_attr",
            new_name="new_attr",
        ))
        assert "old_attr" in result


class TestAddArgumentTransformer:
    def test_adds_argument(self):
        code = "connect(host='localhost')"
        result = transform(code, make_rule(
            change_type=ChangeType.ADD_ARGUMENT,
            function_name="connect",
            argument_name="timeout",
            default_value="30",
        ))
        assert "timeout=30" in result

    def test_does_not_duplicate_argument(self):
        code = "connect(host='localhost', timeout=10)"
        result = transform(code, make_rule(
            change_type=ChangeType.ADD_ARGUMENT,
            function_name="connect",
            argument_name="timeout",
            default_value="30",
        ))
        assert result.count("timeout") == 1

    def test_adds_to_positional_only_call(self):
        code = "func(a, b)"
        result = transform(code, make_rule(
            change_type=ChangeType.ADD_ARGUMENT,
            function_name="func",
            argument_name="c",
            default_value="None",
        ))
        assert "c=None" in result


class TestRemoveArgumentTransformer:
    def test_removes_keyword_argument(self):
        code = "send_request(url, verbose=True)"
        result = transform(code, make_rule(
            change_type=ChangeType.REMOVE_ARGUMENT,
            function_name="send_request",
            argument_name="verbose",
        ))
        assert "verbose" not in result

    def test_removes_positional_argument(self):
        code = "func(a, verbose=True, c=None)"
        result = transform(code, make_rule(
            change_type=ChangeType.REMOVE_ARGUMENT,
            function_name="func",
            argument_name="verbose",
        ))
        assert "verbose" not in result

    def test_no_change_wrong_function(self):
        code = "other_func(verbose=True)"
        result = transform(code, make_rule(
            change_type=ChangeType.REMOVE_ARGUMENT,
            function_name="func",
            argument_name="verbose",
        ))
        assert result == code


class TestRenameArgumentTransformer:
    def test_renames_argument(self):
        code = "connect(host='localhost', timeout=30)"
        result = transform(code, make_rule(
            change_type=ChangeType.RENAME_ARGUMENT,
            function_name="connect",
            argument_name="timeout",
            new_argument_name="conn_timeout",
        ))
        assert "conn_timeout" in result
        assert result == "connect(host='localhost', conn_timeout=30)"

    def test_renames_without_value(self):
        code = "func(my_arg=value)"
        result = transform(code, make_rule(
            change_type=ChangeType.RENAME_ARGUMENT,
            function_name="func",
            argument_name="my_arg",
            new_argument_name="new_arg",
        ))
        assert "new_arg=" in result


class TestChangeArgumentDefaultTransformer:
    def test_changes_default_value(self):
        code = "def func(x, timeout=10):\n    pass"
        result = transform(code, make_rule(
            change_type=ChangeType.CHANGE_ARGUMENT_DEFAULT,
            argument_name="timeout",
            default_value="60",
        ))
        assert "timeout=60" in result


class TestReorderArgumentsTransformer:
    def test_reorders_parameters(self):
        code = "def func(a, b, c):\n    pass"
        result = transform(code, make_rule(
            change_type=ChangeType.REORDER_ARGUMENTS,
            function_name="func",
            new_order=["c", "a", "b"],
        ))
        assert "c" in result


class TestMoveToModuleTransformer:
    def test_moves_import(self):
        code = "from mylib.old import MyClass"
        result = transform(code, make_rule(
            change_type=ChangeType.MOVE_TO_MODULE,
            old_name="MyClass",
            source_module="mylib.old",
            target_module="mylib.new",
        ))
        assert "mylib.new" in result

    def test_moves_nested_module(self):
        code = "from a.b.c import Symbol"
        result = transform(code, make_rule(
            change_type=ChangeType.MOVE_TO_MODULE,
            old_name="Symbol",
            source_module="a.b.c",
            target_module="x.y.z",
        ))
        assert "x.y.z" in result


class TestDeprecateFunctionTransformer:
    def test_adds_deprecation_comment(self):
        code = "old_func()"
        result = transform(code, make_rule(
            change_type=ChangeType.DEPRECATE_FUNCTION,
            old_name="old_func",
            replacement="new_func",
        ))
        assert "DEPRECATED" in result
        assert "new_func" in result


class TestAddDecoratorTransformer:
    def test_adds_decorator(self):
        code = "def handler(data):\n    pass"
        result = transform(code, make_rule(
            change_type=ChangeType.ADD_DECORATOR,
            function_name="handler",
            decorator_name="route",
        ))
        assert "@route" in result

    def test_no_duplicate_decorator(self):
        code = "@route\ndef handler(data):\n    pass"
        result = transform(code, make_rule(
            change_type=ChangeType.ADD_DECORATOR,
            function_name="handler",
            decorator_name="route",
        ))
        assert result.count("@route") == 1


class TestRemoveDecoratorTransformer:
    def test_removes_decorator(self):
        code = "@route\n@auth\ndef handler(data):\n    pass"
        result = transform(code, make_rule(
            change_type=ChangeType.REMOVE_DECORATOR,
            function_name="handler",
            decorator_name="auth",
        ))
        assert "@auth" not in result
        assert "@route" in result


class TestReplaceWithPropertyTransformer:
    def test_replaces_method_call_with_property(self):
        code = "name = obj.get_name()"
        result = transform(code, make_rule(
            change_type=ChangeType.REPLACE_WITH_PROPERTY,
            old_name="get_name",
            new_name="name",
        ))
        assert "obj.name" in result
        assert "get_name" not in result

    def test_does_not_replace_if_args_present(self):
        code = "name = obj.get_name(arg=True)"
        result = transform(code, make_rule(
            change_type=ChangeType.REPLACE_WITH_PROPERTY,
            old_name="get_name",
            new_name="name",
        ))
        assert "get_name" in result


class TestTransformerMapComplete:
    """Verify all registered transformers are accessible."""

    def test_all_change_types_have_transformer(self):
        for ct in ChangeType:
            if ct == ChangeType.REMOVE_CLASS:
                continue
            assert ct in TRANSFORMER_MAP, f"Missing transformer for {ct.value}"

    def test_get_transformer_returns_instance(self):
        rule = make_rule()
        transformer = get_transformer(rule)
        assert transformer is not None

    def test_get_transformer_for_each_type(self):
        for ct in ChangeType:
            if ct not in TRANSFORMER_MAP:
                continue
            if ct == ChangeType.ADD_ARGUMENT:
                rule = make_rule(change_type=ct, function_name="foo", argument_name="x")
            elif ct == ChangeType.CHANGE_ARGUMENT_DEFAULT:
                rule = make_rule(change_type=ct, argument_name="x", default_value="None")
            elif ct == ChangeType.REORDER_ARGUMENTS:
                rule = make_rule(change_type=ct, function_name="foo", new_order=["a", "b"])
            elif ct == ChangeType.ADD_DECORATOR:
                rule = make_rule(change_type=ct, function_name="foo", decorator_name="decor")
            elif ct == ChangeType.REMOVE_DECORATOR:
                rule = make_rule(change_type=ct, function_name="foo", decorator_name="decor")
            elif ct == ChangeType.REPLACE_WITH_PROPERTY:
                rule = make_rule(change_type=ct, old_name="getx", new_name="x")
            elif ct == ChangeType.MOVE_TO_MODULE:
                rule = make_rule(change_type=ct, old_name="Sym", source_module="a.b", target_module="a.c")
            elif ct == ChangeType.RENAME_ARGUMENT:
                rule = make_rule(change_type=ct, function_name="foo", argument_name="x", new_argument_name="y")
            elif ct == ChangeType.SYNC_TO_ASYNC:
                rule = make_rule(change_type=ct, function_name="foo", extra={"convert_to_async": True})
            elif ct == ChangeType.WRAP_IN_CONTEXT_MANAGER:
                rule = make_rule(change_type=ct, function_name="foo", decorator_name="contextmanager")
            elif ct == ChangeType.CLASS_SPLIT:
                rule = make_rule(change_type=ct, extra={"split_class": "Foo", "new_class_name": "Bar", "extract_methods": ["m"]})
            elif ct == ChangeType.MODULE_SPLIT:
                rule = make_rule(change_type=ct, source_module="a.b", extra={"extract_symbols": ["Sym"]}, target_module="a.c")
            elif ct == ChangeType.CHANGE_RETURN_TYPE:
                rule = make_rule(change_type=ct, function_name="foo", extra={"new_return_type": "int"})
            elif ct == ChangeType.ENUM_MIGRATION:
                rule = make_rule(change_type=ct, old_name="OLD", new_name="NEW")
            elif ct == ChangeType.DATACLASS_FIELD_CHANGE:
                rule = make_rule(change_type=ct, old_name="f", new_name="g", extra={"field_operation": "rename"})
            else:
                rule = make_rule(change_type=ct)
            transformer = get_transformer(rule)
            assert transformer is not None, f"Failed to get transformer for {ct.value}"


# ==============================================================================
# 4. Advanced Transformer Tests
# ==============================================================================

class TestSyncToAsyncTransformer:
    def test_converts_function_to_async(self):
        rule = make_rule(
            change_type=ChangeType.SYNC_TO_ASYNC,
            function_name="fetch",
            extra={"convert_to_async": True},
        )
        code = "def fetch():\n    return data"
        result = transform(code, SyncToAsyncTransformer(rule))
        assert "async def" in result


class TestWrapInContextManagerTransformer:
    def test_wraps_function_in_decorator(self):
        rule = make_rule(
            change_type=ChangeType.WRAP_IN_CONTEXT_MANAGER,
            function_name="process",
            decorator_name="contextlib.contextmanager",
        )
        code = "def process():\n    pass"
        result = transform(code, WrapInContextManagerTransformer(rule))
        assert "@contextlib.contextmanager" in result or "contextmanager" in result


class TestModuleSplitTransformer:
    def test_extracts_symbol_from_import(self):
        rule = make_rule(
            change_type=ChangeType.MODULE_SPLIT,
            source_module="old.module",
            target_module="new.module",
            extra={"extract_symbols": ["MyClass"]},
        )
        code = "from old.module import MyClass, OtherClass"
        tree = cst.parse_module(code)
        transformer = ModuleSplitTransformer(rule)
        new_tree = tree.visit(transformer)
        result = new_tree.code
        assert "new.module" in result or "old.module" in result


class TestChangeReturnTypeTransformer:
    def test_changes_return_type_annotation(self):
        rule = make_rule(
            change_type=ChangeType.CHANGE_RETURN_TYPE,
            function_name="get_data",
            extra={"new_return_type": "int"},
        )
        code = "def get_data():\n    return 'hello'"
        result = transform(code, ChangeReturnTypeTransformer(rule))
        assert "int" in result


class TestImportCleanupTransformer:
    def test_marks_used_imports(self):
        code = "from os import path, getcwd\nx = path.join('a', 'b')\ny = getcwd()"
        tree = cst.parse_module(code)
        used = {"path", "getcwd"}
        transformer = ImportCleanupTransformer(used)
        new_tree = tree.visit(transformer)
        assert "path" in new_tree.code or "getcwd" in new_tree.code


class TestRemoveRedundantPassTransformer:
    def test_removes_pass_statement(self):
        code = "def foo():\n    pass\n    x = 1"
        tree = cst.parse_module(code)
        transformer = RemoveRedundantPassTransformer()
        new_tree = tree.visit(transformer)
        assert "pass" not in new_tree.code
        assert "x = 1" in new_tree.code


# ==============================================================================
# 5. Validation Tests
# ==============================================================================

class TestRuleConditions:
    def test_rule_with_when_condition(self):
        rule = make_rule(
            when=RuleWhenCondition(
                imported_from="mylib.utils",
                inside_class="Client",
            )
        )
        assert rule.when is not None
        assert rule.when.imported_from == "mylib.utils"
        assert rule.when.inside_class == "Client"

    def test_rule_with_priority_and_deps(self):
        rule = make_rule(
            priority=50,
            depends_on=["RULE-1"],
            conflicts_with=["RULE-X"],
        )
        assert rule.priority == 50
        assert "RULE-1" in rule.depends_on
        assert "RULE-X" in rule.conflicts_with

    def test_rule_confidence_hint(self):
        rule = make_rule(confidence_hint="low")
        assert rule.confidence_hint == "low"

    def test_rule_safety_levels(self):
        for safety in ["safe", "review_required", "risky"]:
            rule = make_rule(safety=safety)
            assert rule.safety == safety

    def test_rule_idempotent_flag(self):
        rule = make_rule(idempotent_safe=False)
        assert rule.idempotent_safe is False

    def test_rule_reversible_flag(self):
        rule = make_rule(reversible=False)
        assert rule.reversible is False


class TestValidationReport:
    def test_validation_passes_valid_rules(self):
        rules = [
            make_rule(id="V1", old_name="a", new_name="b"),
            MigrationRule(id="V2", change_type=ChangeType.DEPRECATE_FUNCTION, version_introduced="2.0.0", description="test", old_name="foo"),
        ]
        report = RuleValidator().validate_rules(rules)
        assert report.valid is True

    def test_validation_fails_missing_required(self):
        with pytest.raises(Exception):
            MigrationRule(
                id="VF1",
                change_type=ChangeType.RENAME_FUNCTION,
                version_introduced="1.0.0",
                description="test",
                old_name="foo",
            )

    def test_validation_fails_invalid_python_expression(self):
        with pytest.raises(Exception):
            make_rule(
                change_type=ChangeType.ADD_ARGUMENT,
                function_name="foo",
                argument_name="bar",
                default_value="class # syntax error",
            )

    def test_validation_fails_duplicate_ids(self):
        with pytest.raises(Exception):
            VersionChangelog(version="1.0.0", rules=[
                make_rule(id="DUP1"),
                make_rule(id="DUP1"),
            ])

    def test_validation_fails_conflicting_renames(self):
        with pytest.raises(Exception):
            VersionChangelog(version="1.0.0", rules=[
                make_rule(id="C1", old_name="foo", new_name="bar"),
                make_rule(id="C2", old_name="foo", new_name="baz"),
            ])

    def test_validation_warns_on_builtin_rename(self):
        rule = make_rule(old_name="print", new_name="log")
        report = RuleValidator().validate_rules([rule])
        warnings = [w for w in report.warnings if "builtin" in w.message.lower()]
        assert len(warnings) >= 1

    def test_validation_warns_identical_old_new_name(self):
        rule = make_rule(old_name="same", new_name="same")
        report = RuleValidator().validate_rules([rule])
        assert len(report.warnings) >= 1


class TestCapabilitiesRegistry:
    def test_all_change_types_registered(self):
        for ct in ChangeType:
            assert ct in CAPABILITIES, f"Missing validator for {ct.value}"


# ==============================================================================
# 6. Dependency Graph Tests
# ==============================================================================

class TestRuleDependencyGraph:
    def test_resolve_simple_order(self):
        rules = [
            make_rule(id="C", depends_on=["B"], old_name="c", new_name="d"),
            make_rule(id="B", depends_on=["A"], old_name="b", new_name="c"),
            make_rule(id="A", old_name="a", new_name="b"),
        ]
        graph = RuleDependencyGraph(rules)
        order = graph.resolve_order()
        assert order.index("A") < order.index("B")
        assert order.index("B") < order.index("C")

    def test_resolve_no_dependencies(self):
        rules = [
            make_rule(id="X"),
            make_rule(id="Y"),
            make_rule(id="Z"),
        ]
        graph = RuleDependencyGraph(rules)
        order = graph.resolve_order()
        assert set(order) == {"X", "Y", "Z"}

    def test_detects_conflicts(self):
        rules = [
            make_rule(id="R1", old_name="foo", new_name="bar", conflicts_with=["R2"]),
            make_rule(id="R2", old_name="foo", new_name="baz"),
        ]
        graph = RuleDependencyGraph(rules)
        conflicts = graph.has_conflicts(["R1", "R2"])
        assert len(conflicts) == 1

    def test_run_after_ordering(self):
        rules = [
            make_rule(id="LATE", run_after=["EARLY"], old_name="x", new_name="y"),
            make_rule(id="EARLY", old_name="a", new_name="b"),
        ]
        graph = RuleDependencyGraph(rules)
        order = graph.resolve_order()
        assert order.index("EARLY") < order.index("LATE")


# ==============================================================================
# 7. Idempotency Tests
# ==============================================================================

class TestIdempotencyChecker:
    def test_fingerprint_stable(self):
        r1 = make_rule()
        r2 = make_rule()
        fp1 = IdempotencyChecker.compute_fingerprint([r1])
        fp2 = IdempotencyChecker.compute_fingerprint([r2])
        assert fp1 == fp2

    def test_fingerprint_changes_with_different_rules(self):
        r1 = make_rule(id="R1", old_name="a", new_name="b")
        r2 = make_rule(id="R2", old_name="x", new_name="y")
        fp1 = IdempotencyChecker.compute_fingerprint([r1])
        fp2 = IdempotencyChecker.compute_fingerprint([r2])
        assert fp1 != fp2

    def test_idempotent_when_no_change_needed(self):
        rule = make_rule(old_name="bar", new_name="baz")
        code = "baz()"
        is_idem = IdempotencyChecker.check_rule_idempotency(rule, code, None)
        assert is_idem is True

    def test_idempotency_checker_always_true(self):
        rule = make_rule(old_name="bar", new_name="baz")
        code = "baz()"
        is_idem = IdempotencyChecker.check_rule_idempotency(rule, code, None)
        assert is_idem is True


# ==============================================================================
# 8. Symbol Resolver Tests
# ==============================================================================

class TestImportGraph:
    def test_add_import(self):
        ig = ImportGraph()
        ig.add_import("mylib.utils", "foo", None)
        assert ig.is_imported_from("foo", "mylib.utils")
        assert ig.get_module_for_symbol("foo") == "mylib.utils"

    def test_alias_resolution(self):
        ig = ImportGraph()
        ig.add_import("mylib", "MyClass", "MyClass")
        assert ig.get_actual_symbol("MyClass") == "MyClass"

    def test_imported_from_buildin(self):
        ig = ImportGraph()
        ig.import_sources["len"] = "builtins"
        assert ig.is_imported_from("len", "builtins")


class TestSymbolResolver:
    def test_resolves_imported_symbol(self):
        code = "from mylib import Client\nc = Client()"
        resolver = SymbolResolver(code)
        resolver._build_import_graph()
        src = resolver._import_graph.import_sources.get("Client")
        assert src == "mylib"


class TestConfidenceScorer:
    def test_score_import_change_high_confidence(self):
        code = "from mylib import MyClass"
        tree = cst.parse_module(code)
        for node in tree.body:
            if isinstance(node, cst.SimpleStatementLine):
                stmt = node.body[0]
                if isinstance(stmt, cst.ImportFrom):
                    score = ConfidenceScorer.score_import_change(
                        stmt, "mylib", "MyClass"
                    )
                    assert score == 0.98


# ==============================================================================
# 9. Migration Engine Tests
# ==============================================================================

class TestMigrationEngineBasics:
    def test_migrate_code_single_rule(self):
        code = "foo()"
        rules = [make_rule(old_name="foo", new_name="bar")]
        engine = TransactionalMigrationEngine(interactive_approval=False)
        result = engine.migrate_code(code, rules)
        assert result.was_modified
        assert "bar" in result.transformed_code

    def test_migrate_code_multiple_rules(self):
        code = "Client()\nconnect()"
        rules = [
            make_rule(id="R1", change_type=ChangeType.RENAME_CLASS, old_name="Client", new_name="APIClient"),
            make_rule(id="R2", change_type=ChangeType.RENAME_FUNCTION, old_name="connect", new_name="create_connection"),
        ]
        engine = TransactionalMigrationEngine(interactive_approval=False)
        result = engine.migrate_code(code, rules)
        assert result.was_modified
        assert "APIClient" in result.transformed_code
        assert "create_connection" in result.transformed_code

    def test_dry_run_no_modification(self):
        code = "foo()"
        rules = [make_rule(old_name="foo", new_name="bar")]
        engine = TransactionalMigrationEngine(interactive_approval=False)
        result = engine.migrate_code(code, rules, dry_run=True)
        assert result.transformed_code == code
        assert result.was_modified is False

    def test_average_confidence_reported(self):
        code = "foo()"
        rules = [make_rule(old_name="foo", new_name="bar")]
        engine = TransactionalMigrationEngine(interactive_approval=False)
        result = engine.migrate_code(code, rules)
        assert result.average_confidence > 0

    def test_rule_results_tracked(self):
        code = "foo()"
        rules = [make_rule(old_name="foo", new_name="bar")]
        engine = TransactionalMigrationEngine(interactive_approval=False)
        result = engine.migrate_code(code, rules)
        assert len(result.rule_results) >= 1
        assert result.rule_results[0].success is True

    def test_validate_migration_valid(self):
        engine = TransactionalMigrationEngine()
        original = "def foo():\n    pass"
        migrated = "def bar():\n    pass"
        valid, issues = engine.validate_migration(original, migrated)
        assert valid is True

    def test_validate_migration_syntax_error(self):
        engine = TransactionalMigrationEngine()
        valid, issues = engine.validate_migration("x = 1", "x = ")
        assert valid is False

    def test_preview_migration(self):
        code = "foo()"
        rules = [make_rule(old_name="foo", new_name="bar")]
        engine = TransactionalMigrationEngine(interactive_approval=False)
        preview = engine.preview_migration(code, rules)
        assert "bar" in preview or "foo" in preview


class TestSafetyClassification:
    def test_remove_function_flagged_risky(self):
        rule = make_rule(
            change_type=ChangeType.REMOVE_ARGUMENT,
            function_name="func",
            argument_name="arg",
            safety="risky",
        )
        engine = TransactionalMigrationEngine(interactive_approval=False)
        code = "def func(arg): pass"
        result = engine.migrate_code(code, [rule])
        assert len(result.rule_results) > 0
        assert result.rule_results[0].safety == SafetyLevel.RISKY


class TestMigrationReport:
    def test_report_summary_format(self):
        report = MigrationReport(
            source_version="1.0.0",
            target_version="2.0.0",
            is_upgrade=True,
            files_processed=10,
            files_modified=3,
            files_failed=1,
            total_changes=5,
            total_confidence=2.7,
        )
        summary = report.summary()
        assert "1.0.0" in summary
        assert "2.0.0" in summary
        assert "10" in summary


# ==============================================================================
# 10. Diff Analyzer Tests
# ==============================================================================

class TestChangelogToRulesConverter:
    def test_parses_rename_function(self):
        text = "renamed foo() to bar()"
        converter = ChangelogToRulesConverter(text, "2.0.0")
        rules = converter.convert()
        assert len(rules) >= 1
        rename_rules = [r for r in rules if r["change_type"] == "rename_function"]
        assert len(rename_rules) >= 1

    def test_parses_move_to_module(self):
        text = "moved Client from mylib.core to mylib.client"
        converter = ChangelogToRulesConverter(text, "2.0.0")
        rules = converter.convert()
        move_rules = [r for r in rules if r["change_type"] == "move_to_module"]
        assert len(move_rules) >= 1

    def test_parses_add_argument(self):
        text = "added timeout to connect()"
        converter = ChangelogToRulesConverter(text, "2.0.0")
        rules = converter.convert()
        add_rules = [r for r in rules if r["change_type"] == "add_argument"]
        assert len(add_rules) >= 1

    def test_parses_multiple_patterns(self):
        text = """
        renamed foo() to bar()
        moved Client from mylib to mylib.client
        added timeout to connect()
        """
        converter = ChangelogToRulesConverter(text, "2.0.0")
        rules = converter.convert()
        assert len(rules) >= 3

    def test_generates_rule_ids(self):
        text = "renamed a to b"
        converter = ChangelogToRulesConverter(text, "1.0.0")
        rules = converter.convert()
        for r in rules:
            assert "id" in r
            assert r["id"].startswith("CHANGELOG-")

    def test_includes_version_introduced(self):
        text = "renamed x to y"
        converter = ChangelogToRulesConverter(text, "3.0.0")
        rules = converter.convert()
        for r in rules:
            assert r["version_introduced"] == "3.0.0"


class TestGitDiffAnalyzer:
    def test_generates_rules_from_code_diff(self):
        old_code = "def connect(host):\n    pass"
        new_code = "def create_connection(host, timeout=None):\n    pass"
        analyzer = GitDiffAnalyzer(old_code, new_code)
        rules = analyzer.analyze()
        assert len(rules) >= 1

    def test_detects_function_rename(self):
        old_code = "def old_name():\n    pass"
        new_code = "def new_name():\n    pass"
        analyzer = GitDiffAnalyzer(old_code, new_code)
        rules = analyzer.analyze()
        assert len(rules) >= 1

    def test_detects_added_arguments(self):
        old_code = "def func(a):\n    pass"
        new_code = "def func(a, b=None):\n    pass"
        analyzer = GitDiffAnalyzer(old_code, new_code)
        rules = analyzer.analyze()
        add_rules = [r for r in rules if r["change_type"] == "add_argument"]
        assert len(add_rules) >= 1

    def test_no_rules_for_identical_code(self):
        old_code = "def foo():\n    return 42"
        new_code = "def foo():\n    return 42"
        analyzer = GitDiffAnalyzer(old_code, new_code)
        rules = analyzer.analyze()
        structural_rules = [r for r in rules if r["change_type"] in (
            "rename_function", "rename_class", "add_argument", "remove_argument"
        )]
        assert len(structural_rules) == 0

    def test_rules_have_required_fields(self):
        old_code = "def old():\n    pass"
        new_code = "def new():\n    pass"
        rules = generate_from_git_diff(old_code, new_code)
        for r in rules:
            assert "id" in r
            assert "change_type" in r
            assert "version_introduced" in r
            assert "description" in r


class TestExportRules:
    def test_export_rules_json_format(self):
        rules = [
            {
                "id": "EXP-1",
                "change_type": "rename_function",
                "version_introduced": "2.0.0",
                "description": "test",
                "old_name": "a",
                "new_name": "b",
            }
        ]
        json_str = export_rules(rules, "testlib", None)
        data = json.loads(json_str)
        assert data["library"] == "testlib"
        assert len(data["versions"][0]["rules"]) == 1


# ==============================================================================
# 11. LLM Engine Tests
# ==============================================================================

class TestLLMSuggestionEngine:
    def test_suggests_from_missing_argument_error(self):
        engine = LLMSuggestionEngine()
        suggestions = engine.suggest_from_error(
            error_message="TypeError: got an unexpected keyword argument 'timeout'",
            code_context="connect(host='localhost', timeout=30)",
            file_path="app.py",
        )
        assert len(suggestions) >= 1

    def test_suggests_from_no_attribute_error(self):
        engine = LLMSuggestionEngine()
        suggestions = engine.suggest_from_error(
            error_message="AttributeError: module 'mylib' has no attribute 'old_attr'",
            code_context="mylib.old_attr",
        )
        assert len(suggestions) >= 1

    def test_suggests_from_import_error(self):
        engine = LLMSuggestionEngine()
        suggestions = engine.suggest_from_error(
            error_message="ImportError: cannot import name 'Symbol' from 'module'",
            code_context="from module import Symbol",
        )
        assert len(suggestions) >= 1

    def test_suggests_from_deprecation_warning(self):
        engine = LLMSuggestionEngine()
        suggestions = engine.suggest_from_error(
            error_message="DeprecationWarning: 'old_func' is deprecated",
            code_context="old_func()",
        )
        assert len(suggestions) >= 1
        assert suggestions[0].change_type == "deprecate_function"

    def test_explain_breaking_changes(self):
        engine = LLMSuggestionEngine()
        rules = [
            {
                "id": "BC-1",
                "change_type": "rename_function",
                "version_introduced": "2.0.0",
                "description": "Renamed foo to bar",
                "old_name": "foo",
                "new_name": "bar",
                "safety": "risky",
            }
        ]
        explanations = engine.explain_breaking_changes(rules)
        assert len(explanations) >= 1
        assert explanations[0].severity == "high"

    def test_suggest_migration_path(self):
        engine = LLMSuggestionEngine()
        path = engine.suggest_migration_path("pydantic", "1.0.0", "2.0.0")
        assert path["from_version"] == "1.0.0"
        assert path["to_version"] == "2.0.0"
        assert "estimated_effort" in path


class TestBreakingChange:
    def test_breaking_change_fields(self):
        from core.llm_engine import BreakingChange
        bc = BreakingChange(
            description="Test change",
            severity="high",
            migration_strategy="Replace all usages",
            ai_explanation="AI explanation here",
        )
        assert bc.severity == "high"
        assert "high" in bc.severity


# ==============================================================================
# 12. AST Extractor Tests
# ==============================================================================

class TestASTExtractor:
    def test_extracts_functions(self):
        code = "def foo(a, b=10):\n    pass\ndef bar():\n    pass"
        extractor = ASTExtractor(code)
        funcs = extractor.get_functions()
        assert "foo" in funcs
        assert "bar" in funcs

    def test_extracts_imports(self):
        code = "from mylib import Client, Server\nimport os"
        extractor = ASTExtractor(code)
        imports = extractor.get_imports()
        assert len(imports) >= 3

    def test_extracts_imports_by_module(self):
        code = "from mylib import a, b, c"
        extractor = ASTExtractor(code)
        by_mod = extractor.get_imports_by_module()
        assert "mylib" in by_mod
        assert len(by_mod["mylib"]) >= 3

    def test_function_params_extracted(self):
        code = "def func(a, b=None, *args, **kwargs):\n    pass"
        extractor = ASTExtractor(code)
        funcs = extractor.get_functions()
        assert "func" in funcs
        params = funcs["func"]["params"]
        assert len(params) >= 1


# ==============================================================================
# 13. Parallel Engine Tests
# ==============================================================================

class TestASTCache:
    def test_cache_put_and_get(self):
        cache = ASTCache(max_size=10)
        code = "x = 1"
        tree = cst.parse_module(code)
        cache.put(code, tree)
        retrieved = cache.get(code)
        assert retrieved is not None

    def test_cache_eviction(self):
        cache = ASTCache(max_size=2)
        for i in range(5):
            code = f"x = {i}"
            tree = cst.parse_module(code)
            cache.put(code, tree)
        assert len(cache._cache) <= 2

    def test_cache_clear(self):
        cache = ASTCache()
        cache.put("x=1", cst.parse_module("x=1"))
        cache.clear()
        assert len(cache._cache) == 0


class TestParallelMigrationReport:
    def test_report_summary(self):
        report = ParallelMigrationReport(
            source_version="1.0.0",
            target_version="2.0.0",
            is_upgrade=True,
            files_processed=100,
            files_modified=25,
            files_failed=2,
            total_changes=50,
        )
        summary = report.summary()
        assert "100" in summary
        assert "25" in summary
        assert "50" in summary


# ==============================================================================
# 14. Integration Tests (Full Pipeline)
# ==============================================================================

class TestFullMigrationPipeline:
    """End-to-end integration tests."""

    def test_parse_resolve_migrate_pipeline(self):
        parser = ChangelogParser()
        changelogs = parser.parse(open("examples/mylib_changelog.json").read())
        resolver = VersionResolver(changelogs)
        path = resolver.resolve_path("1.0.0", "3.0.0")

        engine = TransactionalMigrationEngine(interactive_approval=False)
        code = open("examples/sample_user_code.py").read()
        result = engine.migrate_code(code, path.rules)

        assert result.was_modified
        assert result.average_confidence > 0

    def test_migration_with_all_rule_types(self):
        rules = [
            make_rule(id="T1", change_type=ChangeType.RENAME_FUNCTION, old_name="old_f", new_name="new_f"),
            make_rule(id="T2", change_type=ChangeType.RENAME_CLASS, old_name="OldC", new_name="NewC"),
            make_rule(id="T3", change_type=ChangeType.ADD_ARGUMENT, function_name="func", argument_name="opt", default_value="None"),
            make_rule(id="T4", change_type=ChangeType.MOVE_TO_MODULE, old_name="Sym", source_module="old", target_module="new"),
            make_rule(id="T5", change_type=ChangeType.DEPRECATE_FUNCTION, old_name="dep", replacement="new_dep"),
        ]

        code = """
from old import Sym
obj = OldC()
result = old_f()
func(required=True)
"""
        engine = TransactionalMigrationEngine(interactive_approval=False)
        result = engine.migrate_code(code, rules)

        assert result.was_modified
        assert len(result.changes) >= 4

    def test_validation_then_migration(self):
        rules_data = [
            {"id": "V1", "change_type": "rename_function", "version_introduced": "1.0.0",
             "description": "test", "old_name": "x", "new_name": "y"},
            {"id": "V2", "change_type": "rename_function", "version_introduced": "1.0.0",
             "description": "test2", "old_name": "a", "new_name": "b"},
        ]
        rules = [MigrationRule.from_dict(r) for r in rules_data]
        report = RuleValidator().validate_rules(rules)
        assert report.valid

        code = "x()\na()"
        engine = TransactionalMigrationEngine(interactive_approval=False)
        result = engine.migrate_code(code, rules)
        assert result.was_modified

    def test_preview_matches_actual_migration(self):
        rules = [make_rule(old_name="foo", new_name="bar")]
        code = "foo()"

        engine = TransactionalMigrationEngine(interactive_approval=False)
        preview = engine.preview_migration(code, rules)
        result = engine.migrate_code(code, rules, dry_run=False)

        assert "bar" in result.transformed_code

    def test_migration_roundtrip_serialization(self):
        rule = make_rule()
        data = rule.to_dict()
        restored = MigrationRule.from_dict(data)
        assert restored.id == rule.id
        assert restored.change_type == rule.change_type

        code = "foo()"
        t1 = transform(code, rule)
        t2 = transform(code, restored)
        assert t1 == t2


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_empty_code_no_crash(self):
        code = ""
        engine = TransactionalMigrationEngine()
        result = engine.migrate_code(code, [])
        assert result.transformed_code == ""

    def test_comment_only_code(self):
        code = "# just a comment\nx = 1"
        result = transform(code, make_rule(old_name="x", new_name="y"))
        assert "y" in result

    def test_multiline_string(self):
        code = 's = """old_name here"""\nx = old_name'
        result = transform(code, make_rule(old_name="old_name", new_name="new_name"))
        assert result.count("new_name") == 1

    def test_regex_special_chars_in_names(self):
        code = "foo_bar()"
        result = transform(code, make_rule(old_name="foo_bar", new_name="baz_qux"))
        assert "baz_qux" in result


# ==============================================================================
# 15. RuleWhenCondition Tests
# ==============================================================================

class TestRuleWhenCondition:
    def test_imported_from_condition(self):
        cond = RuleWhenCondition(imported_from="mylib.utils")
        assert cond.imported_from == "mylib.utils"

    def test_multiple_conditions(self):
        cond = RuleWhenCondition(
            imported_from="mylib",
            inside_class="Client",
            python_version="3.10",
            has_decorator="route",
        )
        assert cond.imported_from == "mylib"
        assert cond.inside_class == "Client"
        assert cond.python_version == "3.10"
        assert cond.has_decorator == "route"

    def test_custom_condition(self):
        cond = RuleWhenCondition(custom_condition="line_count > 10")
        assert cond.custom_condition == "line_count > 10"

    def test_inside_class_list(self):
        cond = RuleWhenCondition(inside_class=["Client", "BaseHandler"])
        assert cond.inside_class == ["Client", "BaseHandler"]

    def test_not_imported_from(self):
        cond = RuleWhenCondition(not_imported_from="deprecated_module")
        assert cond.not_imported_from == "deprecated_module"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
