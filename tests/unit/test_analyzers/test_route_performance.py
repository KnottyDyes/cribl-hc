from typing import Optional
from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.route_performance import RoutePerformanceAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


def create_route(route_id: str, pipeline: str = "main", disabled: bool = False) -> dict:
    return {"id": route_id, "pipeline": pipeline, "disabled": disabled}


def create_route_metrics(
    route_id: str,
    events_in: int = 1000,
    events_out: int = 1000,
    errors: int = 0,
    latencies: Optional[list[float]] = None,
    processing_time_ms: float = 100.0,
) -> dict:
    if latencies is None:
        latencies = [10.0] * 10

    return {
        "in": {"events": events_in},
        "out": {"events": events_out},
        "errors": errors,
        "latencies": latencies,
        "processing_time_ms": processing_time_ms,
    }


def create_metrics_response(routes_data: dict) -> dict:
    return {"routes": routes_data}


class TestRoutePerformanceAnalyzer:
    """Test suite for RoutePerformanceAnalyzer."""

    @pytest.fixture
    def mock_client(self):
        client = AsyncMock(spec=CriblAPIClient)
        client.get_routes = AsyncMock(return_value=[])
        client.get_pipelines = AsyncMock(return_value=[])
        client.get_metrics = AsyncMock(return_value={})
        # Default worker group
        client.worker_group = "default"
        return client

    @pytest.mark.asyncio
    async def test_healthy_routes_no_findings(self, mock_client):
        """Test that healthy routes produce no findings."""
        routes = [create_route("route-1"), create_route("route-2")]

        metrics_data = {
            "route-1": create_route_metrics("route-1"),
            "route-2": create_route_metrics("route-2"),
        }

        mock_client.get_routes.return_value = routes
        mock_client.get_metrics.return_value = create_metrics_response(metrics_data)

        analyzer = RoutePerformanceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 0
        assert result.metadata["healthy_routes"] == 2
        assert result.metadata["critical_findings"] == 0

    @pytest.mark.asyncio
    async def test_zero_throughput_warning(self, mock_client):
        """Test that enabled route with zero throughput is flagged as LOW."""
        routes = [create_route("route-unused")]

        metrics_data = {
            "route-unused": create_route_metrics("route-unused", events_in=0, events_out=0)
        }

        mock_client.get_routes.return_value = routes
        mock_client.get_metrics.return_value = create_metrics_response(metrics_data)

        analyzer = RoutePerformanceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "low"
        assert "Zero Throughput" in finding.title

    @pytest.mark.asyncio
    async def test_high_p99_latency(self, mock_client):
        """Test that p99 latency > 5000ms is flagged as HIGH."""
        routes = [create_route("route-slow")]

        # Create latencies where p99 is > 5000ms
        # For 100 samples: p99 = index 98 (0-based), which means 99th value
        # So we need 98 low values, then high values for 99-100
        latencies = [100.0] * 98 + [6000.0, 6500.0]
        metrics_data = {"route-slow": create_route_metrics("route-slow", latencies=latencies)}

        mock_client.get_routes.return_value = routes
        mock_client.get_metrics.return_value = create_metrics_response(metrics_data)

        analyzer = RoutePerformanceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "high"
        assert "High Latency" in finding.title
        assert finding.metadata["p99_latency"] > 5000

    @pytest.mark.asyncio
    async def test_critical_p99_latency(self, mock_client):
        """Test that p99 latency > 10000ms is flagged as CRITICAL."""
        routes = [create_route("route-slow-crit")]

        # For 100 samples: p99 = index 98, so we need 98 low values + high values for 99-100
        latencies = [100.0] * 98 + [11000.0, 11500.0]
        metrics_data = {
            "route-slow-crit": create_route_metrics("route-slow-crit", latencies=latencies)
        }

        mock_client.get_routes.return_value = routes
        mock_client.get_metrics.return_value = create_metrics_response(metrics_data)

        analyzer = RoutePerformanceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "critical"
        assert finding.metadata["p99_latency"] > 10000

    @pytest.mark.asyncio
    async def test_error_rate_high(self, mock_client):
        """Test that error rate > 5% is flagged as HIGH."""
        routes = [create_route("route-err")]

        # 7% error rate: 70 errors / 1000 events
        metrics_data = {"route-err": create_route_metrics("route-err", events_in=1000, errors=70)}

        mock_client.get_routes.return_value = routes
        mock_client.get_metrics.return_value = create_metrics_response(metrics_data)

        analyzer = RoutePerformanceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "high"
        assert "High Error Rate" in finding.title
        assert round(finding.metadata["error_rate"], 1) == 7.0

    @pytest.mark.asyncio
    async def test_error_rate_critical(self, mock_client):
        """Test that error rate > 10% is flagged as CRITICAL."""
        routes = [create_route("route-err-crit")]

        # 12% error rate: 120 errors / 1000 events
        metrics_data = {
            "route-err-crit": create_route_metrics("route-err-crit", events_in=1000, errors=120)
        }

        mock_client.get_routes.return_value = routes
        mock_client.get_metrics.return_value = create_metrics_response(metrics_data)

        analyzer = RoutePerformanceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "critical"
        assert finding.metadata["error_rate"] == 12.0

    @pytest.mark.asyncio
    async def test_pipeline_overload_detection(self, mock_client):
        """Test that high volume (>5000 eps) to single pipeline is flagged as MEDIUM."""
        routes = [create_route("route-heavy", pipeline="pipe-1")]

        # 20 million events per hour -> ~5555 events/sec
        # 5555 > 5000 threshold
        high_eps_events = 20_000_000
        metrics_data = {
            "route-heavy": create_route_metrics("route-heavy", events_in=high_eps_events)
        }

        mock_client.get_routes.return_value = routes
        mock_client.get_pipelines.return_value = [{"id": "pipe-1"}]
        mock_client.get_metrics.return_value = create_metrics_response(metrics_data)

        analyzer = RoutePerformanceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "medium"
        assert "High Volume" in finding.title
        assert finding.metadata["throughput"] > 5000

    @pytest.mark.asyncio
    async def test_route_imbalance_detection(self, mock_client):
        """Test that imbalanced traffic distribution is flagged as MEDIUM."""
        routes = [create_route("route-huge"), create_route("route-tiny")]

        # Huge imbalance: one route has 10M events, other has 100
        # This will result in a high Coefficient of Variation (CV)
        metrics_data = {
            "route-huge": create_route_metrics("route-huge", events_in=10_000_000),
            "route-tiny": create_route_metrics("route-tiny", events_in=100),
        }

        mock_client.get_routes.return_value = routes
        mock_client.get_metrics.return_value = create_metrics_response(metrics_data)

        analyzer = RoutePerformanceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "medium"
        assert "Imbalanced" in finding.title
        assert finding.metadata["coefficient_of_variation"] > 0.5

    @pytest.mark.asyncio
    async def test_no_routes_available(self, mock_client):
        """Test behavior when no routes are configured."""
        mock_client.get_routes.return_value = []
        mock_client.get_metrics.return_value = create_metrics_response({})

        analyzer = RoutePerformanceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # One info finding about no routes
        assert len(result.findings) == 1
        assert result.findings[0].id == "route-perf-no-routes"

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_client):
        """Test graceful handling of API errors."""
        mock_client.get_routes.side_effect = Exception("API Failure")

        analyzer = RoutePerformanceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is False
        assert "API Failure" in result.metadata["error"]
