"""
Unit tests for SearchWorkspaceOptimizationAnalyzer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from cribl_hc.analyzers.search_workspace_optimization import (
    SearchWorkspaceOptimizationAnalyzer,
    SavedSearchInfo,
    DashboardInfo,
    DatasetInfo,
)
from cribl_hc.core.api_client import CriblAPIClient


class TestSearchWorkspaceOptimizationAnalyzer:
    """Test SearchWorkspaceOptimizationAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return SearchWorkspaceOptimizationAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = AsyncMock(spec=CriblAPIClient)
        return client

    def test_objective_name(self, analyzer):
        """Test analyzer objective name."""
        assert analyzer.objective_name == "search-workspace-optimization"

    def test_supported_products(self, analyzer):
        """Test supported products."""
        assert analyzer.supported_products == ["search"]

    def test_required_permissions(self, analyzer):
        """Test required permissions."""
        expected = [
            "read:search",
            "read:datasets",
            "read:dashboards",
            "read:saved-searches",
            "read:audit",
        ]
        assert analyzer.get_required_permissions() == expected

    @pytest.mark.asyncio
    async def test_analyze_no_assets(self, analyzer, mock_client):
        """Test analysis with no search assets."""
        # Mock empty responses
        mock_client.get.side_effect = [
            {"items": []},  # saved-searches
            {"items": []},  # dashboards
            {"items": []},  # datasets
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        assert "No Search Assets Found" in result.findings[0].title

    @pytest.mark.asyncio
    async def test_analyze_wildcard_searches(self, analyzer, mock_client):
        """Test detection of wildcard dataset searches."""
        searches_data = {
            "items": [
                {
                    "id": "search1",
                    "name": "Wildcard Search",
                    "query": "search *",
                    "dataset": "*",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "executionCount": 100,
                }
            ]
        }

        mock_client.get.side_effect = [
            searches_data,  # saved-searches
            {"items": []},  # dashboards
            {"items": []},  # datasets
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) >= 1
        # Should find wildcard dataset issue

    @pytest.mark.asyncio
    async def test_analyze_unused_expensive_searches(self, analyzer, mock_client):
        """Test detection of unused expensive searches."""
        searches_data = {
            "items": [
                {
                    "id": "expensive_search",
                    "name": "Expensive Search",
                    "query": "search all data",
                    "dataset": "large_dataset",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "lastExecuted": (datetime.now() - timedelta(days=40)).isoformat(),
                    "executionCount": 5,
                    "estimatedCostPerMonth": 150.0,
                }
            ]
        }

        mock_client.get.side_effect = [
            searches_data,  # saved-searches
            {"items": []},  # dashboards
            {"items": []},  # datasets
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        assert len(medium_findings) >= 1
        # Should find unused expensive search

    @pytest.mark.asyncio
    async def test_analyze_high_cost_low_usage(self, analyzer, mock_client):
        """Test detection of high-cost, low-usage searches."""
        searches_data = {
            "items": [
                {
                    "id": "high_cost_search",
                    "name": "High Cost Search",
                    "query": "complex query",
                    "dataset": "dataset1",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "executionCount": 2,
                    "estimatedCostPerMonth": 200.0,
                }
            ]
        }

        mock_client.get.side_effect = [
            searches_data,  # saved-searches
            {"items": []},  # dashboards
            {"items": []},  # datasets
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) >= 1
        # Should find high-cost, low-usage search

    @pytest.mark.asyncio
    async def test_analyze_wildcard_dashboards(self, analyzer, mock_client):
        """Test detection of dashboards with wildcard queries."""
        dashboards_data = {
            "items": [
                {
                    "id": "dashboard1",
                    "name": "Wildcard Dashboard",
                    "panels": [
                        {"query": "search *"},
                        {"query": "search dataset1"},
                        {"query": "search ?"},
                    ],
                    "accessCount": 50,
                }
            ]
        }

        mock_client.get.side_effect = [
            {"items": []},  # saved-searches
            dashboards_data,  # dashboards
            {"items": []},  # datasets
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        assert len(medium_findings) >= 1
        # Should find dashboard with wildcard queries

    @pytest.mark.asyncio
    async def test_analyze_unused_dashboards(self, analyzer, mock_client):
        """Test detection of unused dashboards."""
        old_date = (datetime.now() - timedelta(days=70)).isoformat()
        dashboards_data = {
            "items": [
                {
                    "id": "old_dashboard",
                    "name": "Old Dashboard",
                    "panels": [{"query": "search dataset1"}],
                    "lastAccessed": old_date,
                    "accessCount": 1,
                }
            ]
        }

        mock_client.get.side_effect = [
            {"items": []},  # saved-searches
            dashboards_data,  # dashboards
            {"items": []},  # datasets
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        low_findings = [f for f in result.findings if f.severity == "low"]
        assert len(low_findings) >= 1
        # Should find unused dashboard

    @pytest.mark.asyncio
    async def test_analyze_unused_datasets(self, analyzer, mock_client):
        """Test detection of unused datasets."""
        datasets_data = {
            "items": [
                {
                    "name": "unused_dataset",
                    "type": "index",
                    "sizeBytes": 1000000,
                    "lastAccessed": (datetime.now() - timedelta(days=40)).isoformat(),
                    "accessCount": 0,
                    "queryCount": 0,
                }
            ]
        }

        mock_client.get.side_effect = [
            {"items": []},  # saved-searches
            {"items": []},  # dashboards
            datasets_data,  # datasets
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        assert len(medium_findings) >= 1
        # Should find unused dataset

    @pytest.mark.asyncio
    async def test_analyze_duplicate_names(self, analyzer, mock_client):
        """Test detection of duplicate asset names."""
        searches_data = {
            "items": [
                {
                    "id": "search1",
                    "name": "Common Query",
                    "query": "search data",
                    "dataset": "dataset1",
                },
                {
                    "id": "search2",
                    "name": "Common Query",
                    "query": "search data",
                    "dataset": "dataset2",
                },
            ]
        }

        dashboards_data = {
            "items": [{"id": "dash1", "name": "Common Query", "panels": [], "accessCount": 10}]
        }

        mock_client.get.side_effect = [
            searches_data,  # saved-searches
            dashboards_data,  # dashboards
            {"items": []},  # datasets
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        assert len(medium_findings) >= 1
        # Should find duplicate names

    @pytest.mark.asyncio
    async def test_analyze_high_cost_workspace(self, analyzer, mock_client):
        """Test high-cost workspace analysis."""
        searches_data = {
            "items": [
                {"id": "s1", "name": "Search 1", "estimatedCostPerMonth": 200.0},
                {"id": "s2", "name": "Search 2", "estimatedCostPerMonth": 300.0},
                {"id": "s3", "name": "Search 3", "estimatedCostPerMonth": 600.0},
            ]
        }

        mock_client.get.side_effect = [
            searches_data,  # saved-searches
            {"items": []},  # dashboards
            {"items": []},  # datasets
            {"items": []},  # audit
        ]

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) >= 1
        # Should find high search cost workspace

    def test_saved_search_properties(self):
        """Test SavedSearchInfo property methods."""
        wildcard_search = SavedSearchInfo(
            id="test", name="Wildcard Search", query="search *", dataset="*"
        )

        assert wildcard_search.is_wildcard_dataset is True

        specific_search = SavedSearchInfo(
            id="test2", name="Specific Search", query="search data", dataset="dataset1"
        )

        assert specific_search.is_wildcard_dataset is False

        # Test days since last run
        old_date = datetime.now() - timedelta(days=10)
        search_with_history = SavedSearchInfo(
            id="test3", name="Old Search", query="search old", dataset="dataset1", last_run=old_date
        )

        assert search_with_history.days_since_last_run == 10

    def test_dashboard_properties(self):
        """Test DashboardInfo property methods."""
        dashboard = DashboardInfo(
            id="test",
            name="Test Dashboard",
            queries=["search dataset1", "search dataset2", "search *"],
        )

        assert dashboard.total_queries == 3
        assert dashboard.has_wildcard_queries is True

        clean_dashboard = DashboardInfo(
            id="test2", name="Clean Dashboard", queries=["search dataset1", "search dataset2"]
        )

        assert clean_dashboard.has_wildcard_queries is False

    def test_dataset_properties(self):
        """Test DatasetInfo property methods."""
        unused_dataset = DatasetInfo(
            name="unused",
            type="index",
            access_count=0,
            query_count=0,
            last_accessed=datetime.now() - timedelta(days=50),
        )

        assert unused_dataset.is_unused is True

        used_dataset = DatasetInfo(name="used", type="index", access_count=10, query_count=5)

        assert used_dataset.is_unused is False
