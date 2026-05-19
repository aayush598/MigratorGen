"""Tests for CLI services."""

from pathlib import Path

from cli.services.config_service import load_config


class TestConfigService:
    def test_load_config_nonexistent(self):
        result = load_config("/nonexistent/path.toml")
        assert result == {}

    def test_load_config_not_toml(self, tmp_path: Path):
        f = tmp_path / "config.txt"
        f.write_text("not toml")
        result = load_config(str(f))
        assert result == {}
