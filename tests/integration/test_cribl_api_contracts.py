"""
Contract tests for Cribl API endpoints.

Tests that validate the cribl-hc API client correctly handles Cribl API responses
according to expected schemas for:
- System endpoints (/api/v1/system/*)
- Worker endpoints (/api/v1/master/workers)
- Metrics endpoints (/api/v1/metrics)
- Health endpoints (/api/v1/health)
- Version endpoints (/api/v1/version)

These tests use respx to mock realistic Cribl API responses.
"""

import pytest
import respx
from httpx import Response

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


class TestVersionEndpoint:
    """Test /api/v1/version endpoint contract."""

    @pytest.mark.asyncio
    async def test_version_endpoint_structure(self, api_client, mock_cribl_api):
        """Test version endpoint returns expected schema."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(
                200,
                json={
                    "version": "5.0.0",
                    "build": "abcd1234",
                    "buildDate": "2024-01-15T10:30:00Z"
                }
            )
        )

        result = await api_client.test_connection()

        assert result.success is True
        assert result.cribl_version == "5.0.0"
        assert result.response_time_ms is not None
        assert result.response_time_ms > 0

    @pytest.mark.asyncio
    async def test_version_endpoint_minimal_response(self, api_client, mock_cribl_api):
        """Test version endpoint with minimal valid response."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(
                200,
                json={"version": "4.5.3"}
            )
        )

        result = await api_client.test_connection()

        assert result.success is True
        assert result.cribl_version == "4.5.3"


class TestSystemEndpoints:
    """Test /api/v1/system/* endpoint contracts."""

    @pytest.mark.asyncio
    async def test_system_info_endpoint(self, api_client, mock_cribl_api):
        """Test system status endpoint returns expected fields."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(
                200,
                json={
                    "guid": "test-guid-12345",
                    "hostname": "cribl-leader-1",
                    "version": "5.0.0",
                    "product": "stream",
                    "uptime": 86400
                }
            )
        )

        result = await api_client.get_system_status()

        assert result is not None
        assert "version" in result

    @pytest.mark.asyncio
    async def test_system_status_endpoint(self, api_client, mock_cribl_api):
        """Test system status endpoint schema."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(
                200,
                json={
                    "version": "5.0.0",
                    "status": "healthy",
                    "workerCount": 10,
                    "cpuUsage": 45.2,
                    "memoryUsage": 60.5
                }
            )
        )

        result = await api_client.get_system_status()

        assert result is not None
        assert result["status"] == "healthy"
        assert "version" in result
        assert "workerCount" in result


class TestWorkerEndpoints:
    """Test /api/v1/master/workers endpoint contracts."""

    @pytest.mark.asyncio
    async def test_workers_list_structure(self, api_client, mock_cribl_api):
        """Test workers endpoint returns expected structure."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "count": 2,
                    "items": [
                        {
                            "id": "worker-1",
                            "guid": "worker-guid-1",
                            "info": {
                                "cribl": {
                                    "version": "5.0.0",
                                    "distMode": "worker"
                                },
                                "os": {
                                    "type": "Linux",
                                    "platform": "linux",
                                    "release": "5.15.0"
                                },
                                "cpu": {
                                    "usage": 45.2,
                                    "count": 4
                                },
                                "memory": {
                                    "usage": 60.5,
                                    "total": 16000000000
                                },
                                "disk": {
                                    "usage": 50.3,
                                    "total": 100000000000
                                }
                            },
                            "status": "alive",
                            "connectedSince": "2024-01-15T10:30:00Z",
                            "configVersion": 123
                        },
                        {
                            "id": "worker-2",
                            "guid": "worker-guid-2",
                            "info": {
                                "cribl": {
                                    "version": "5.0.0",
                                    "distMode": "worker"
                                },
                                "os": {"type": "Linux"},
                                "cpu": {"usage": 50.0},
                                "memory": {"usage": 55.0},
                                "disk": {"usage": 45.0}
                            },
                            "status": "alive"
                        }
                    ]
                }
            )
        )

        result = await api_client.get_workers()

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2

        # Verify worker structure
        worker = result[0]
        assert "id" in worker
        assert "info" in worker
        assert "status" in worker
        assert worker["status"] == "alive"

        # Verify worker info structure
        info = worker["info"]
        assert "cribl" in info
        assert "cpu" in info
        assert "memory" in info
        assert "disk" in info

    @pytest.mark.asyncio
    async def test_workers_empty_list(self, api_client, mock_cribl_api):
        """Test workers endpoint with no workers."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "count": 0,
                    "items": []
                }
            )
        )

        result = await api_client.get_workers()

        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_worker_dead_status(self, api_client, mock_cribl_api):
        """Test handling of dead worker status."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-dead",
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

        result = await api_client.get_workers()

        assert result is not None
        assert isinstance(result, list)
        assert result[0]["status"] == "dead"


class TestHealthEndpoint:
    """Test /api/v1/health endpoint contract."""

    @pytest.mark.asyncio
    async def test_health_endpoint_healthy(self, api_client, mock_cribl_api):
        """Test health endpoint with healthy status."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(
                200,
                json={
                    "status": "healthy",
                    "checks": {
                        "database": "ok",
                        "redis": "ok",
                        "workers": "ok"
                    },
                    "version": "5.0.0"
                }
            )
        )

        response = await api_client.get("/api/v1/health")
        result = response.json()

        assert result["status"] == "healthy"
        assert "checks" in result

    @pytest.mark.asyncio
    async def test_health_endpoint_unhealthy(self, api_client, mock_cribl_api):
        """Test health endpoint with unhealthy status."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/health").mock(
            return_value=Response(
                503,
                json={
                    "status": "unhealthy",
                    "checks": {
                        "database": "ok",
                        "redis": "error",
                        "workers": "degraded"
                    }
                }
            )
        )

        response = await api_client.get("/api/v1/health")

        # May return error or success depending on implementation
        assert response.status_code == 503


class TestMetricsEndpoint:
    """Test /api/v1/metrics endpoint contract."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_structure(self, api_client, mock_cribl_api):
        """Test metrics endpoint returns expected structure."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/metrics").mock(
            return_value=Response(
                200,
                json={
                    "timestamp": "2024-01-15T10:30:00Z",
                    "cpu_usage": 45.2,
                    "memory_usage": 60.5,
                    "disk_usage": 50.3,
                    "network": {
                        "bytes_in": 1000000,
                        "bytes_out": 800000
                    },
                    "events": {
                        "in": 10000,
                        "out": 9500,
                        "dropped": 50
                    }
                }
            )
        )

        result = await api_client.get_metrics()

        assert result is not None
        assert "cpu_usage" in result or "memory_usage" in result

    @pytest.mark.asyncio
    async def test_metrics_minimal_response(self, api_client, mock_cribl_api):
        """Test metrics with minimal valid response."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/metrics").mock(
            return_value=Response(
                200,
                json={
                    "cpu_usage": 30.0,
                    "memory_usage": 40.0
                }
            )
        )

        result = await api_client.get_metrics()

        assert result is not None
        assert result.get("cpu_usage") == 30.0
        assert result.get("memory_usage") == 40.0


