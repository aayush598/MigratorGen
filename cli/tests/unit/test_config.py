"""Tests for CLI configuration."""

from cli.config.settings import CLISettings
from cli.config.loader import load_settings


class TestCLISettings:
    def test_defaults(self):
        s = CLISettings()
        assert s.backup_suffix == ".bak"
        assert s.max_preview_lines == 80
        assert s.progress_spinner is True

    def test_custom_values(self):
        s = CLISettings(backup_suffix=".orig", max_preview_lines=50)
        assert s.backup_suffix == ".orig"
        assert s.max_preview_lines == 50


class TestLoadSettings:
    def test_no_config_returns_defaults(self):
        s = load_settings(None)
        assert isinstance(s, CLISettings)
        assert s.backup_suffix == ".bak"

    def test_nonexistent_config_returns_defaults(self):
        s = load_settings("/nonexistent/config.toml")
        assert isinstance(s, CLISettings)
