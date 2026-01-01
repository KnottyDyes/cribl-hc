"""
Unit tests for SearchPerformanceAnalyzer.

Tests CPU cost analysis, query efficiency, dashboard analysis, and optimization recommendations.
"""

import pytest
from unittest.mock import AsyncMock

from cribl_hc.analyzers.search_performance import SearchPerformanceAnalyzer


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
    """Create SearchPerformanceAnalyzer instance."""
    return SearchPerformanceAnalyzer()


class TestSearchPerformanceAnalyzer:
    """Tests for SearchPerformanceAnalyzer."""

    def test_objective_name(self, analyzer):
        """Test analyzer returns correct objective name."""
        assert analyzer.objective_name == "search"

    def test_estimated_api_calls(self, analyzer):
        """Test API call estimation."""
        # jobs(1) + dashboards(1) = 2
        assert analyzer.get_estimated_api_calls() == 2

    @pytest.mark.asyncio
    async def test_analyze_with_efficient_queries(self, analyzer, mock_client):
        """Test analyzer with efficient queries (low CPU usage)."""
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-001",
                    "status": "completed",
                    "query": "cribl dataset='logs' | count",
                    "cpuMetrics": {
                        "totalCPUSeconds": 5.0,
                        "billableCPUSeconds": 4.0,
                        "executorsCPUSeconds": 3.0
                    }
                }
            ],
            "count": 1
        }
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.objective == "search"
        assert result.success is True
        assert result.metadata["completed_jobs_with_metrics"] == 1
        assert result.metadata["total_billable_cpu_seconds"] == 4.0
        # No high CPU findings for efficient queries
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) == 0

    @pytest.mark.asyncio
    async def test_analyze_detects_very_high_cpu(self, analyzer, mock_client):
        """Test analyzer detects very high CPU usage (>5 min)."""
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-expensive",
                    "status": "completed",
                    "query": "cribl dataset='*' | expensive operation",
                    "cpuMetrics": {
                        "totalCPUSeconds": 400.0,
                        "billableCPUSeconds": 350.0,
                        "executorsCPUSeconds": 300.0
                    }
                }
            ],
            "count": 1
        }
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["very_high_cpu_jobs"] == 1
        # Should have high severity finding
        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) > 0
        assert any("very high cpu" in f.title.lower() for f in high_findings)

    @pytest.mark.asyncio
    async def test_analyze_detects_high_cpu(self, analyzer, mock_client):
        """Test analyzer detects high CPU usage (>1 min)."""
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-high",
                    "status": "completed",
                    "query": "cribl dataset='logs' | heavy aggregation",
                    "cpuMetrics": {
                        "totalCPUSeconds": 100.0,
                        "billableCPUSeconds": 80.0,
                        "executorsCPUSeconds": 70.0
                    }
                }
            ],
            "count": 1
        }
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["high_cpu_jobs"] == 1
        # Should have medium severity finding
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        assert len(medium_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_detects_inefficient_queries(self, analyzer, mock_client):
        """Test analyzer detects inefficient queries (low billable/total ratio)."""
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-inefficient",
                    "status": "completed",
                    "query": "cribl dataset='logs' | inefficient query",
                    "cpuMetrics": {
                        "totalCPUSeconds": 100.0,
                        "billableCPUSeconds": 20.0,  # Only 20% efficiency
                        "executorsCPUSeconds": 80.0
                    }
                }
            ],
            "count": 1
        }
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["inefficient_jobs"] == 1
        # Should have medium severity finding for inefficiency
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        assert any("inefficient" in f.title.lower() for f in medium_findings)

    @pytest.mark.asyncio
    async def test_analyze_detects_wildcard_datasets(self, analyzer, mock_client):
        """Test analyzer detects wildcard dataset usage."""
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-wildcard",
                    "status": "completed",
                    "query": "cribl dataset='*' | count",
                    "cpuMetrics": {
                        "totalCPUSeconds": 50.0,
                        "billableCPUSeconds": 40.0,
                        "executorsCPUSeconds": 35.0
                    }
                }
            ],
            "count": 1
        }
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should have finding for wildcard usage
        wildcard_findings = [f for f in result.findings if "wildcard" in f.title.lower()]
        assert len(wildcard_findings) > 0
        # Should have recommendation to avoid wildcards
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_analyze_adds_cost_summary_for_high_total(self, analyzer, mock_client):
        """Test analyzer adds cost summary recommendation for high total CPU."""
        # Multiple jobs totaling >600 CPU seconds
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-1",
                    "status": "completed",
                    "query": "cribl dataset='logs' | query1",
                    "cpuMetrics": {
                        "totalCPUSeconds": 300.0,
                        "billableCPUSeconds": 250.0,
                        "executorsCPUSeconds": 200.0
                    }
                },
                {
                    "id": "job-2",
                    "status": "completed",
                    "query": "cribl dataset='logs' | query2",
                    "cpuMetrics": {
                        "totalCPUSeconds": 400.0,
                        "billableCPUSeconds": 350.0,
                        "executorsCPUSeconds": 300.0
                    }
                },
                {
                    "id": "job-3",
                    "status": "completed",
                    "query": "cribl dataset='logs' | query3",
                    "cpuMetrics": {
                        "totalCPUSeconds": 100.0,
                        "billableCPUSeconds": 80.0,
                        "executorsCPUSeconds": 70.0
                    }
                }
            ],
            "count": 3
        }
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_billable_cpu_seconds"] == 680.0
        # Should have cost optimization recommendation
        cost_recs = [r for r in result.recommendations if "cost" in r.title.lower() or "cpu" in r.title.lower()]
        assert len(cost_recs) > 0

    @pytest.mark.asyncio
    async def test_analyze_handles_empty_jobs(self, analyzer, mock_client):
        """Test analyzer handles no completed jobs gracefully."""
        mock_client.get_search_jobs.return_value = {"items": [], "count": 0}
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["completed_jobs_with_metrics"] == 0
        # Should have info finding
        info_findings = [f for f in result.findings if f.severity == "info"]
        assert len(info_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_handles_jobs_without_metrics(self, analyzer, mock_client):
        """Test analyzer handles jobs without CPU metrics."""
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-no-metrics",
                    "status": "completed",
                    "query": "cribl dataset='logs' | count"
                    # No cpuMetrics
                }
            ],
            "count": 1
        }
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["completed_jobs_with_metrics"] == 0

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
    async def test_analyze_calculates_efficiency_ratio(self, analyzer, mock_client):
        """Test analyzer correctly calculates efficiency ratio."""
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-1",
                    "status": "completed",
                    "query": "cribl dataset='logs' | count",
                    "cpuMetrics": {
                        "totalCPUSeconds": 100.0,
                        "billableCPUSeconds": 80.0,
                        "executorsCPUSeconds": 70.0
                    }
                }
            ],
            "count": 1
        }
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["efficiency_ratio"] == 0.8  # 80/100 = 0.8

    @pytest.mark.asyncio
    async def test_analyze_skips_running_jobs(self, analyzer, mock_client):
        """Test analyzer only analyzes completed jobs."""
        mock_client.get_search_jobs.return_value = {
            "items": [
                {
                    "id": "job-running",
                    "status": "running",
                    "query": "cribl dataset='logs' | count",
                    "cpuMetrics": {
                        "totalCPUSeconds": 50.0,
                        "billableCPUSeconds": 40.0,
                        "executorsCPUSeconds": 35.0
                    }
                },
                {
                    "id": "job-completed",
                    "status": "completed",
                    "query": "cribl dataset='logs' | count",
                    "cpuMetrics": {
                        "totalCPUSeconds": 10.0,
                        "billableCPUSeconds": 8.0,
                        "executorsCPUSeconds": 7.0
                    }
                }
            ],
            "count": 2
        }
        mock_client.get_search_dashboards.return_value = {"items": [], "count": 0}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_jobs_analyzed"] == 2
        assert result.metadata["completed_jobs_with_metrics"] == 1
        assert result.metadata["total_billable_cpu_seconds"] == 8.0  # Only from completed job

    @pytest.mark.asyncio
    async def test_analyze_detects_dashboard_wildcards(self, analyzer, mock_client):
        """Test analyzer detects wildcard dataset usage in dashboards."""
        mock_client.get_search_jobs.return_value = {"items": [], "count": 0}
        mock_client.get_search_dashboards.return_value = {
            "items": [
                {
                    "id": "dash-wildcard",
                    "name": "All Data Dashboard",
                    "elements": [
                        {
                            "id": "elem-1",
                            "type": "chart",
                            "query": "cribl dataset='*' | count by source"
                        }
                    ]
                }
            ],
            "count": 1
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["dashboards_with_wildcards"] == 1
        # Should have finding for dashboard wildcards
        wildcard_findings = [f for f in result.findings if "dashboard" in f.title.lower() and "wildcard" in f.title.lower()]
        assert len(wildcard_findings) > 0
        # Should have recommendation
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_analyze_tracks_dashboard_elements(self, analyzer, mock_client):
        """Test analyzer counts dashboard elements analyzed."""
        mock_client.get_search_jobs.return_value = {"items": [], "count": 0}
        mock_client.get_search_dashboards.return_value = {
            "items": [
                {
                    "id": "dash-1",
                    "name": "Dashboard 1",
                    "elements": [
                        {"id": "e1", "type": "chart", "query": "cribl dataset='logs' | count"},
                        {"id": "e2", "type": "table", "query": "cribl dataset='logs' | head 10"}
                    ]
                },
                {
                    "id": "dash-2",
                    "name": "Dashboard 2",
                    "elements": [
                        {"id": "e3", "type": "chart", "query": "cribl dataset='metrics' | count"}
                    ]
                }
            ],
            "count": 2
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_dashboards"] == 2
        assert result.metadata["dashboard_elements_analyzed"] == 3

    @pytest.mark.asyncio
    async def test_analyze_ignores_dashboards_without_elements(self, analyzer, mock_client):
        """Test analyzer handles dashboards without elements."""
        mock_client.get_search_jobs.return_value = {"items": [], "count": 0}
        mock_client.get_search_dashboards.return_value = {
            "items": [
                {
                    "id": "dash-empty",
                    "name": "Empty Dashboard",
                    "elements": []
                }
            ],
            "count": 1
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_dashboards"] == 1
        assert result.metadata["dashboard_elements_analyzed"] == 0
