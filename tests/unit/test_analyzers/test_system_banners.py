from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.system_banners import SystemBannersAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSystemBannersAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SystemBannersAnalyzer:
        return SystemBannersAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_banners = AsyncMock(
            return_value=[{"id": "banner-1", "enabled": True, "message": "Hello"}]
        )
        return client

    def test_objective_name(self, analyzer: SystemBannersAnalyzer) -> None:
        assert analyzer.objective_name == "system_banners"

    @pytest.mark.asyncio
    async def test_enabled_banner(
        self, analyzer: SystemBannersAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any("system-banner-enabled" in f.id for f in result.findings)
