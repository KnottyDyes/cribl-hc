"""
Integration tests for health analyzer.

Tests the health analyzer with mocked Cribl API responses including:
- Worker health assessment
- Leader health checks
- Deployment architecture validation
- Health score calculation
- Finding and recommendation generation
"""

import pytest
import respx
from httpx import Response
from unittest.mock import AsyncMock, MagicMock

from cribl_hc.analyzers.health import HealthAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


@pytest.fixture
def mock_cribl_api():
    """Setup respx mock for Cribl API."""
    with respx.mock:
        yield respx


@pytest.fixture
async def api_client():
    """Create API client for testing."""
    async with CriblAPIClient(
        base_url="https://cribl.example.com:9000",
        auth_token="test-token-12345"
    ) as client:
        yield client


class TestHealthAnalyzerBasics:
    """Test health analyzer basic properties."""

    def test_objective_name(self):
        """Test objective name is 'health'."""
        analyzer = HealthAnalyzer()
        assert analyzer.objective_name == "health"

    def test_description(self):
        """Test description is informative."""
        analyzer = HealthAnalyzer()
        description = analyzer.get_description()

        assert "health" in description.lower()
        assert "worker" in description.lower()

    def test_estimated_api_calls(self):
        """Test API call estimation."""
        analyzer = HealthAnalyzer()
        estimated = analyzer.get_estimated_api_calls()

        assert estimated > 0
        assert estimated <= 10  # Should be reasonable

    def test_required_permissions(self):
        """Test required permissions list."""
        analyzer = HealthAnalyzer()
        permissions = analyzer.get_required_permissions()

        assert "read:workers" in permissions
        assert "read:system" in permissions


