"""
Unit tests for CriblAPIClient and connection testing.
"""

import pytest
import httpx
import respx
from datetime import datetime

from cribl_hc.core.api_client import CriblAPIClient, ConnectionTestResult


class TestConnectionTestResult:
    """Test ConnectionTestResult model."""

    def test_valid_connection_test_result(self):
        """Test creating a valid connection test result."""
        result = ConnectionTestResult(
            success=True,
            message="Connected successfully",
            response_time_ms=125.5,
            cribl_version="4.5.2",
            api_url="https://cribl.example.com/api/v1/version",
        )

        assert result.success is True
        assert result.message == "Connected successfully"
        assert result.response_time_ms == 125.5
        assert result.cribl_version == "4.5.2"
        assert result.api_url == "https://cribl.example.com/api/v1/version"
        assert result.error is None
        assert isinstance(result.tested_at, datetime)

    def test_connection_test_result_with_error(self):
        """Test connection test result with error details."""
        result = ConnectionTestResult(
            success=False,
            message="Connection failed",
            response_time_ms=50.0,
            api_url="https://cribl.example.com/api/v1/version",
            error="HTTP 401: Unauthorized",
        )

        assert result.success is False
        assert result.error == "HTTP 401: Unauthorized"
        assert result.cribl_version is None


class TestCriblAPIClient:
    """Test CriblAPIClient initialization and basic functionality."""

    def test_client_initialization(self):
        """Test client initialization with required parameters."""
        client = CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token-123",
        )

        assert client.base_url == "https://cribl.example.com"
        assert client.auth_token == "test-token-123"
        assert client.timeout == 30.0  # default
        assert client.max_retries == 3  # default
        # API call tracking is delegated to rate_limiter
        assert client.get_api_calls_used() == 0

    def test_client_strips_trailing_slash(self):
        """Test that trailing slash is removed from base URL."""
        client = CriblAPIClient(
            base_url="https://cribl.example.com/",
            auth_token="token",
        )

        assert client.base_url == "https://cribl.example.com"

    def test_client_custom_timeout_and_retries(self):
        """Test client with custom timeout and retry settings."""
        client = CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="token",
            timeout=60.0,
            max_retries=5,
        )

        assert client.timeout == 60.0
        assert client.max_retries == 5


class TestConnectionTesting:
    """Test connection testing functionality with mocked HTTP responses."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_connection(self, respx_mock):
        """Test successful connection to Cribl API."""
        # Mock the version endpoint
        respx_mock.get("https://cribl.example.com/api/v1/system/info").mock(
            return_value=httpx.Response(
                200,
                json={"version": "4.5.2", "build": "12345", "product": "stream"},
            )
        )

        async with CriblAPIClient("https://cribl.example.com", "valid-token") as client:
            result = await client.test_connection()

            assert result.success is True
            assert "Successfully connected" in result.message
            assert result.cribl_version == "4.5.2"
            assert result.response_time_ms is not None
            assert result.response_time_ms > 0
            assert result.error is None
            assert client.get_api_calls_used() == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_connection_server_error(self, respx_mock):
        """Test connection failure with server error."""
        respx_mock.get("https://cribl.example.com/api/v1/system/info").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        async with CriblAPIClient("https://cribl.example.com", "valid-token") as client:
            result = await client.test_connection()

            assert result.success is False
            assert "Unexpected response code: 500" in result.message
            assert result.error is not None
            assert "HTTP 500" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_connection_network_error(self, respx_mock):
        """Test connection failure with network/connection error."""
        respx_mock.get("https://cribl.example.com/api/v1/system/info").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        async with CriblAPIClient("https://cribl.example.com", "valid-token") as client:
            result = await client.test_connection()

            assert result.success is False
            assert "Connection test failed" in result.message
            assert result.error is not None
            assert "Connection refused" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_connection_timeout(self, respx_mock):
        """Test connection failure with timeout."""
        respx_mock.get("https://cribl.example.com/api/v1/system/info").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "valid-token", timeout=5.0
        ) as client:
            result = await client.test_connection()

            assert result.success is False
            assert "Connection test failed" in result.message
            assert result.error is not None
            assert "Request timeout" in result.error

    @pytest.mark.asyncio
    async def test_connection_without_context_manager(self):
        """Test that connection test fails when client not initialized."""
        client = CriblAPIClient("https://cribl.example.com", "token")

        # Call test_connection without entering context manager
        result = await client.test_connection()

        assert result.success is False
        assert "Client not initialized" in result.message
        assert result.error == "Client not initialized"


class TestAPICallBudget:
    """Test API call budget tracking and enforcement."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_call_tracking(self, respx_mock):
        """Test that API calls are tracked correctly."""
        respx_mock.get("https://cribl.example.com/api/v1/system/info").mock(
            return_value=httpx.Response(200, json={"version": "4.5.2"})
        )

        async with CriblAPIClient("https://cribl.example.com", "token") as client:
            assert client.get_api_calls_used() == 0

            await client.test_connection()
            assert client.get_api_calls_used() == 1

            await client.test_connection()
            assert client.get_api_calls_used() == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_budget_exceeded_on_get(self, respx_mock):
        """Test that GET requests fail when budget exceeded."""
        respx_mock.get("https://cribl.example.com/api/v1/test").mock(
            return_value=httpx.Response(200, json={})
        )

        async with CriblAPIClient("https://cribl.example.com", "token") as client:
            # Manually set calls to budget limit via rate_limiter
            client.rate_limiter.total_calls_made = 100

            with pytest.raises(RuntimeError) as exc_info:
                await client.get("/api/v1/test")

            assert "API call budget exhausted" in str(exc_info.value)
            assert "(100/100)" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_without_context_manager(self):
        """Test that GET fails without context manager."""
        client = CriblAPIClient("https://cribl.example.com", "token")

        with pytest.raises(RuntimeError) as exc_info:
            await client.get("/api/v1/test")

        assert "Client not initialized" in str(exc_info.value)


