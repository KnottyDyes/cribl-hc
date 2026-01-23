"""
Unit tests for SearchUsageGroupsAnalyzer.
"""

from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.search_usage_groups import SearchUsageGroupsAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestSearchUsageGroupsAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SearchUsageGroupsAnalyzer:
        return SearchUsageGroupsAnalyzer()

    @pytest.fixture
    def mock_client(self) -> CriblAPIClient:
        client = AsyncMock(spec=CriblAPIClient)
        client.get_search_workspaces = AsyncMock(return_value=["main"])
        client.get_search_groups = AsyncMock(
            return_value={
                "items": [
                    {"id": "group-1", "datasets": ["ds-1"], "dashboards": []},
                    {"id": "group-2", "datasets": [], "dashboards": []},
                ],
                "count": 2,
            }
        )
        return client

    def test_objective_name(self, analyzer: SearchUsageGroupsAnalyzer) -> None:
        assert analyzer.objective_name == "search_usage_groups"

    def test_required_permissions(self, analyzer: SearchUsageGroupsAnalyzer) -> None:
        assert "read:search:groups" in analyzer.get_required_permissions()

    @pytest.mark.asyncio
    async def test_empty_group_detected(
        self, analyzer: SearchUsageGroupsAnalyzer, mock_client: CriblAPIClient
    ) -> None:
        result = await analyzer.analyze(mock_client)
        assert any(f.id == "search-groups-empty-main" for f in result.findings)
