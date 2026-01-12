from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.search_healthcheck import SearchHealthcheckAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSearchHealthcheckAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SearchHealthcheckAnalyzer:
        return SearchHealthcheckAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_search_healthcheck = AsyncMock(
            return_value={
                "items": [{"status": "red", "reported_at": 1, "reason": "FAIL"}],
                "count": 1,
            }
        )
        return client

    def test_objective_name(self, analyzer: SearchHealthcheckAnalyzer) -> None:
        assert analyzer.objective_name == "search_healthcheck"

    @pytest.mark.asyncio
    async def test_red_status(
        self, analyzer: SearchHealthcheckAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "search-healthcheck-red" for f in result.findings)
