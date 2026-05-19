import pytest

from migrator_gen import MigrationClient, SDKConfig


class TestAsyncMigrationClient:
    @pytest.mark.asyncio
    async def test_remote_mode_with_base_url(self):
        client = MigrationClient(mode="remote", base_url="http://test:8000")
        async with client:
            assert client.mode == "remote"
            assert client.config.base_url == "http://test:8000"

    @pytest.mark.asyncio
    async def test_config_property(self):
        client = MigrationClient(mode="remote", base_url="http://test:8000")
        async with client:
            assert isinstance(client.config, SDKConfig)

    @pytest.mark.asyncio
    async def test_remote_detection_from_env(self, monkeypatch):
        monkeypatch.setenv("MIGRATOR_MODE", "remote")
        monkeypatch.setenv("MIGRATOR_BASE_URL", "https://env.api:8000")
        client = MigrationClient()
        async with client:
            assert client.mode == "remote"

    @pytest.mark.asyncio
    async def test_context_manager_closes(self):
        client = MigrationClient(mode="remote", base_url="http://test:8000")
        async with client:
            pass