class TestHTTPMethods:
    """Test basic HTTP methods (GET, POST)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_request(self, respx_mock):
        """Test GET request increments call counter."""
        respx_mock.get("https://cribl.example.com/api/v1/workers").mock(
            return_value=httpx.Response(200, json={"items": []})
        )

        async with CriblAPIClient("https://cribl.example.com", "token") as client:
            response = await client.get("/api/v1/workers")

            assert response.status_code == 200
            assert client.get_api_calls_used() == 1


class TestEdgeAPIMethods:
    """Test Edge-specific API methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_nodes_routes_to_edge(self, respx_mock):
        """Test that get_nodes() calls Edge endpoint when is_edge=True."""
        # Mock version endpoint to detect Edge
        respx_mock.get("https://edge.example.com/api/v1/system/info").mock(
            return_value=httpx.Response(200, json={"version": "4.15.0", "product": "edge"})
        )

        # Mock Edge nodes endpoint
        respx_mock.get("https://edge.example.com/api/v1/edge/nodes").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [
                        {"id": "node-1", "status": "connected"},
                    ]
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://edge.example.com", auth_token="test-token"
        ) as client:
            # Detect product type
            await client.test_connection()

            # Verify Edge detection
            assert client.is_edge is True
            assert client.product_type == "edge"

            # get_nodes() should route to Edge endpoint
            nodes = await client.get_nodes()

            assert len(nodes) == 1
            assert nodes[0]["id"] == "node-1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_nodes_routes_to_stream(self, respx_mock):
        """Test that get_nodes() calls Stream endpoint when is_stream=True."""
        # Mock version endpoint to detect Stream
        respx_mock.get("https://stream.example.com/api/v1/system/info").mock(
            return_value=httpx.Response(200, json={"version": "4.7.0", "product": "stream"})
        )

        # Mock Stream workers endpoint
        respx_mock.get("https://stream.example.com/api/v1/master/workers").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [
                        {"id": "worker-1", "status": "healthy"},
                    ]
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://stream.example.com", auth_token="test-token"
        ) as client:
            # Detect product type
            await client.test_connection()

            # Verify Stream detection
            assert client.is_stream is True
            assert client.product_type == "stream"

            # get_nodes() should route to Stream endpoint
            nodes = await client.get_nodes()

            assert len(nodes) == 1
            assert nodes[0]["id"] == "worker-1"

    @pytest.mark.asyncio
    async def test_normalize_edge_node_data(self):
        """Test Edge node normalization."""
        client = CriblAPIClient(base_url="https://edge.example.com", auth_token="test-token")
        client._product_type = "edge"

        edge_node = {
            "id": "node-1",
            "status": "connected",
            "fleet": "production",
            "lastSeen": "2024-12-13T12:00:00Z",
        }

        normalized = client._normalize_node_data(edge_node)
        assert normalized == edge_node

    @pytest.mark.asyncio
    async def test_normalize_stream_node_is_noop(self):
        """Test that normalization is no-op for Stream workers."""
        client = CriblAPIClient(base_url="https://stream.example.com", auth_token="test-token")
        client._product_type = "stream"

        stream_worker = {
            "id": "worker-1",
            "status": "healthy",
            "group": "default",
        }

        normalized = client._normalize_node_data(stream_worker)

        # Should return unchanged for Stream
        assert normalized == stream_worker


class TestAPIGetMethods:
    """Test specific get_* methods in the API client."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_outputs_returns_empty_list_on_404(self, respx_mock):
        """Test that get_outputs() returns an empty list on a 404 error."""
        respx_mock.get("https://cribl.example.com/api/v1/master/outputs").mock(
            return_value=httpx.Response(404)
        )

        async with CriblAPIClient("https://cribl.example.com", "token") as client:
            client._product_type = "stream"  # Simulate a detected stream instance
            result = await client.get_outputs()
            assert result == []
            # Verify the call was made
            assert client.get_api_calls_used() == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_outputs_raises_on_401(self, respx_mock):
        """Test that get_outputs() raises HTTPStatusError on 401."""
        respx_mock.get("https://cribl.example.com/api/v1/master/outputs").mock(
            return_value=httpx.Response(401)
        )

        async with CriblAPIClient("https://cribl.example.com", "token") as client:
            client._product_type = "stream"
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_outputs()
            assert client.get_api_calls_used() == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_raises_on_timeout(self, respx_mock):
        """Test that a generic get raises TimeoutException."""
        respx_mock.get("https://cribl.example.com/api/v1/master/outputs").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        async with CriblAPIClient("https://cribl.example.com", "token") as client:
            client._product_type = "stream"
            with pytest.raises(httpx.TimeoutException):
                await client.get_outputs()
            assert client.get_api_calls_used() == 1
