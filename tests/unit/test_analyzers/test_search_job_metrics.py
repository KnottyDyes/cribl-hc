from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.search_job_metrics import SearchJobMetricsAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSearchJobMetricsAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SearchJobMetricsAnalyzer:
        return SearchJobMetricsAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_search_job_metrics = AsyncMock(
            return_value={"items": [{"status": "error"}], "count": 1}
        )
        return client

    def test_objective_name(self, analyzer: SearchJobMetricsAnalyzer) -> None:
        assert analyzer.objective_name == "search_job_metrics"

    @pytest.mark.asyncio
    async def test_error_metrics(
        self, analyzer: SearchJobMetricsAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "search-job-metrics-errors" for f in result.findings)
