import pytest

from migrator_gen import ChangeType, Rule, SDKConfig
from migrator_gen import exceptions as exc
from migrator_gen.services.remote_service import SyncRemoteService


class TestSyncRemoteService:
    def _make_client(self) -> SyncRemoteService:
        return SyncRemoteService(SDKConfig.build(mode="remote", base_url="http://test:8000", max_retries=1))

    def test_init(self):
        client = self._make_client()
        assert client._base_url == "http://test:8000"
        client.close()

    def test_connection_error(self):
        client = self._make_client()
        with pytest.raises(exc.APIError):
            client.list_libraries()
        client.close()

    def test_migrate_code_payload(self):
        client = self._make_client()
        rules = [Rule(id="R1", change_type=ChangeType.RENAME_FUNCTION, description="test", old_name="foo", new_name="bar")]
        with pytest.raises(Exception):
            client.migrate_code("def foo(): pass", rules)
        client.close()
