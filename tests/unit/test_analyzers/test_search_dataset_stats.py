from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.search_dataset_stats import SearchDatasetStatsAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSearchDatasetStatsAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SearchDatasetStatsAnalyzer:
        return SearchDatasetStatsAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_search_datasets = AsyncMock(return_value={"items": [{"id": "ds-1"}], "count": 1})
        client.get_search_dataset_stats = AsyncMock(
            return_value={
                "byteCounts": [],
                "eventCounts": [],
                "maxEventTime": 0,
                "minEventTime": 0,
                "totalByteCount": 0,
                "totalEventCount": 0,
            }
        )
        client.get_search_dataset_usage_stats = AsyncMock(
            return_value={"queryCounts": [{"count": 0, "startTime": 0}], "topUsers": []}
        )
        return client

    def test_objective_name(self, analyzer: SearchDatasetStatsAnalyzer) -> None:
        assert analyzer.objective_name == "search_dataset_stats"

    @pytest.mark.asyncio
    async def test_zero_events(
        self, analyzer: SearchDatasetStatsAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any("search-dataset-no-events" in f.id for f in result.findings)
        assert any("search-dataset-unused" in f.id for f in result.findings)
