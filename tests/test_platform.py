"""
Tests for MigratorGen platform.
Run with: python -m pytest tests/ -v
"""

import pytest
import json
import libcst as cst
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.changelog_parser import (
    ChangelogParser, MigrationRule, ChangeType, VersionChangelog
)
from core.version_resolver import VersionResolver
from core.migration_engine import MigrationEngine
from core.transformers import (
    RenameFunctionTransformer, RenameClassTransformer,
    RenameAttributeTransformer, RenameImportTransformer,
    AddArgumentTransformer, RemoveArgumentTransformer,
    MoveToModuleTransformer, ReplaceWithPropertyTransformer,
    DeprecateFunctionTransformer, AddDecoratorTransformer,
)


# ---- Helpers ----

def make_rule(**kwargs) -> MigrationRule:
    defaults = {
        "change_type": ChangeType.RENAME_FUNCTION,
        "version_introduced": "2.0.0",
        "description": "Test rule",
    }
    defaults.update(kwargs)
    return MigrationRule(**defaults)


def transform(code: str, transformer) -> str:
    tree = cst.parse_module(code)
    new_tree = tree.visit(transformer)
    return new_tree.code


# ---- Changelog Parser Tests ----

class TestChangelogParser:
    def test_parse_json_changelog(self):
        data = json.dumps({
            "library": "mylib",
            "versions": [
                {
                    "version": "2.0.0",
                    "release_date": "2024-01-01",
                    "rules": [
                        {
                            "change_type": "rename_function",
                            "version_introduced": "2.0.0",
                            "description": "Renamed foo to bar",
                            "old_name": "foo",
                            "new_name": "bar",
                        }
                    ]
                }
            ]
        })
        parser = ChangelogParser()
        changelogs = parser.parse(data, fmt="json")
        assert len(changelogs) == 1
        assert changelogs[0].version == "2.0.0"
        assert len(changelogs[0].rules) == 1
        assert changelogs[0].rules[0].old_name == "foo"
        assert changelogs[0].rules[0].new_name == "bar"



    def test_version_sorting(self):
        from core.changelog_parser import _version_key
        versions = ["1.10.0", "2.0.0", "1.9.0", "1.2.1"]
        sorted_v = sorted(versions, key=_version_key)
        assert sorted_v == ["1.2.1", "1.9.0", "1.10.0", "2.0.0"]

    def test_merge_changelogs(self):
        parser = ChangelogParser()
        old = [VersionChangelog("1.0.0", None), VersionChangelog("2.0.0", None)]
        new = [VersionChangelog("1.0.0", None), VersionChangelog("2.0.0", None), VersionChangelog("3.0.0", None)]
        merged = parser.merge_changelogs(old, new)
        assert len(merged) == 1
        assert merged[0].version == "3.0.0"


# ---- Version Resolver Tests ----

class TestVersionResolver:
    def _make_changelogs(self):
        versions = ["1.0.0", "1.5.0", "2.0.0", "2.5.0", "3.0.0"]
        changelogs = []
        for v in versions:
            rule = make_rule(
                change_type=ChangeType.RENAME_FUNCTION,
                version_introduced=v,
                old_name=f"func_v{v.replace('.', '_')}",
                new_name=f"new_func_v{v.replace('.', '_')}",
            )
            vc = VersionChangelog(version=v, release_date=None, rules=[rule])
            changelogs.append(vc)
        return changelogs

    def test_upgrade_path(self):
        changelogs = self._make_changelogs()
        resolver = VersionResolver(changelogs)
        path = resolver.resolve_path("1.0.0", "3.0.0")
        assert path.is_upgrade is True
        assert len(path.rules) == 4  # 1.5, 2.0, 2.5, 3.0

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


# ---- Transformer Tests ----

class TestRenameFunctionTransformer:
    def test_renames_function_call(self):
        code = "result = old_func(x, y)"
        rule = make_rule(old_name="old_func", new_name="new_func")
        transformer = RenameFunctionTransformer(rule)
        new_code = transform(code, transformer)
        assert "new_func" in new_code
        assert "old_func" not in new_code

    def test_renames_function_def(self):
        code = "def old_func(x):\n    return x"
        rule = make_rule(old_name="old_func", new_name="new_func")
        transformer = RenameFunctionTransformer(rule)
        new_code = transform(code, transformer)
        assert "def new_func" in new_code

    def test_no_change_for_different_name(self):
        code = "result = other_func(x)"
        rule = make_rule(old_name="old_func", new_name="new_func")
        transformer = RenameFunctionTransformer(rule)
        new_code = transform(code, transformer)
        assert new_code == code


class TestRenameImportTransformer:
    def test_renames_from_import(self):
        code = "from mylib import OldClass"
        rule = make_rule(
            change_type=ChangeType.RENAME_IMPORT,
            old_name="OldClass",
            new_name="NewClass",
            old_module="mylib",
            new_module="mylib.new",
        )
        transformer = RenameImportTransformer(rule)
        new_code = transform(code, transformer)
        assert "NewClass" in new_code
        assert "mylib.new" in new_code

    def test_no_change_wrong_module(self):
        code = "from otherlib import OldClass"
        rule = make_rule(
            change_type=ChangeType.RENAME_IMPORT,
            old_name="OldClass",
            new_name="NewClass",
            old_module="mylib",
            new_module="mylib.new",
        )
        transformer = RenameImportTransformer(rule)
        new_code = transform(code, transformer)
        assert new_code == code


