from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.system_user_info import SystemUserInfoAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSystemUserInfoAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SystemUserInfoAnalyzer:
        return SystemUserInfoAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_users = AsyncMock(
            return_value=[
                {"id": "u1", "roles": []},
                {"id": "u2", "roles": ["admin"]},
            ]
        )
        client.get_roles = AsyncMock(return_value=[{"id": "admin"}])
        return client

    def test_objective_name(self, analyzer: SystemUserInfoAnalyzer) -> None:
        assert analyzer.objective_name == "system_user_info"

    @pytest.mark.asyncio
    async def test_users_without_roles(
        self, analyzer: SystemUserInfoAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "system-users-no-roles" for f in result.findings)
