
from migrator_gen import SDKConfig, SyncMigrationClient


class TestSyncMigrationClientInit:
    def test_remote_mode_with_base_url(self):
        client = SyncMigrationClient(mode="remote", base_url="http://test:8000")
        assert client.mode == "remote"
        assert client.config.base_url == "http://test:8000"
        client.close()

    def test_context_manager(self):
        with SyncMigrationClient(mode="remote", base_url="http://test:8000") as c:
            assert c.config.base_url == "http://test:8000"

    def test_config_property(self):
        client = SyncMigrationClient(mode="remote", base_url="http://test:8000")
        assert isinstance(client.config, SDKConfig)
        client.close()

    def test_remote_detection_from_env(self, monkeypatch):
        monkeypatch.setenv("MIGRATOR_MODE", "remote")
        monkeypatch.setenv("MIGRATOR_BASE_URL", "https://env.api:8000")
        client = SyncMigrationClient()
        assert client.mode == "remote"
        client.close()

    def test_remote_mode_init_with_default_base(self):
        client = SyncMigrationClient(mode="remote")
        assert client.mode == "remote"
        assert client.config.base_url == "http://localhost:8000"
        client.close()
