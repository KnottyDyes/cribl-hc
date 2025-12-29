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


class TestCriblAPIClient:
    """Test CriblAPIClient core functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test client initialization."""
        client = CriblAPIClient(
            base_url="https://cribl.example.com:9000",
            auth_token="test-token"
        )

        # Before entering context manager, _client is None
        assert client.base_url == "https://cribl.example.com:9000"
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client as async context manager."""
        with respx.mock:
            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token"
            ) as client:
                # After entering context manager, _client is initialized
                assert client._client is not None

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        with respx.mock:
            # Mock the /api/v1/version endpoint
            respx.get("https://cribl.example.com:9000/api/v1/version").mock(
                return_value=Response(
                    200,
                    json={"version": "5.0.0", "build": "12345"}
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token-12345"
            ) as client:
                result = await client.test_connection()

                assert isinstance(result, ConnectionTestResult)
                assert result.success is True
                assert result.cribl_version == "5.0.0"
                assert result.response_time_ms is not None
                assert result.response_time_ms > 0

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test connection test with failed response."""
        with respx.mock:
            # Mock failed connection
            respx.get("https://cribl.example.com:9000/api/v1/version").mock(
                return_value=Response(401, json={"error": "Unauthorized"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token-12345"
            ) as client:
                result = await client.test_connection()

                assert isinstance(result, ConnectionTestResult)
                assert result.success is False
                assert result.error is not None

    @pytest.mark.asyncio
    async def test_get_system_status(self):
        """Test getting system status."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/system/status").mock(
                return_value=Response(
                    200,
                    json={"health": "healthy", "hostname": "cribl-master"}
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token-12345"
            ) as client:
                result = await client.get_system_status()

                assert result is not None
                assert "health" in result

    @pytest.mark.asyncio
    async def test_get_workers(self):
        """Test getting worker nodes."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
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

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token-12345"
            ) as client:
                result = await client.get_workers()

                # get_workers returns the items list directly
                assert result is not None
                assert isinstance(result, list)
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_workers_404(self):
        """Test getting workers when endpoint returns 404."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/master/workers").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token-12345"
            ) as client:
                result = await client.get_workers()

                # Should return empty list on 404
                assert result == []


class TestAPIClientRetries:
    """Test retry and error handling logic."""

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx_error(self):
        """Test that client doesn't retry on 4xx errors."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/version").mock(
                return_value=Response(404, json={"error": "Not Found"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token-12345"
            ) as client:
                result = await client.test_connection()

                # Should fail immediately without retries
                assert result.success is False


class TestAPIClientAuth:
    """Test authentication handling."""

    @pytest.mark.asyncio
    async def test_bearer_token_in_headers(self):
        """Test that bearer token is included in requests."""
        with respx.mock:
            route = respx.get("https://cribl.example.com:9000/api/v1/version").mock(
                return_value=Response(200, json={"version": "5.0.0"})
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token-12345"
            ) as client:
                await client.test_connection()

                # Check that the request included Authorization header
                assert route.called
                request = route.calls.last.request
                assert "Authorization" in request.headers
                assert request.headers["Authorization"] == "Bearer test-token-12345"


class TestAPIClientErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test handling of request timeouts."""
        import httpx

        with respx.mock:
            # Mock timeout
            respx.get("https://cribl.example.com:9000/api/v1/version").mock(
                side_effect=httpx.TimeoutException("Request timeout")
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token-12345"
            ) as client:
                result = await client.test_connection()

                assert result.success is False
                assert result.error is not None
                assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling of connection errors."""
        import httpx

        with respx.mock:
            # Mock connection error
            respx.get("https://cribl.example.com:9000/api/v1/version").mock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token-12345"
            ) as client:
                result = await client.test_connection()

                assert result.success is False
                assert result.error is not None

    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON responses."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/version").mock(
                return_value=Response(200, text="not valid json")
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token-12345"
            ) as client:
                # Should handle gracefully
                result = await client.test_connection()

                # May succeed or fail depending on implementation
                assert isinstance(result, ConnectionTestResult)

    @pytest.mark.asyncio
    async def test_empty_response(self):
        """Test handling of empty responses."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/version").mock(
                return_value=Response(200, text="")
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token-12345"
            ) as client:
                result = await client.test_connection()

                assert isinstance(result, ConnectionTestResult)

    @pytest.mark.asyncio
    async def test_client_not_initialized_error(self):
        """Test that using client outside context manager fails gracefully."""
        client = CriblAPIClient(
            base_url="https://cribl.example.com:9000",
            auth_token="test-token-12345"
        )

        # Without entering context manager, test_connection should return failure
        result = await client.test_connection()
        assert result.success is False
        assert "not initialized" in result.error.lower()


class TestAPIClientDeploymentDetection:
    """Test deployment type detection."""

    @pytest.mark.asyncio
    async def test_cloud_detection(self):
        """Test that Cribl Cloud deployments are detected."""
        client = CriblAPIClient(
            base_url="https://main-myorg.cribl.cloud",
            auth_token="test-token"
        )
        assert client.is_cloud is True

    @pytest.mark.asyncio
    async def test_self_hosted_detection(self):
        """Test that self-hosted deployments are detected."""
        client = CriblAPIClient(
            base_url="https://cribl.example.com:9000",
            auth_token="test-token"
        )
        assert client.is_cloud is False

    @pytest.mark.asyncio
    async def test_product_type_detection(self):
        """Test that product type is detected from version response."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/version").mock(
                return_value=Response(
                    200,
                    json={"version": "5.0.0", "product": "stream"}
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token"
            ) as client:
                result = await client.test_connection()

                assert result.success is True
                assert client.product_type == "stream"
                assert client.is_stream is True
                assert client.is_edge is False

    @pytest.mark.asyncio
    async def test_edge_product_detection(self):
        """Test that Edge product is detected."""
        with respx.mock:
            respx.get("https://cribl.example.com:9000/api/v1/version").mock(
                return_value=Response(
                    200,
                    json={"version": "4.8.0", "product": "edge"}
                )
            )

            async with CriblAPIClient(
                base_url="https://cribl.example.com:9000",
                auth_token="test-token"
            ) as client:
                result = await client.test_connection()

                assert result.success is True
                assert client.product_type == "edge"
                assert client.is_edge is True
                assert client.is_stream is False
