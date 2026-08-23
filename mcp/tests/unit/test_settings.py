"""Tests for MCP settings and config loader."""

from pathlib import Path

from migrator_gen_mcp.config.loader import load_settings
from migrator_gen_mcp.config.settings import MCPSettings
from migrator_gen_mcp.exceptions import ConfigError


class TestMCPSettings:
    def test_defaults(self):
        s = MCPSettings()
        assert s.host == "0.0.0.0"
        assert s.port == 8001
        assert s.transport == "stdio"
        assert s.log_level == "INFO"

    def test_custom_values(self):
        s = MCPSettings(host="127.0.0.1", port=9000, transport="http")
        assert s.host == "127.0.0.1"
        assert s.port == 9000
        assert s.transport == "http"

    def test_port_validation(self):
        import pytest

        with pytest.raises(Exception):
            MCPSettings(port=99999)


class TestLoadSettings:
    def test_no_config_returns_defaults(self):
        s = load_settings()
        assert isinstance(s, MCPSettings)
        assert s.host == "0.0.0.0"

    def test_nonexistent_config_raises(self):
        import pytest

        with pytest.raises(ConfigError):
            load_settings("/nonexistent/config.toml")

    def test_config_file_loaded(self, tmp_path: Path):
        config = tmp_path / "mcp.toml"
        config.write_text("""[mcp]
host = "127.0.0.1"
port = 9000
transport = "http"
""")
        s = load_settings(str(config))
        assert s.host == "127.0.0.1"
        assert s.port == 9000
        assert s.transport == "http"