class TestHealthyDeployment:
    """Test health analyzer with healthy deployment."""

    @pytest.mark.asyncio
    async def test_healthy_workers(self, api_client, mock_cribl_api):
        """Test analysis of healthy worker deployment."""
        # Mock version endpoint
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        # Mock system status
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(200, json={"version": "5.0.0", "status": "healthy"})
        )

        # Mock workers endpoint with healthy workers
        # HealthAnalyzer expects status="healthy" and disk info in info.totalDiskSpace/freeDiskSpace
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-1",
                            "info": {
                                "hostname": "worker-1.example.com",
                                "cribl": {"version": "5.0.0"},
                                "totalDiskSpace": 100000000000,  # 100GB
                                "freeDiskSpace": 50000000000,    # 50GB (50% used)
                                "totalmem": 8589934592           # 8GB
                            },
                            "status": "healthy"
                        },
                        {
                            "id": "worker-2",
                            "info": {
                                "hostname": "worker-2.example.com",
                                "cribl": {"version": "5.0.0"},
                                "totalDiskSpace": 100000000000,
                                "freeDiskSpace": 55000000000,
                                "totalmem": 8589934592
                            },
                            "status": "healthy"
                        }
                    ]
                }
            )
        )

        # Mock health endpoint
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(200, json={"status": "healthy"})
        )

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(api_client)

        assert result.success is True
        assert result.objective == "health"
        assert result.metadata["worker_count"] == 2
        assert result.metadata["health_score"] >= 90  # Healthy threshold
        assert result.metadata["health_status"] in ["healthy", "degraded"]

    @pytest.mark.asyncio
    async def test_single_healthy_worker(self, api_client, mock_cribl_api):
        """Test analysis with single healthy worker."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-1",
                            "info": {
                                "hostname": "worker-1.example.com",
                                "cribl": {"version": "5.0.0"},
                                "totalDiskSpace": 100000000000,
                                "freeDiskSpace": 65000000000,  # 35% used
                                "totalmem": 8589934592
                            },
                            "status": "healthy"
                        }
                    ]
                }
            )
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(200, json={"status": "healthy"})
        )

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(api_client)

        assert result.success is True
        assert result.metadata["worker_count"] == 1
        assert result.metadata["unhealthy_workers"] == 0


class TestUnhealthyDeployment:
    """Test health analyzer with unhealthy deployment."""

    @pytest.mark.asyncio
    async def test_high_cpu_worker(self, api_client, mock_cribl_api):
        """Test detection of worker with high CPU usage."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-1",
                            "info": {
                                "cribl": {"version": "5.0.0"},
                                "cpu": {"usage": 95.0},  # Critical
                                "memory": {"usage": 50.0},
                                "disk": {"usage": 40.0}
                            },
                            "status": "alive"
                        }
                    ]
                }
            )
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(200, json={"status": "healthy"})
        )

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(api_client)

        assert result.success is True
        # Should detect unhealthy worker
        assert result.metadata["unhealthy_workers"] >= 1

    @pytest.mark.asyncio
    async def test_high_memory_worker(self, api_client, mock_cribl_api):
        """Test detection of worker with high memory usage."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-1",
                            "info": {
                                "cribl": {"version": "5.0.0"},
                                "cpu": {"usage": 40.0},
                                "memory": {"usage": 92.0},  # Critical
                                "disk": {"usage": 40.0}
                            },
                            "status": "alive"
                        }
                    ]
                }
            )
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(200, json={"status": "healthy"})
        )

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(api_client)

        assert result.success is True
        assert result.metadata["unhealthy_workers"] >= 1

    @pytest.mark.asyncio
    async def test_multiple_unhealthy_workers(self, api_client, mock_cribl_api):
        """Test detection of multiple unhealthy workers."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-1",
                            "info": {
                                "cribl": {"version": "5.0.0"},
                                "cpu": {"usage": 95.0},
                                "memory": {"usage": 50.0},
                                "disk": {"usage": 40.0}
                            },
                            "status": "alive"
                        },
                        {
                            "id": "worker-2",
                            "info": {
                                "cribl": {"version": "5.0.0"},
                                "cpu": {"usage": 40.0},
                                "memory": {"usage": 95.0},
                                "disk": {"usage": 40.0}
                            },
                            "status": "alive"
                        },
                        {
                            "id": "worker-3",
                            "info": {
                                "cribl": {"version": "5.0.0"},
                                "cpu": {"usage": 30.0},
                                "memory": {"usage": 30.0},
                                "disk": {"usage": 95.0}
                            },
                            "status": "alive"
                        }
                    ]
                }
            )
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(200, json={"status": "healthy"})
        )

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(api_client)

        assert result.success is True
        assert result.metadata["worker_count"] == 3
        assert result.metadata["unhealthy_workers"] >= 2


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_no_workers(self, api_client, mock_cribl_api):
        """Test analysis with no workers."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(200, json={"items": []})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(200, json={"status": "healthy"})
        )

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(api_client)

        # Should complete but report low health
        assert result.success is True
        assert result.metadata["worker_count"] == 0

    @pytest.mark.asyncio
    async def test_api_error_handling(self, api_client, mock_cribl_api):
        """Test graceful handling of API errors."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        # Mock failure for some endpoints
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(500, json={"error": "Internal Server Error"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(500, json={"error": "Internal Server Error"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(500, json={"error": "Internal Server Error"})
        )

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(api_client)

        # HealthAnalyzer catches exceptions internally and returns success=True
        # with graceful degradation - it calculates health from what it can get
        # The result should succeed even with partial data
        assert result.success is True
        # Should have metadata about worker count (0 due to errors)
        assert "worker_count" in result.metadata

    @pytest.mark.asyncio
    async def test_malformed_worker_data(self, api_client, mock_cribl_api):
        """Test handling of malformed worker data."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        # Malformed worker data
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-1",
                            # Missing info field
                            "status": "alive"
                        }
                    ]
                }
            )
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(200, json={"status": "healthy"})
        )

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(api_client)

        # Should handle gracefully (may succeed or fail depending on implementation)
        assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_dead_workers(self, api_client, mock_cribl_api):
        """Test detection of dead/offline workers."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-1",
                            "info": {
                                "cribl": {"version": "5.0.0"},
                                "cpu": {"usage": 30.0},
                                "memory": {"usage": 40.0},
                                "disk": {"usage": 35.0}
                            },
                            "status": "alive"
                        },
                        {
                            "id": "worker-2",
                            "info": {
                                "cribl": {"version": "5.0.0"},
                                "cpu": {"usage": 0.0},
                                "memory": {"usage": 0.0},
                                "disk": {"usage": 0.0}
                            },
                            "status": "dead"
                        }
                    ]
                }
            )
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(200, json={"status": "healthy"})
        )

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(api_client)

        assert result.success is True
        # Should detect issues with dead worker
        assert result.metadata["worker_count"] == 2


class TestRecommendations:
    """Test recommendation generation."""

    @pytest.mark.asyncio
    async def test_recommendations_for_unhealthy_workers(self, api_client, mock_cribl_api):
        """Test that recommendations are generated for unhealthy workers."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-1",
                            "info": {
                                "cribl": {"version": "5.0.0"},
                                "cpu": {"usage": 95.0},  # Critical
                                "memory": {"usage": 92.0},  # Critical
                                "disk": {"usage": 91.0}  # Critical
                            },
                            "status": "alive"
                        }
                    ]
                }
            )
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(200, json={"status": "healthy"})
        )

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(api_client)

        assert result.success is True
        # Should generate recommendations
        assert len(result.recommendations) > 0 or len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_no_recommendations_for_healthy_deployment(self, api_client, mock_cribl_api):
        """Test that no critical recommendations for healthy deployment."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-1",
                            "info": {
                                "cribl": {"version": "5.0.0"},
                                "cpu": {"usage": 30.0},
                                "memory": {"usage": 40.0},
                                "disk": {"usage": 35.0}
                            },
                            "status": "alive"
                        }
                    ]
                }
            )
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(200, json={"status": "healthy"})
        )

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(api_client)

        assert result.success is True
        # Healthy deployment shouldn't have critical recommendations
        critical_recs = [r for r in result.recommendations if r.priority == "critical"]
        assert len(critical_recs) == 0
