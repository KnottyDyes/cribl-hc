"""
Unit tests for SearchHealthAnalyzer.

Tests search job health monitoring, dataset availability checks,
and dashboard/saved search analysis.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from cribl_hc.analyzers.search_health import SearchHealthAnalyzer


@pytest.fixture
def mock_client():
    """Create a mock Cribl API client."""
    client = AsyncMock()
    client.product_type = "search"
    client.is_edge = False
    client.base_url = "https://test.cribl.cloud"
    return client


@pytest.fixture
def analyzer():
    """Create SearchHealthAnalyzer instance."""
    return SearchHealthAnalyzer()


class TestSearchHealthAnalyzer:
    """Tests for SearchHealthAnalyzer."""

    def test_objective_name(self, analyzer):
        """Test analyzer returns correct objective name."""
        assert analyzer.objective_name == "search"

    def test_estimated_api_calls(self, analyzer):
        """Test API call estimation."""
        # jobs(1) + datasets(1) + dashboards(1) + saved(1) = 4
        assert analyzer.get_estimated_api_calls() == 4

    @pytest.mark.asyncio
    async def test_analyze_with_healthy_resources(self, analyzer, mock_client):
        """Test analyzer with all search resources healthy."""
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-001",
                    "status": "completed",
                    "query": "cribl dataset='logs' | count"
                }
            ],
            "count": 1
        }
        mock_client.get_search_datasets.return_value = {
            "items": [
                {
                    "id": "cribl_logs",
                    "provider": "cribl_lake",
                    "enabled": True
                }
            ],
            "count": 1
        }
        mock_client.get_search_dashboards.return_value = {
            "items": [
                {
                    "id": "dash-001",
                    "name": "Operations",
                    "elements": [{"id": "elem-001", "type": "chart"}]
                }
            ],
            "count": 1
        }
        mock_client.get_search_saved_searches.return_value = {
            "items": [
                {
                    "id": "saved-001",
                    "name": "Error Query",
                    "query": "cribl dataset='logs' | where level='error'"
                }
            ],
            "count": 1
        }

        result = await analyzer.analyze(mock_client)

        assert result.objective == "search"
        assert result.success is True
        assert result.metadata["total_jobs"] == 1
        assert result.metadata["total_datasets"] == 1
        assert result.metadata["total_dashboards"] == 1
        assert result.metadata["total_saved_searches"] == 1

    @pytest.mark.asyncio
    async def test_analyze_detects_failed_jobs(self, analyzer, mock_client):
        """Test analyzer detects failed search jobs."""
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-failed",
                    "status": "failed",
                    "query": "invalid query syntax",
                    "error": "Query parse error: unexpected token"
                }
            ],
            "count": 1
        }
        mock_client.get_search_datasets.return_value = {"items": [], "count": 0}
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}
        mock_client.get_search_saved_searches.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["failed_jobs"] == 1
        # Should have high severity finding for failed job
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) > 0
        assert any("failed" in f.title.lower() for f in high_findings)

    @pytest.mark.asyncio
    async def test_analyze_detects_long_running_jobs(self, analyzer, mock_client):
        """Test analyzer detects long-running search jobs."""
        # Job started 10 minutes ago (600 seconds > 300 threshold)
        start_time = datetime.utcnow() - timedelta(minutes=10)
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-long",
                    "status": "running",
                    "query": "cribl dataset='logs' | count",
                    "timeStarted": int(start_time.timestamp() * 1000)
                }
            ],
            "count": 1
        }
        mock_client.get_search_datasets.return_value = {"items": [], "count": 0}
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}
        mock_client.get_search_saved_searches.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["running_jobs"] == 1
        # Should have medium severity finding for long-running job
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        assert len(medium_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_detects_stuck_jobs(self, analyzer, mock_client):
        """Test analyzer detects potentially stuck jobs (>15 minutes)."""
        # Job started 20 minutes ago (1200 seconds > 900 threshold)
        start_time = datetime.utcnow() - timedelta(minutes=20)
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-stuck",
                    "status": "running",
                    "query": "cribl dataset='logs' | some complex query",
                    "timeStarted": int(start_time.timestamp() * 1000)
                }
            ],
            "count": 1
        }
        mock_client.get_search_datasets.return_value = {"items": [], "count": 0}
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}
        mock_client.get_search_saved_searches.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should have high severity finding for stuck job
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) > 0
        assert any("stuck" in f.title.lower() for f in high_findings)
        # Should have recommendation to optimize or cancel
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_analyze_detects_high_cpu_jobs(self, analyzer, mock_client):
        """Test analyzer detects jobs with high CPU usage."""
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-cpu",
                    "status": "completed",
                    "query": "cribl dataset='logs' | expensive query",
                    "cpuMetrics": {
                        "totalCPUSeconds": 400.0,
                        "billableCPUSeconds": 350.0,
                        "executorsCPUSeconds": 300.0
                    }
                }
            ],
            "count": 1
        }
        mock_client.get_search_datasets.return_value = {"items": [], "count": 0}
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}
        mock_client.get_search_saved_searches.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should have high severity finding for very high CPU
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) > 0
        assert any("cpu" in f.title.lower() for f in high_findings)
        # Should have optimization recommendation
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_analyze_detects_disabled_datasets(self, analyzer, mock_client):
        """Test analyzer detects disabled datasets."""
        mock_client.get_search_jobs.return_value = {"items": [], "count": 0}
        mock_client.get_search_datasets.return_value = {
            "items": [
                {"id": "enabled_ds", "provider": "cribl_lake", "enabled": True},
                {"id": "disabled_ds", "provider": "cribl_lake", "enabled": False}
            ],
            "count": 2
        }
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}
        mock_client.get_search_saved_searches.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["enabled_datasets"] == 1
        # Should have low severity finding for disabled datasets
        low_findings = [f for f in result.findings if f.severity == "low"]
        assert len(low_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_detects_empty_dashboards(self, analyzer, mock_client):
        """Test analyzer detects dashboards without elements."""
        mock_client.get_search_jobs.return_value = {"items": [], "count": 0}
        mock_client.get_search_datasets.return_value = {"items": [], "count": 0}
        mock_client.get_search_dashboards.return_value = {
            "items": [
                {"id": "empty_dash", "name": "Empty Dashboard", "elements": []},
                {"id": "full_dash", "name": "Full Dashboard", "elements": [{"id": "e1"}]}
            ],
            "count": 2
        }
        mock_client.get_search_saved_searches.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should have info finding for empty dashboards
        info_findings = [f for f in result.findings if f.severity == "info"]
        assert len(info_findings) > 0
        assert any("empty" in f.title.lower() for f in info_findings)

    @pytest.mark.asyncio
    async def test_analyze_handles_empty_resources(self, analyzer, mock_client):
        """Test analyzer handles no search resources gracefully."""
        mock_client.get_search_jobs.return_value = {"items": [], "count": 0}
        mock_client.get_search_datasets.return_value = {"items": [], "count": 0}
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}
        mock_client.get_search_saved_searches.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_jobs"] == 0
        # Should have info finding about no resources
        info_findings = [f for f in result.findings if f.severity == "info"]
        assert len(info_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_handles_api_errors(self, analyzer, mock_client):
        """Test analyzer handles API errors gracefully."""
        mock_client.get_search_jobs.side_effect = Exception("API connection failed")

        result = await analyzer.analyze(mock_client)

        assert result.success is False
        assert "error" in result.metadata
        # Should have critical error finding
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        assert len(critical_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_detects_saved_searches_without_query(self, analyzer, mock_client):
        """Test analyzer detects saved searches without query."""
        mock_client.get_search_jobs.return_value = {"items": [], "count": 0}
        mock_client.get_search_datasets.return_value = {"items": [], "count": 0}
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}
        mock_client.get_search_saved_searches.return_value = {
            "items": [
                {"id": "valid_saved", "name": "Valid", "query": "cribl | count"},
                {"id": "invalid_saved", "name": "Invalid", "query": None}
            ],
            "count": 2
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should have low severity finding for invalid saved searches
        low_findings = [f for f in result.findings if f.severity == "low"]
        assert len(low_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_tracks_scheduled_dashboards(self, analyzer, mock_client):
        """Test analyzer tracks dashboards with schedules."""
        mock_client.get_search_jobs.return_value = {"items": [], "count": 0}
        mock_client.get_search_datasets.return_value = {"items": [], "count": 0}
        mock_client.get_search_dashboards.return_value = {
            "items": [
                {
                    "id": "scheduled_dash",
                    "name": "Scheduled",
                    "elements": [{"id": "e1"}],
                    "schedule": {"enabled": True, "cron": "0 * * * *"}
                },
                {
                    "id": "unscheduled_dash",
                    "name": "Unscheduled",
                    "elements": [{"id": "e2"}]
                }
            ],
            "count": 2
        }
        mock_client.get_search_saved_searches.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["scheduled_dashboards"] == 1
