from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.search_dataset_providers import SearchDatasetProvidersAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSearchDatasetProvidersAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SearchDatasetProvidersAnalyzer:
        return SearchDatasetProvidersAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_search_dataset_providers = AsyncMock(
            return_value={"items": [{"id": "prov-1"}, {"id": "prov-2"}], "count": 2}
        )
        client.get_search_datasets = AsyncMock(
            return_value={
                "items": [
                    {"id": "ds-1", "provider": "prov-1"},
                    {"id": "ds-2", "provider": "custom-1"},
                ],
                "count": 2,
            }
        )
        return client

    def test_objective_name(self, analyzer: SearchDatasetProvidersAnalyzer) -> None:
        assert analyzer.objective_name == "search_dataset_providers"

    @pytest.mark.asyncio
    async def test_unused_and_unknown_providers(
        self, analyzer: SearchDatasetProvidersAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any("search-provider-unused" in f.id for f in result.findings)
        assert any("search-provider-missing" in f.id for f in result.findings)
