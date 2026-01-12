from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.system_settings import SystemSettingsAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSystemSettingsAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SystemSettingsAnalyzer:
        return SystemSettingsAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_system_settings = AsyncMock(return_value={"items": [], "count": 0})
        return client

    def test_objective_name(self, analyzer: SystemSettingsAnalyzer) -> None:
        assert analyzer.objective_name == "system_settings"

    @pytest.mark.asyncio
    async def test_no_settings(
        self, analyzer: SystemSettingsAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "system-settings-none" for f in result.findings)