class TestErrorResponses:
    """Test API client handles error responses correctly."""

    @pytest.mark.asyncio
    async def test_401_unauthorized(self, api_client, mock_cribl_api):
        """Test handling of 401 unauthorized response."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(
                401,
                json={"error": "Unauthorized", "message": "Invalid token"}
            )
        )

        result = await api_client.test_connection()

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_403_forbidden(self, api_client, mock_cribl_api):
        """Test handling of 403 forbidden response."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/status").mock(
            return_value=Response(
                403,
                json={"error": "Forbidden", "message": "Insufficient permissions"}
            )
        )

        # Should raise or return error depending on implementation
        try:
            result = await api_client.get_system_status()
            # If it doesn't raise, it should return some indication of error
            assert result is None or "error" in str(result).lower()
        except Exception as e:
            # Expected to potentially raise
            assert "403" in str(e) or "forbidden" in str(e).lower()

    @pytest.mark.asyncio
    async def test_404_not_found(self, api_client, mock_cribl_api):
        """Test handling of 404 not found response."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/nonexistent").mock(
            return_value=Response(
                404,
                json={"error": "Not Found"}
            )
        )

        try:
            response = await api_client.get("/api/v1/nonexistent")
            assert response.status_code == 404
        except Exception:
            # Expected to potentially raise
            pass

    @pytest.mark.asyncio
    async def test_500_internal_error(self, api_client, mock_cribl_api):
        """Test handling of 500 internal server error."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(
                500,
                json={"error": "Internal Server Error"}
            )
        )

        result = await api_client.test_connection()

        # Should handle error gracefully
        assert result.success is False or result.error is not None

    @pytest.mark.asyncio
    async def test_503_service_unavailable(self, api_client, mock_cribl_api):
        """Test handling of 503 service unavailable."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(
                503,
                json={"error": "Service Unavailable"}
            )
        )

        result = await api_client.test_connection()

        assert result.success is False


class TestRateLimiting:
    """Test rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_rate_limit_header_handling(self, api_client, mock_cribl_api):
        """Test that rate limit headers are handled if present."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(
                200,
                json={"version": "5.0.0"},
                headers={
                    "X-RateLimit-Limit": "100",
                    "X-RateLimit-Remaining": "95",
                    "X-RateLimit-Reset": "1640000000"
                }
            )
        )

        result = await api_client.test_connection()

        assert result.success is True

    @pytest.mark.asyncio
    async def test_429_too_many_requests(self, api_client, mock_cribl_api):
        """Test handling of 429 rate limit exceeded."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(
                429,
                json={"error": "Too Many Requests"},
                headers={"Retry-After": "60"}
            )
        )

        result = await api_client.test_connection()

        assert result.success is False
        assert "rate" in result.error.lower() or "too many" in result.error.lower()


class TestAuthenticationHeaders:
    """Test authentication header handling."""

    @pytest.mark.asyncio
    async def test_bearer_token_in_request(self, api_client, mock_cribl_api):
        """Test that bearer token is included in requests."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        await api_client.test_connection()

        # Verify the request included Authorization header
        request = mock_cribl_api.calls.last.request
        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("Bearer ")
        assert "test-token-12345" in request.headers["Authorization"]
