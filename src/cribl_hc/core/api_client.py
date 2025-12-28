"""
Cribl API client with rate limiting, error handling, and connection testing.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, Field

from cribl_hc.utils.logger import get_logger
from cribl_hc.utils.rate_limiter import RateLimiter


log = get_logger(__name__)


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
        rate_limiter: Optional[RateLimiter] = None,
        worker_group: Optional[str] = None,
    ):
        """
        Initialize Cribl API client.

        Args:
            base_url: Cribl leader URL (e.g., "https://cribl.example.com")
            auth_token: Bearer token for authentication
            timeout: Request timeout in seconds (default: 30.0)
            max_retries: Maximum retry attempts (default: 3)
            rate_limiter: Optional rate limiter (creates default if not provided)
            worker_group: Worker group name for Cribl Cloud (auto-detected if not provided)
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self.max_retries = max_retries

        # HTTP client will be initialized in __aenter__
        self._client: Optional[httpx.AsyncClient] = None

        # Deployment type detection
        self._is_cloud = "cribl.cloud" in base_url.lower()
        self._worker_group = worker_group  # Will be auto-detected if None
        self._deployment_detected = False

        # Product type detection (stream, edge, lake)
        self._product_type: Optional[str] = None  # Will be detected on first API call
        self._product_version: Optional[str] = None

        # Rate limiter for API call budget enforcement
        self.rate_limiter = rate_limiter or RateLimiter(
            max_calls=100,
            time_window_seconds=3600.0,  # 1 hour window
            enable_backoff=True,
        )

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

        # Auto-detect worker group for Cribl Cloud deployments
        if self._is_cloud and not self._worker_group:
            await self._detect_worker_group()

        return self

    async def _detect_worker_group(self) -> None:
        """
        Auto-detect worker group for Cribl Cloud deployments.

        Tries common worker group names ("default", "defaultGroup", "workers")
        and detects which one works by testing the pipelines endpoint.
        """
        if not self._client:
            return

        # Try common worker group names
        candidates = ["default", "defaultGroup", "workers", "main"]

        log.debug("detecting_worker_group", candidates=candidates)

        for group_name in candidates:
            try:
                # Test if this group exists by checking pipelines endpoint
                test_endpoint = f"/api/v1/m/{group_name}/pipelines"
                response = await self._client.get(test_endpoint)

                if response.status_code == 200:
                    self._worker_group = group_name
                    self._deployment_detected = True
                    log.info("worker_group_detected", group=group_name)
                    return

            except Exception:
                continue

        # If no group found, default to "default"
        log.warning("worker_group_not_detected", using_default="default")
        self._worker_group = "default"
        self._deployment_detected = True

    @property
    def is_cloud(self) -> bool:
        """
        Check if this is a Cribl Cloud deployment.

        Returns:
            True if deployment is Cribl Cloud, False if self-hosted
        """
        return self._is_cloud

    @property
    def product_type(self) -> Optional[str]:
        """
        Get the detected Cribl product type.

        Returns:
            Product type: "stream", "edge", "lake", or None if not yet detected

        Note:
            Product detection happens automatically on first API call to /api/v1/version
        """
        return self._product_type

    @property
    def is_stream(self) -> bool:
        """Check if this is a Cribl Stream deployment."""
        return self._product_type == "stream"

    @property
    def is_edge(self) -> bool:
        """Check if this is a Cribl Edge deployment."""
        return self._product_type == "edge"

    @property
    def is_lake(self) -> bool:
        """Check if this is a Cribl Lake deployment."""
        return self._product_type == "lake"

    @property
    def product_version(self) -> Optional[str]:
        """
        Get the detected Cribl product version.

        Returns:
            Product version string (e.g., "4.5.0") or None if not yet detected
        """
        return self._product_version

    async def _detect_product_type(self, version_info: Dict[str, Any]) -> None:
        """
        Detect Cribl product type from version endpoint response.

        Args:
            version_info: Response from /api/v1/version endpoint

        The version endpoint returns different structures for different products:
        - Stream: {"version": "4.5.0", "product": "stream"} or no product field
        - Edge: {"version": "4.8.0", "product": "edge"}
        - Lake: {"version": "1.2.0", "product": "lake"}
        """
        if not version_info:
            self._product_type = "stream"  # Default to stream
            return

        # Try to detect from explicit product field
        product = version_info.get("product", "").lower()
        if product in ["stream", "edge", "lake"]:
            self._product_type = product
            self._product_version = version_info.get("version")
            log.info("product_detected", product=product, version=self._product_version)
            return

        # Fallback: Try to infer from endpoint availability
        # Edge and Lake have different endpoint structures
        if self._client:
            # Check for Edge-specific endpoint
            try:
                response = await self._client.get("/api/v1/edge/fleets")
                if response.status_code in [200, 401, 403]:  # Exists but may need auth
                    self._product_type = "edge"
                    self._product_version = version_info.get("version")
                    log.info("product_inferred", product="edge", method="endpoint_probe")
                    return
            except Exception:
                pass

            # Check for Lake-specific endpoint
            try:
                response = await self._client.get("/api/v1/datasets")
                if response.status_code in [200, 401, 403]:
                    self._product_type = "lake"
                    self._product_version = version_info.get("version")
                    log.info("product_inferred", product="lake", method="endpoint_probe")
                    return
            except Exception:
                pass

        # Default to Stream if nothing else matches
        self._product_type = "stream"
        self._product_version = version_info.get("version")
        log.info("product_defaulted", product="stream", version=self._product_version)

    def _build_config_endpoint(self, resource: str, fleet: Optional[str] = None) -> str:
        """
        Build the correct API endpoint based on deployment type and product.

        Args:
            resource: Resource type (pipelines, routes, inputs, outputs)
            fleet: Optional Edge fleet name (only used for Edge deployments)

        Returns:
            Full endpoint path for the resource

        Example:
            Stream self-hosted: /api/v1/master/pipelines
            Stream Cloud: /api/v1/m/default/pipelines
            Edge global: /api/v1/edge/pipelines
            Edge fleet-specific: /api/v1/e/{fleet}/pipelines
        """
        if self.is_edge:
            # Edge deployment
            if fleet:
                return f"/api/v1/e/{fleet}/{resource}"
            else:
                return f"/api/v1/edge/{resource}"
        elif self._is_cloud:
            # Stream Cloud deployment
            group = self._worker_group or "default"
            return f"/api/v1/m/{group}/{resource}"
        else:
            # Stream self-hosted deployment
            return f"/api/v1/master/{resource}"

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
            # Use rate limiter context manager for automatic tracking
            async with self.rate_limiter:
                response = await self._client.get(endpoint)

            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Check response status
            if response.status_code == 200:
                data = response.json()
                version = data.get("version", "unknown")

                # Detect product type on first successful connection
                if not self._product_type:
                    await self._detect_product_type(data)

                # Build product-aware success message
                product_name = {
                    "stream": "Cribl Stream",
                    "edge": "Cribl Edge",
                    "lake": "Cribl Lake"
                }.get(self._product_type or "stream", "Cribl")

                # Check version compatibility and build message
                base_message = f"Successfully connected to {product_name} {version}"

                # Add version compatibility warning if needed
                try:
                    from cribl_hc.utils.version import parse_version, is_version_supported
                    parsed_version = parse_version(version)
                    if parsed_version and not is_version_supported(parsed_version):
                        # Version is older than N-2, add warning
                        base_message += (
                            f" (⚠️  Version {version} is older than officially supported. "
                            f"Analysis will proceed with best-effort compatibility.)"
                        )
                        log.warning(
                            "unsupported_version_detected",
                            version=version,
                            product=self._product_type,
                            message="Proceeding with best-effort analysis"
                        )
                except Exception:
                    # Don't fail connection test if version parsing fails
                    pass

                return ConnectionTestResult(
                    success=True,
                    message=base_message,
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
        Make GET request to Cribl API with rate limiting.

        Args:
            endpoint: API endpoint path (e.g., "/api/v1/master/workers")
            **kwargs: Additional arguments to pass to httpx

        Returns:
            httpx.Response object

        Raises:
            RuntimeError: If API call budget exceeded or client not initialized
        """
        if not self._client:
            raise RuntimeError("Client not initialized - use async context manager")

        async with self.rate_limiter:
            log.debug("api_request", method="GET", endpoint=endpoint)
            response = await self._client.get(endpoint, **kwargs)
            log.info(
                "api_response",
                method="GET",
                endpoint=endpoint,
                status_code=response.status_code,
            )
            return response

    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        """
        Make POST request to Cribl API with rate limiting.

        Args:
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to httpx

        Returns:
            httpx.Response object

        Raises:
            RuntimeError: If API call budget exceeded or client not initialized
        """
        if not self._client:
            raise RuntimeError("Client not initialized - use async context manager")

        async with self.rate_limiter:
            log.debug("api_request", method="POST", endpoint=endpoint)
            response = await self._client.post(endpoint, **kwargs)
            log.info(
                "api_response",
                method="POST",
                endpoint=endpoint,
                status_code=response.status_code,
            )
            return response

    def _normalize_node_data(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Edge node data to match Stream worker structure.

        This allows analyzers to work with unified data structure regardless of product.

        Args:
            node: Raw node data from API

        Returns:
            Normalized node data compatible with analyzer expectations

        Key Transformations:
            - Edge "connected" → Stream "healthy"
            - Edge "disconnected" → Stream "unhealthy"
            - Edge "fleet" → Stream "group"
            - Edge "lastSeen" → Stream "lastMsgTime"
        """
        if not self.is_edge:
            # Already Stream format, return as-is
            return node

        # Create normalized copy
        normalized = node.copy()

        # Map Edge status to Stream status
        edge_status = node.get("status", "unknown")
        if edge_status == "connected":
            normalized["status"] = "healthy"
        elif edge_status == "disconnected":
            normalized["status"] = "unhealthy"
        else:
            normalized["status"] = edge_status

        # Map fleet to group for consistency
        if "fleet" in node:
            normalized["group"] = node["fleet"]

        # Edge nodes may have lastSeen instead of lastMsgTime
        if "lastSeen" in node and "lastMsgTime" not in normalized:
            # Convert ISO timestamp to milliseconds
            # Edge: "2024-12-13T12:00:00Z"
            # Stream: 1702468800000
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(node["lastSeen"].replace("Z", "+00:00"))
                normalized["lastMsgTime"] = int(dt.timestamp() * 1000)
            except Exception:
                # If timestamp conversion fails, skip it
                pass

        return normalized

    # High-level endpoint methods for common operations

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status from /api/v1/system/status.

        Returns:
            System status data including health and component status

        Example:
            >>> status = await client.get_system_status()
            >>> print(status["health"])
        """
        response = await self.get("/api/v1/system/status")
        response.raise_for_status()
        return response.json()

    async def get_workers(self) -> List[Dict[str, Any]]:
        """
        Get worker nodes from /api/v1/master/workers.

        Returns:
            List of worker node data with status and metrics

        Example:
            >>> workers = await client.get_workers()
            >>> for worker in workers:
            ...     print(f"{worker['id']}: {worker['status']}")
        """
        response = await self.get("/api/v1/master/workers")
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])

    async def get_edge_nodes(self, fleet: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get Edge node instances from /api/v1/edge/nodes.

        Args:
            fleet: Optional fleet name to filter nodes

        Returns:
            List of Edge node data with status and metrics

        Example:
            >>> nodes = await client.get_edge_nodes()
            >>> for node in nodes:
            ...     print(f"{node['id']}: {node['status']}")
        """
        if fleet:
            endpoint = f"/api/v1/e/{fleet}/nodes"
        else:
            endpoint = "/api/v1/edge/nodes"

        response = await self.get(endpoint)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])

    async def get_edge_fleets(self) -> List[Dict[str, Any]]:
        """
        Get Edge fleet configurations from /api/v1/edge/fleets.

        Returns:
            List of Edge fleet data

        Example:
            >>> fleets = await client.get_edge_fleets()
            >>> for fleet in fleets:
            ...     print(f"{fleet['id']}: {fleet['name']}")
        """
        response = await self.get("/api/v1/edge/fleets")
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])

    async def get_nodes(self) -> List[Dict[str, Any]]:
        """
        Get worker nodes (Stream) or Edge nodes (Edge) based on detected product.

        This is a unified method that abstracts the difference between products.
        Product type is automatically detected during connection test.

        Returns:
            List of node data (workers for Stream, nodes for Edge)

        Example:
            >>> nodes = await client.get_nodes()  # Works for both Stream and Edge
            >>> for node in nodes:
            ...     print(f"{node['id']}: {node['status']}")
        """
        if self.is_edge:
            return await self.get_edge_nodes()
        else:
            # Default to Stream (includes is_stream and fallback)
            return await self.get_workers()

    async def get_metrics(self, time_range: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics from /api/v1/metrics.

        Args:
            time_range: Optional time range (e.g., "1h", "24h")

        Returns:
            Metrics data including throughput, CPU, memory, etc.

        Example:
            >>> metrics = await client.get_metrics(time_range="1h")
            >>> print(metrics["throughput"]["bytes_in"])
        """
        params = {"timeRange": time_range} if time_range else {}
        response = await self.get("/api/v1/metrics", params=params)
        response.raise_for_status()
        return response.json()

    async def get_pipelines(self) -> List[Dict[str, Any]]:
        """
        Get pipeline configurations.

        Automatically uses the correct endpoint for Cloud or self-hosted deployments:
        - Cloud: /api/v1/m/{group}/pipelines
        - Self-hosted: /api/v1/master/pipelines

        Returns:
            List of pipeline configurations

        Example:
            >>> pipelines = await client.get_pipelines()
            >>> for pipeline in pipelines:
            ...     print(f"{pipeline['id']}: {len(pipeline['functions'])} functions")
        """
        endpoint = self._build_config_endpoint("pipelines")
        response = await self.get(endpoint)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])

    async def get_routes(self) -> List[Dict[str, Any]]:
        """
        Get route configurations.

        Automatically uses the correct endpoint for Cloud or self-hosted deployments:
        - Cloud: /api/v1/m/{group}/routes
        - Self-hosted: /api/v1/master/routes

        Returns:
            List of route configurations

        Example:
            >>> routes = await client.get_routes()
            >>> for route in routes:
            ...     print(f"{route['id']}: {route['output']}")
        """
        endpoint = self._build_config_endpoint("routes")
        response = await self.get(endpoint)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])

    async def get_inputs(self) -> List[Dict[str, Any]]:
        """
        Get input configurations.

        Automatically uses the correct endpoint for Cloud or self-hosted deployments:
        - Cloud: /api/v1/m/{group}/inputs
        - Self-hosted: /api/v1/master/inputs

        Returns:
            List of input configurations

        Example:
            >>> inputs = await client.get_inputs()
            >>> for input_cfg in inputs:
            ...     print(f"{input_cfg['id']}: {input_cfg['type']}")
        """
        endpoint = self._build_config_endpoint("inputs")
        response = await self.get(endpoint)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])

    async def get_outputs(self) -> List[Dict[str, Any]]:
        """
        Get output/destination configurations.

        Automatically uses the correct endpoint for Cloud or self-hosted deployments:
        - Cloud: /api/v1/m/{group}/outputs
        - Self-hosted: /api/v1/master/outputs

        Returns:
            List of output configurations

        Example:
            >>> outputs = await client.get_outputs()
            >>> for output in outputs:
            ...     print(f"{output['id']}: {output['type']}")
        """
        endpoint = self._build_config_endpoint("outputs")
        response = await self.get(endpoint)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])

    async def get_license_info(self) -> dict:
        """
        Get license information including consumption and allocation.

        Returns:
            License information with daily_gb_limit and current_daily_gb

        Example:
            >>> license_info = await client.get_license_info()
            >>> print(f"License: {license_info['current_daily_gb']}/{license_info['daily_gb_limit']} GB/day")
        """
        endpoint = f"{self.base_url}/api/v1/system/limits"
        response = await self.get(endpoint)
        response.raise_for_status()
        data = response.json()

        # Transform to expected format
        return {
            "daily_gb_limit": data.get("dailyVolumeQuota", 0) / (1024 ** 3) if data.get("dailyVolumeQuota") else 0,
            "current_daily_gb": data.get("currentDailyVolume", 0) / (1024 ** 3) if data.get("currentDailyVolume") else 0,
        }

    def get_api_calls_remaining(self) -> int:
        """
        Get number of API calls remaining in budget.

        Returns:
            Number of remaining API calls

        Example:
            >>> remaining = client.get_api_calls_remaining()
            >>> print(f"{remaining} API calls remaining")
        """
        return self.rate_limiter.get_remaining_calls()

    def get_api_calls_used(self) -> int:
        """
        Get number of API calls used.

        Returns:
            Number of API calls made

        Example:
            >>> used = client.get_api_calls_used()
            >>> print(f"Used {used}/100 API calls")
        """
        return self.rate_limiter.total_calls_made

    # -------------------------------------------------------------------------
    # Cribl Lake API Methods
    # -------------------------------------------------------------------------

    async def get_lake_datasets(
        self,
        lake_name: str = "default",
        include_metrics: bool = False,
        storage_location_id: Optional[str] = None
    ) -> dict:
        """
        Get Lake datasets.

        Uses product-scoped endpoint pattern:
        /api/v1/products/lake/lakes/{lake_name}/datasets

        Args:
            lake_name: Lake name (default: "default")
            include_metrics: Include dataset metrics in response
            storage_location_id: Filter by storage location ID

        Returns:
            Dict with "items" (list of datasets) and "count" (total count)

        Example:
            >>> datasets = await client.get_lake_datasets(include_metrics=True)
            >>> for ds in datasets["items"]:
            ...     print(f"{ds['id']}: {ds['retentionPeriodInDays']} days")
        """
        endpoint = f"{self.base_url}/api/v1/products/lake/lakes/{lake_name}/datasets"

        # Build query parameters
        params = {}
        if include_metrics:
            params["includeMetrics"] = "true"
        if storage_location_id:
            params["storageLocationId"] = storage_location_id

        response = await self.get(endpoint, params=params if params else None)
        response.raise_for_status()
        return response.json()

    async def get_lake_dataset_stats(self, lake_name: str = "default") -> dict:
        """
        Get Lake dataset statistics.

        Args:
            lake_name: Lake name (default: "default")

        Returns:
            Dict with "items" (list of dataset stats) and "count"

        Example:
            >>> stats = await client.get_lake_dataset_stats()
            >>> for stat in stats["items"]:
            ...     print(f"{stat['datasetId']}: {stat['sizeBytes']} bytes")
        """
        endpoint = f"{self.base_url}/api/v1/products/lake/lakes/{lake_name}/datasets/stats"
        response = await self.get(endpoint)
        response.raise_for_status()
        return response.json()

    async def get_lake_lakehouses(self, lake_name: str = "default") -> dict:
        """
        Get Lake lakehouses.

        Args:
            lake_name: Lake name (default: "default")

        Returns:
            Dict with "items" (list of lakehouses) and "count"

        Example:
            >>> lakehouses = await client.get_lake_lakehouses()
            >>> for lh in lakehouses["items"]:
            ...     print(f"{lh['id']}: {lh['status']}")
        """
        endpoint = f"{self.base_url}/api/v1/products/lake/lakes/{lake_name}/lakehouses"
        response = await self.get(endpoint)
        response.raise_for_status()
        return response.json()
