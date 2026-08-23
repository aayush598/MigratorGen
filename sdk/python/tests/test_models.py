import pytest
from pydantic import ValidationError

from migrator_gen import (
    ChangeType,
    DiffPreview,
    EngineMode,
    MigrateResponse,
    MigrationStatus,
    Rule,
    SafetyLevel,
    ValidationReport,
    VersionChangelog,
)


class TestRuleValidation:
    def test_requires_id(self):
        with pytest.raises(ValidationError):
            Rule(change_type=ChangeType.RENAME_FUNCTION, description="test")

    def test_requires_change_type(self):
        with pytest.raises(ValidationError):
            Rule(id="R1", description="test")

    def test_minimal_valid(self):
        rule = Rule(id="R1", change_type=ChangeType.RENAME_FUNCTION, description="test")
        assert rule.id == "R1"

    def test_with_all_fields(self, sample_rule):
        assert sample_rule.old_name == "old_func"
        assert sample_rule.new_name == "new_func"

    def test_to_dict_excludes_none(self):
        rule = Rule(id="R1", change_type=ChangeType.RENAME_FUNCTION, description="test")
        assert "old_name" not in rule.to_dict()

    def test_from_dict_roundtrip(self):
        original = Rule(
            id="R1",
            change_type=ChangeType.RENAME_FUNCTION,
            description="test",
            old_name="foo",
            new_name="bar",
        )
        restored = Rule.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.old_name == "foo"

    def test_invalid_change_type(self):
        with pytest.raises(ValidationError):
            Rule(id="R1", change_type="invalid", description="test")


class TestChangeTypeEnum:
    def test_values(self):
        assert ChangeType.RENAME_FUNCTION.value == "rename_function"
        assert ChangeType.RENAME_CLASS.value == "rename_class"

    def test_all_have_values(self):
        for ct in ChangeType:
            assert ct.value


class TestSafetyLevel:
    def test_values(self):
        assert SafetyLevel.SAFE.value == "safe"
        assert SafetyLevel.RISKY.value == "risky"


class TestEngineMode:
    def test_values(self):
        assert EngineMode.AUTO.value == "auto"
        assert EngineMode.LOCAL.value == "local"
        assert EngineMode.REMOTE.value == "remote"


class TestVersionChangelog:
    def test_empty_rules(self):
        assert VersionChangelog(version="1.0.0").rules == []

    def test_with_rules(self, sample_changelog):
        assert sample_changelog.version == "2.0.0"
        assert len(sample_changelog.rules) == 1


class TestMigrateResponse:
    def test_default(self):
        resp = MigrateResponse()
        assert resp.transformed_code == ""
        assert resp.was_modified is False

    def test_with_values(self):
        resp = MigrateResponse(
            original_code="foo()",
            transformed_code="bar()",
            was_modified=True,
            average_confidence=0.95,
        )
        assert resp.transformed_code == "bar()"


class TestDiffPreview:
    def test_default(self):
        assert DiffPreview().diff == ""

    def test_with_diff(self):
        dp = DiffPreview(
            original_code="a", transformed_code="b", diff="--- a\n+++ b\n", change_count=1
        )
        assert dp.change_count == 1


class TestValidationReport:
    def test_valid_default(self):
        assert ValidationReport().valid is True

    def test_counts(self):
        report = ValidationReport(
            errors=[{"rule_id": "R1", "message": "e1", "severity": "error"}],
            warnings=[{"rule_id": "R2", "message": "w1", "severity": "warning"}],
        )
        assert report.error_count == 1
        assert report.warning_count == 1


class TestMigrationStatus:
    def test_all(self):
        assert MigrationStatus.PENDING.value == "pending"
        assert MigrationStatus.RUNNING.value == "running"
        assert MigrationStatus.COMPLETED.value == "completed"
        assert MigrationStatus.FAILED.value == "failed"
