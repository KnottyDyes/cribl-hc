from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.search_field_stats import SearchFieldStatsAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSearchFieldStatsAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SearchFieldStatsAnalyzer:
        return SearchFieldStatsAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_search_datasets = AsyncMock(return_value={"items": [{"id": "ds-1"}], "count": 1})
        client.get_search_field_stats = AsyncMock(
            return_value={
                "fieldStats": [
                    {"name": "foo", "nullCount": 10, "count": 10},
                    {"name": "bar", "nullCount": 0, "count": 10},
                ],
                "totalEvents": 10,
            }
        )
        return client

    def test_objective_name(self, analyzer: SearchFieldStatsAnalyzer) -> None:
        assert analyzer.objective_name == "search_field_stats"

    @pytest.mark.asyncio
    async def test_null_fields_detected(
        self, analyzer: SearchFieldStatsAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any("search-field-always-null" in f.id for f in result.findings)
