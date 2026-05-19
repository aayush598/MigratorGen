"""Tests for MCP utility functions."""

from migrator_gen_mcp.utils.formatting import (
    format_breaking_changes,
    format_migration_result,
    format_validation_report,
)
from migrator_gen_mcp.utils.validators import validate_file_path, validate_rules_input, validate_version
from migrator_gen_mcp.exceptions import ValidationError


class TestFormatting:
    def test_format_breaking_changes_empty(self):
        result = format_breaking_changes([], [], [])
        assert "Breaking Changes Analysis" in result

    def test_format_breaking_changes_with_risky(self):
        result = format_breaking_changes(
            ["- [rename_function] break something"],
            ["- [deprecate_function] review me"],
            ["- [add_argument] safe change"],
        )
        assert "HIGH RISK" in result
        assert "REVIEW NEEDED" in result
        assert "SAFE" in result


class TestValidators:
    def test_validate_rules_input_valid(self):
        data = [{"change_type": "rename_function", "old_name": "foo", "new_name": "bar"}]
        result = validate_rules_input(data)
        assert result == data

    def test_validate_rules_input_empty(self):
        import pytest
        with pytest.raises(ValidationError, match="Missing required"):
            validate_rules_input(None)

    def test_validate_rules_input_empty_list(self):
        import pytest
        with pytest.raises(ValidationError, match="Missing required"):
            validate_rules_input([])

    def test_validate_rules_input_missing_change_type(self):
        import pytest
        with pytest.raises(ValidationError, match="change_type"):
            validate_rules_input([{"old_name": "foo"}])

    def test_validate_file_path_missing(self):
        import pytest
        with pytest.raises(ValidationError, match="Missing required"):
            validate_file_path(None)

    def test_validate_file_path_nonexistent(self):
        import pytest
        with pytest.raises(ValidationError, match="File not found"):
            validate_file_path("/nonexistent/file.py")

    def test_validate_version_missing(self):
        import pytest
        with pytest.raises(ValidationError, match="Missing required"):
            validate_version(None)

    def test_validate_version_invalid(self):
        import pytest
        with pytest.raises(ValidationError, match="Invalid version"):
            validate_version("abc")

    def test_validate_version_valid(self):
        result = validate_version("1.2.3")
        assert result == "1.2.3"
