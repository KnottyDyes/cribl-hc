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
        assert client.api_calls_made == 0
        assert client.api_call_budget == 100

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
    async def test_successful_connection(self):
        """Test successful connection to Cribl API."""
        # Mock the version endpoint
        respx.get("https://cribl.example.com/api/v1/version").mock(
            return_value=httpx.Response(
                200,
                json={"version": "4.5.2", "build": "12345"},
            )
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "valid-token"
        ) as client:
            result = await client.test_connection()

            assert result.success is True
            assert "Successfully connected" in result.message
            assert result.cribl_version == "4.5.2"
            assert result.response_time_ms is not None
            assert result.response_time_ms > 0
            assert result.error is None
            assert client.api_calls_made == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_connection_invalid_token(self):
        """Test connection failure with invalid authentication token."""
        respx.get("https://cribl.example.com/api/v1/version").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "invalid-token"
        ) as client:
            result = await client.test_connection()

            assert result.success is False
            assert "Authentication failed" in result.message
            assert "invalid bearer token" in result.message
            assert result.cribl_version is None
            assert result.error is not None
            assert "HTTP 401" in result.error
            assert client.api_calls_made == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_connection_forbidden(self):
        """Test connection failure with insufficient permissions."""
        respx.get("https://cribl.example.com/api/v1/version").mock(
            return_value=httpx.Response(403, text="Forbidden")
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "restricted-token"
        ) as client:
            result = await client.test_connection()

            assert result.success is False
            assert "Access forbidden" in result.message
            assert "insufficient permissions" in result.message
            assert result.error is not None
            assert "HTTP 403" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_connection_endpoint_not_found(self):
        """Test connection failure when endpoint doesn't exist."""
        respx.get("https://cribl.example.com/api/v1/version").mock(
            return_value=httpx.Response(404, text="Not Found")
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "valid-token"
        ) as client:
            result = await client.test_connection()

            assert result.success is False
            assert "API endpoint not found" in result.message
            assert "verify URL and Cribl version" in result.message
            assert result.error is not None
            assert "HTTP 404" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_connection_server_error(self):
        """Test connection failure with server error."""
        respx.get("https://cribl.example.com/api/v1/version").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "valid-token"
        ) as client:
            result = await client.test_connection()

            assert result.success is False
            assert "Unexpected response code: 500" in result.message
            assert result.error is not None
            assert "HTTP 500" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_connection_network_error(self):
        """Test connection failure with network/connection error."""
        respx.get("https://cribl.example.com/api/v1/version").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "valid-token"
        ) as client:
            result = await client.test_connection()

            assert result.success is False
            assert "Cannot connect to Cribl API" in result.message
            assert "check URL and network" in result.message
            assert result.error is not None
            assert "Connection error" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_connection_timeout(self):
        """Test connection failure with timeout."""
        respx.get("https://cribl.example.com/api/v1/version").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "valid-token", timeout=5.0
        ) as client:
            result = await client.test_connection()

            assert result.success is False
            assert "Connection timeout after 5.0s" in result.message
            assert result.error is not None
            assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_connection_without_context_manager(self):
        """Test that connection test fails when client not initialized."""
        client = CriblAPIClient("https://cribl.example.com", "token")

        # Call test_connection without entering context manager
        result = await client.test_connection()

        assert result.success is False
        assert "Client not initialized" in result.message
        assert "use async context manager" in result.message
        assert result.error == "Client not initialized"


class TestAPICallBudget:
    """Test API call budget tracking and enforcement."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_call_tracking(self):
        """Test that API calls are tracked correctly."""
        respx.get("https://cribl.example.com/api/v1/version").mock(
            return_value=httpx.Response(200, json={"version": "4.5.2"})
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "token"
        ) as client:
            assert client.api_calls_made == 0

            await client.test_connection()
            assert client.api_calls_made == 1

            await client.test_connection()
            assert client.api_calls_made == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_budget_exceeded_on_get(self):
        """Test that GET requests fail when budget exceeded."""
        respx.get("https://cribl.example.com/api/v1/test").mock(
            return_value=httpx.Response(200, json={})
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "token"
        ) as client:
            # Manually set calls to budget limit
            client.api_calls_made = 100

            with pytest.raises(RuntimeError) as exc_info:
                await client.get("/api/v1/test")

            assert "API call budget exceeded" in str(exc_info.value)
            assert "(100/100)" in str(exc_info.value)

    @pytest.mark.asyncio
    @respx.mock
    async def test_budget_exceeded_on_post(self):
        """Test that POST requests fail when budget exceeded."""
        respx.post("https://cribl.example.com/api/v1/test").mock(
            return_value=httpx.Response(200, json={})
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "token"
        ) as client:
            client.api_calls_made = 100

            with pytest.raises(RuntimeError) as exc_info:
                await client.post("/api/v1/test")

            assert "API call budget exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_without_context_manager(self):
        """Test that GET fails without context manager."""
        client = CriblAPIClient("https://cribl.example.com", "token")

        with pytest.raises(RuntimeError) as exc_info:
            await client.get("/api/v1/test")

        assert "Client not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_post_without_context_manager(self):
        """Test that POST fails without context manager."""
        client = CriblAPIClient("https://cribl.example.com", "token")

        with pytest.raises(RuntimeError) as exc_info:
            await client.post("/api/v1/test")

        assert "Client not initialized" in str(exc_info.value)


class TestHTTPMethods:
    """Test basic HTTP methods (GET, POST)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_request(self):
        """Test GET request increments call counter."""
        respx.get("https://cribl.example.com/api/v1/workers").mock(
            return_value=httpx.Response(200, json={"items": []})
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "token"
        ) as client:
            response = await client.get("/api/v1/workers")

            assert response.status_code == 200
            assert client.api_calls_made == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_request(self):
        """Test POST request increments call counter."""
        respx.post("https://cribl.example.com/api/v1/test").mock(
            return_value=httpx.Response(201, json={"status": "created"})
        )

        async with CriblAPIClient(
            "https://cribl.example.com", "token"
        ) as client:
            response = await client.post("/api/v1/test", json={"data": "test"})

            assert response.status_code == 201
            assert client.api_calls_made == 1
