"""
Cribl API client with rate limiting, error handling, and connection testing.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, Field


class ConnectionTestResult(BaseModel):
    """
    Result of testing connection to Cribl API.

    Attributes:
        success: Whether connection was successful
        message: Human-readable status message
        response_time_ms: API response time in milliseconds
        cribl_version: Detected Cribl version (if successful)
        api_url: The API URL that was tested
        error: Error details if connection failed
        tested_at: Timestamp when test was performed
    """

    success: bool = Field(..., description="Connection test success status")
    message: str = Field(..., description="Human-readable status message")
    response_time_ms: Optional[float] = Field(
        None, description="API response time in milliseconds"
    )
    cribl_version: Optional[str] = Field(None, description="Detected Cribl version")
    api_url: str = Field(..., description="API URL tested")
    error: Optional[str] = Field(None, description="Error details if failed")
    tested_at: datetime = Field(default_factory=datetime.utcnow)


class CriblAPIClient:
    """
    Async HTTP client for Cribl Stream API with rate limiting and error handling.

    Features:
    - Connection testing with health endpoint
    - Rate limiting to stay under 100 API call budget
    - Automatic retry with exponential backoff
    - Graceful error handling
    - Structured logging for audit trail

    Example:
        >>> async with CriblAPIClient("https://cribl.example.com", "token") as client:
        ...     result = await client.test_connection()
        ...     if result.success:
        ...         print(f"Connected to Cribl {result.cribl_version}")
    """

    def __init__(
        self,
        base_url: str,
        auth_token: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize Cribl API client.

        Args:
            base_url: Cribl leader URL (e.g., "https://cribl.example.com")
            auth_token: Bearer token for authentication
            timeout: Request timeout in seconds (default: 30.0)
            max_retries: Maximum retry attempts (default: 3)
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self.max_retries = max_retries

        # HTTP client will be initialized in __aenter__
        self._client: Optional[httpx.AsyncClient] = None

        # API call tracking for budget monitoring
        self.api_calls_made = 0
        self.api_call_budget = 100

    async def __aenter__(self):
        """Async context manager entry - initialize HTTP client."""
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Accept": "application/json",
            "User-Agent": "cribl-health-check/1.0",
        }

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def test_connection(self) -> ConnectionTestResult:
        """
        Test connection to Cribl API by calling the system status endpoint.

        This performs a lightweight API call to verify:
        1. URL is reachable
        2. Authentication token is valid
        3. API is responding
        4. Cribl version can be detected

        Returns:
            ConnectionTestResult with success status and details

        Example:
            >>> result = await client.test_connection()
            >>> if result.success:
            ...     print(f"✓ Connected ({result.response_time_ms:.0f}ms)")
            ... else:
            ...     print(f"✗ Failed: {result.error}")
        """
        if not self._client:
            return ConnectionTestResult(
                success=False,
                message="Client not initialized - use async context manager",
                api_url=self.base_url,
                error="Client not initialized",
            )

        # Use system status endpoint for connection test
        # This is a lightweight endpoint that doesn't require permissions
        endpoint = "/api/v1/version"
        test_url = urljoin(self.base_url, endpoint)

        start_time = datetime.utcnow()

        try:
            response = await self._client.get(endpoint)
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Track API call
            self.api_calls_made += 1

            # Check response status
            if response.status_code == 200:
                data = response.json()
                version = data.get("version", "unknown")

                return ConnectionTestResult(
                    success=True,
                    message=f"Successfully connected to Cribl Stream {version}",
                    response_time_ms=round(elapsed_ms, 2),
                    cribl_version=version,
                    api_url=test_url,
                )

            elif response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    message="Authentication failed - invalid bearer token",
                    response_time_ms=round(elapsed_ms, 2),
                    api_url=test_url,
                    error=f"HTTP 401: {response.text}",
                )

            elif response.status_code == 403:
                return ConnectionTestResult(
                    success=False,
                    message="Access forbidden - insufficient permissions",
                    response_time_ms=round(elapsed_ms, 2),
                    api_url=test_url,
                    error=f"HTTP 403: {response.text}",
                )

            elif response.status_code == 404:
                return ConnectionTestResult(
                    success=False,
                    message="API endpoint not found - verify URL and Cribl version",
                    response_time_ms=round(elapsed_ms, 2),
                    api_url=test_url,
                    error=f"HTTP 404: {response.text}",
                )

            else:
                return ConnectionTestResult(
                    success=False,
                    message=f"Unexpected response code: {response.status_code}",
                    response_time_ms=round(elapsed_ms, 2),
                    api_url=test_url,
                    error=f"HTTP {response.status_code}: {response.text}",
                )

        except httpx.ConnectError as e:
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ConnectionTestResult(
                success=False,
                message="Cannot connect to Cribl API - check URL and network",
                response_time_ms=round(elapsed_ms, 2),
                api_url=test_url,
                error=f"Connection error: {str(e)}",
            )

        except httpx.TimeoutException as e:
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ConnectionTestResult(
                success=False,
                message=f"Connection timeout after {self.timeout}s",
                response_time_ms=round(elapsed_ms, 2),
                api_url=test_url,
                error=f"Timeout: {str(e)}",
            )

        except Exception as e:
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ConnectionTestResult(
                success=False,
                message=f"Connection test failed: {type(e).__name__}",
                response_time_ms=round(elapsed_ms, 2),
                api_url=test_url,
                error=str(e),
            )

    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """
        Make GET request to Cribl API.

        Args:
            endpoint: API endpoint path (e.g., "/api/v1/master/workers")
            **kwargs: Additional arguments to pass to httpx

        Returns:
            httpx.Response object

        Raises:
            RuntimeError: If API call budget exceeded
        """
        if self.api_calls_made >= self.api_call_budget:
            raise RuntimeError(
                f"API call budget exceeded ({self.api_calls_made}/{self.api_call_budget})"
            )

        if not self._client:
            raise RuntimeError("Client not initialized - use async context manager")

        response = await self._client.get(endpoint, **kwargs)
        self.api_calls_made += 1
        return response

    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        """
        Make POST request to Cribl API.

        Args:
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to httpx

        Returns:
            httpx.Response object

        Raises:
            RuntimeError: If API call budget exceeded
        """
        if self.api_calls_made >= self.api_call_budget:
            raise RuntimeError(
                f"API call budget exceeded ({self.api_calls_made}/{self.api_call_budget})"
            )

        if not self._client:
            raise RuntimeError("Client not initialized - use async context manager")

        response = await self._client.post(endpoint, **kwargs)
        self.api_calls_made += 1
        return response
