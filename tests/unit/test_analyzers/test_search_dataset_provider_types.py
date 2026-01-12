from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.search_dataset_provider_types import (
    SearchDatasetProviderTypesAnalyzer,
)
from cribl_hc.core.api_client import CriblAPIClient


class TestSearchDatasetProviderTypesAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SearchDatasetProviderTypesAnalyzer:
        return SearchDatasetProviderTypesAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_search_dataset_provider_types = AsyncMock(return_value={"items": [], "count": 0})
        return client

    def test_objective_name(self, analyzer: SearchDatasetProviderTypesAnalyzer) -> None:
        assert analyzer.objective_name == "search_dataset_provider_types"

    @pytest.mark.asyncio
    async def test_empty_provider_types(
        self, analyzer: SearchDatasetProviderTypesAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "search-provider-types-empty" for f in result.findings)
