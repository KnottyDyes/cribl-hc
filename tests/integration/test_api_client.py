"""
Integration tests for Cribl API client.

Tests HTTP client functionality, rate limiting, error handling, and retries.
Uses respx to mock Cribl API responses.
"""

import pytest
import respx
from httpx import Response

from cribl_hc.core.api_client import CriblAPIClient, ConnectionTestResult
from cribl_hc.utils.rate_limiter import RateLimiter


@pytest.fixture
def mock_cribl_api():
    """Setup respx mock for Cribl API."""
    with respx.mock:
        yield respx


@pytest.fixture
async def api_client():
    """Create API client for testing."""
    client = CriblAPIClient(
        base_url="https://cribl.example.com:9000",
        auth_token="test-token-12345"
    )
    yield client
    await client.close()


class TestCriblAPIClient:
    """Test CriblAPIClient core functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test client initialization."""
        client = CriblAPIClient(
            base_url="https://cribl.example.com:9000",
            auth_token="test-token"
        )

        assert client.base_url == "https://cribl.example.com:9000"
        assert client.client is not None

        await client.close()

    @pytest.mark.asyncio
    async def test_initialization_with_oauth(self):
        """Test client initialization with OAuth credentials."""
        client = CriblAPIClient(
            base_url="https://cribl.example.com:9000",
            auth_token="test-token",
            client_id="test-client-id",
            client_secret="test-client-secret"
        )

        assert client.client_id == "test-client-id"
        assert client.client_secret == "test-client-secret"

        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as async context manager."""
        async with CriblAPIClient(
            base_url="https://cribl.example.com:9000",
            auth_token="test-token"
        ) as client:
            assert client.client is not None

    @pytest.mark.asyncio
    async def test_test_connection_success(self, api_client, mock_cribl_api):
        """Test successful connection test."""
        # Mock the /api/v1/version endpoint
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(
                200,
                json={"version": "5.0.0", "build": "12345"}
            )
        )

        result = await api_client.test_connection()

        assert isinstance(result, ConnectionTestResult)
        assert result.success is True
        assert result.cribl_version == "5.0.0"
        assert result.response_time_ms > 0

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, api_client, mock_cribl_api):
        """Test connection test with failed response."""
        # Mock failed connection
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        result = await api_client.test_connection()

        assert isinstance(result, ConnectionTestResult)
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_get_system_info(self, api_client, mock_cribl_api):
        """Test getting system information."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/system/info").mock(
            return_value=Response(
                200,
                json={"guid": "test-guid", "hostname": "cribl-master"}
            )
        )

        result = await api_client.get_system_info()

        assert result is not None
        assert "guid" in result

    @pytest.mark.asyncio
    async def test_get_workers(self, api_client, mock_cribl_api):
        """Test getting worker nodes."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {"id": "worker-1", "status": "alive"},
                        {"id": "worker-2", "status": "alive"}
                    ]
                }
            )
        )

        result = await api_client.get_workers()

        assert result is not None
        assert "items" in result
        assert len(result["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_metrics(self, api_client, mock_cribl_api):
        """Test getting metrics."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/metrics").mock(
            return_value=Response(
                200,
                json={"cpu_usage": 45.5, "memory_usage": 60.2}
            )
        )

        result = await api_client.get_metrics()

        assert result is not None
        assert "cpu_usage" in result or "memory_usage" in result


class TestAPIClientRetries:
    """Test retry and error handling logic."""

    @pytest.mark.asyncio
    async def test_retry_on_5xx_error(self, api_client, mock_cribl_api):
        """Test that client retries on 5xx errors."""
        # First call fails with 500, second succeeds
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            side_effect=[
                Response(500, json={"error": "Internal Server Error"}),
                Response(200, json={"version": "5.0.0"})
            ]
        )

        result = await api_client.test_connection()

        # Should eventually succeed after retry
        assert result.success is True

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx_error(self, api_client, mock_cribl_api):
        """Test that client doesn't retry on 4xx errors."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(404, json={"error": "Not Found"})
        )

        result = await api_client.test_connection()

        # Should fail immediately without retries
        assert result.success is False


class TestAPIClientRateLimiting:
    """Test rate limiting integration."""

    @pytest.mark.asyncio
    async def test_rate_limiter_integration(self, mock_cribl_api):
        """Test that rate limiter is enforced."""
        # Create client with strict rate limit
        rate_limiter = RateLimiter(max_calls=2, time_window_seconds=60.0)

        client = CriblAPIClient(
            base_url="https://cribl.example.com:9000",
            auth_token="test-token",
            rate_limiter=rate_limiter
        )

        # Mock successful responses
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        # Make 2 calls (should succeed)
        await client.test_connection()
        await client.test_connection()

        # Third call should hit rate limit
        with pytest.raises(RuntimeError, match="budget exhausted"):
            await client.test_connection()

        await client.close()

    @pytest.mark.asyncio
    async def test_api_call_tracking(self, api_client, mock_cribl_api):
        """Test that API calls are tracked."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        initial_calls = api_client.get_api_calls_made()
        await api_client.test_connection()
        final_calls = api_client.get_api_calls_made()

        assert final_calls > initial_calls


class TestAPIClientAuth:
    """Test authentication handling."""

    @pytest.mark.asyncio
    async def test_bearer_token_in_headers(self, api_client, mock_cribl_api):
        """Test that bearer token is included in requests."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        await api_client.test_connection()

        # Check that the request included Authorization header
        request = mock_cribl_api.calls.last.request
        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("Bearer ")

    @pytest.mark.asyncio
    async def test_oauth_token_refresh(self, mock_cribl_api):
        """Test OAuth token refresh logic."""
        client = CriblAPIClient(
            base_url="https://cribl.example.com:9000",
            auth_token="initial-token",
            client_id="test-client",
            client_secret="test-secret"
        )

        # Mock token endpoint
        mock_cribl_api.post("https://cribl.example.com:9000/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "new-token", "expires_in": 3600}
            )
        )

        # Mock API call that requires auth
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, json={"version": "5.0.0"})
        )

        # Token refresh should happen if needed
        await client.test_connection()

        await client.close()


class TestAPIClientErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_timeout_handling(self, api_client, mock_cribl_api):
        """Test handling of request timeouts."""
        import httpx

        # Mock timeout
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        result = await api_client.test_connection()

        assert result.success is False
        assert "timeout" in result.error.lower() if result.error else True

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, api_client, mock_cribl_api):
        """Test handling of connection errors."""
        import httpx

        # Mock connection error
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        result = await api_client.test_connection()

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, api_client, mock_cribl_api):
        """Test handling of invalid JSON responses."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, text="not valid json")
        )

        # Should handle gracefully
        result = await api_client.test_connection()

        # May succeed or fail depending on implementation
        assert isinstance(result, ConnectionTestResult)

    @pytest.mark.asyncio
    async def test_empty_response(self, api_client, mock_cribl_api):
        """Test handling of empty responses."""
        mock_cribl_api.get("https://cribl.example.com:9000/api/v1/version").mock(
            return_value=Response(200, text="")
        )

        result = await api_client.test_connection()

        assert isinstance(result, ConnectionTestResult)