class TestAddArgumentTransformer:
    def test_adds_argument(self):
        code = "result = connect(host='localhost')"
        rule = make_rule(
            change_type=ChangeType.ADD_ARGUMENT,
            function_name="connect",
            argument_name="timeout",
            default_value="30",
        )
        transformer = AddArgumentTransformer(rule)
        new_code = transform(code, transformer)
        assert "timeout=30" in new_code

    def test_does_not_duplicate_argument(self):
        code = "result = connect(host='localhost', timeout=10)"
        rule = make_rule(
            change_type=ChangeType.ADD_ARGUMENT,
            function_name="connect",
            argument_name="timeout",
            default_value="30",
        )
        transformer = AddArgumentTransformer(rule)
        new_code = transform(code, transformer)
        assert new_code.count("timeout") == 1


class TestRemoveArgumentTransformer:
    def test_removes_argument(self):
        code = "send_request(url, verbose=True)"
        rule = make_rule(
            change_type=ChangeType.REMOVE_ARGUMENT,
            function_name="send_request",
            argument_name="verbose",
        )
        transformer = RemoveArgumentTransformer(rule)
        new_code = transform(code, transformer)
        assert "verbose" not in new_code


class TestRenameAttributeTransformer:
    def test_renames_attribute(self):
        code = "x = obj.old_attr"
        rule = make_rule(
            change_type=ChangeType.RENAME_ATTRIBUTE,
            old_name="old_attr",
            new_name="new_attr",
        )
        transformer = RenameAttributeTransformer(rule)
        new_code = transform(code, transformer)
        assert "obj.new_attr" in new_code

    def test_does_not_rename_standalone_name(self):
        code = "old_attr = 5"
        rule = make_rule(
            change_type=ChangeType.RENAME_ATTRIBUTE,
            old_name="old_attr",
            new_name="new_attr",
        )
        transformer = RenameAttributeTransformer(rule)
        new_code = transform(code, transformer)
        # Should NOT change standalone name, only attribute access
        assert "old_attr" in new_code  # standalone stays


class TestMoveToModuleTransformer:
    def test_moves_import(self):
        code = "from mylib.old import MyClass"
        rule = make_rule(
            change_type=ChangeType.MOVE_TO_MODULE,
            old_name="MyClass",
            source_module="mylib.old",
            target_module="mylib.new",
        )
        transformer = MoveToModuleTransformer(rule)
        new_code = transform(code, transformer)
        assert "mylib.new" in new_code


class TestReplaceWithPropertyTransformer:
    def test_replaces_call_with_property(self):
        code = "name = obj.get_name()"
        rule = make_rule(
            change_type=ChangeType.REPLACE_WITH_PROPERTY,
            old_name="get_name",
            new_name="name",
        )
        transformer = ReplaceWithPropertyTransformer(rule)
        new_code = transform(code, transformer)
        assert "obj.name" in new_code
        assert "()" not in new_code


class TestAddDecoratorTransformer:
    def test_adds_decorator(self):
        code = "def on_response(data):\n    pass\n"
        rule = make_rule(
            change_type=ChangeType.ADD_DECORATOR,
            function_name="on_response",
            decorator_name="handler",
        )
        transformer = AddDecoratorTransformer(rule)
        new_code = transform(code, transformer)
        assert "@handler" in new_code

    def test_no_duplicate_decorator(self):
        code = "@handler\ndef on_response(data):\n    pass\n"
        rule = make_rule(
            change_type=ChangeType.ADD_DECORATOR,
            function_name="on_response",
            decorator_name="handler",
        )
        transformer = AddDecoratorTransformer(rule)
        new_code = transform(code, transformer)
        assert new_code.count("@handler") == 1


# ---- Migration Engine Tests ----

class TestMigrationEngine:
    def test_apply_multiple_rules(self):
        code = "from mylib import Client\nclient = Client()\nconn = connect()\n"
        rules = [
            make_rule(
                change_type=ChangeType.RENAME_CLASS,
                old_name="Client",
                new_name="APIClient",
            ),
            make_rule(
                change_type=ChangeType.RENAME_FUNCTION,
                old_name="connect",
                new_name="create_connection",
            ),
        ]
        engine = MigrationEngine()
        result = engine.migrate_code(code, rules)
        assert "APIClient" in result.transformed_code
        assert "create_connection" in result.transformed_code
        assert result.was_modified is True
        assert len(result.changes) >= 2  # Client renamed in import + usage, plus connect()

    def test_dry_run_no_modification(self):
        code = "old_func()\n"
        rules = [make_rule(old_name="old_func", new_name="new_func")]
        engine = MigrationEngine()
        result = engine.migrate_code(code, rules, dry_run=True)
        assert result.transformed_code == code  # no change in dry run

    def test_validates_syntax(self):
        original = "def foo():\n    pass\n"
        migrated = "def bar():\n    pass\n"
        engine = MigrationEngine()
        valid, issues = engine.validate_migration(original, migrated)
        assert valid is True

    def test_invalid_syntax_detected(self):
        engine = MigrationEngine()
        valid, issues = engine.validate_migration("def foo(): pass", "def bar(: pass")
        assert valid is False

    def test_preview_shows_diff(self):
        code = "result = old_func()\n"
        rules = [make_rule(old_name="old_func", new_name="new_func")]
        engine = MigrationEngine()
        preview = engine.preview_migration(code, rules)
        assert "new_func" in preview or "old_func" in preview


# ---- Migration Rule Serialization Tests ----

class TestMigrationRuleSerialization:
    def test_roundtrip_serialization(self):
        rule = MigrationRule(
            change_type=ChangeType.RENAME_FUNCTION,
            version_introduced="2.0.0",
            description="Test",
            old_name="foo",
            new_name="bar",
        )
        data = rule.to_dict()
        restored = MigrationRule.from_dict(data)
        assert restored.change_type == rule.change_type
        assert restored.old_name == rule.old_name
        assert restored.new_name == rule.new_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])