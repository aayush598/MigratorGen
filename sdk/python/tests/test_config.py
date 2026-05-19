
from migrator_gen import SDKConfig


class TestSDKConfigDefaults:
    def test_default_base_url(self):
        assert SDKConfig().base_url == "http://localhost:8000"

    def test_default_mode(self):
        assert SDKConfig().mode == "auto"

    def test_default_timeout(self):
        assert SDKConfig().timeout == 30

    def test_default_max_retries(self):
        assert SDKConfig().max_retries == 3

    def test_default_log_level(self):
        assert SDKConfig().log_level == "INFO"

    def test_api_key_none_by_default(self):
        assert SDKConfig().api_key is None


class TestSDKConfigBuild:
    def test_build_with_kwargs(self):
        config = SDKConfig.build(mode="remote", base_url="https://api.example.com", api_key="sk-test", timeout=60, max_retries=5)
        assert config.mode == "remote"
        assert config.base_url == "https://api.example.com"
        assert config.api_key == "sk-test"
        assert config.timeout == 60
        assert config.max_retries == 5

    def test_build_local_defaults(self):
        config = SDKConfig.local_defaults()
        assert config.mode == "local"
        assert config.base_url == ""

    def test_build_partial_overrides(self):
        config = SDKConfig.build(mode="local")
        assert config.mode == "local"
        assert config.base_url == "http://localhost:8000"


class TestSDKConfigEnvVars:
    def test_env_var_base_url(self, monkeypatch):
        monkeypatch.setenv("MIGRATOR_BASE_URL", "https://env.example.com")
        assert SDKConfig().base_url == "https://env.example.com"

    def test_env_var_api_key(self, monkeypatch):
        monkeypatch.setenv("MIGRATOR_API_KEY", "env-key-123")
        assert SDKConfig().api_key == "env-key-123"

    def test_env_var_timeout(self, monkeypatch):
        monkeypatch.setenv("MIGRATOR_TIMEOUT", "120")
        assert SDKConfig().timeout == 120

    def test_env_var_mode(self, monkeypatch):
        monkeypatch.setenv("MIGRATOR_MODE", "remote")
        assert SDKConfig().mode == "remote"

    def test_env_var_override_with_kwargs(self, monkeypatch):
        monkeypatch.setenv("MIGRATOR_BASE_URL", "https://env.example.com")
        config = SDKConfig.build(base_url="https://kwargs.example.com")
        assert config.base_url == "https://kwargs.example.com"


class TestSDKConfigSerialization:
    def test_to_dict(self):
        d = SDKConfig.build(mode="local").to_dict()
        assert d["mode"] == "local"

    def test_to_env(self):
        env = SDKConfig.build(mode="remote", api_key="test-key").to_env()
        assert env["MIGRATOR_MODE"] == "remote"
        assert env["MIGRATOR_API_KEY"] == "test-key"
