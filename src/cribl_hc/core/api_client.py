from datetime import datetime
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, Field

from cribl_hc.utils.logger import get_logger
from cribl_hc.utils.rate_limiter import RateLimiter

log = get_logger(__name__)


class ConnectionTestResult(BaseModel):
    success: bool = Field(..., description="Connection test success status")
    message: str = Field(..., description="Human-readable status message")
    response_time_ms: Optional[float] = Field(
        default=None, description="API response time in milliseconds"
    )
    cribl_version: Optional[str] = Field(default=None, description="Detected Cribl version")
    api_url: str = Field(..., description="API URL tested")
    error: Optional[str] = Field(default=None, description="Error details if failed")
    tested_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}


class CriblAPIClient:
    def __init__(
        self,
        base_url: str,
        auth_token: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limiter: Optional[RateLimiter] = None,
        worker_group: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._is_cloud = "cribl.cloud" in base_url.lower()
        self._worker_group = worker_group
        self._deployment_detected = False
        self._product_type: Optional[str] = None
        self._product_version: Optional[str] = None
        self.rate_limiter = rate_limiter or RateLimiter(
            max_calls=100,
            time_window_seconds=3600.0,
            enable_backoff=True,
        )

    async def __aenter__(self):
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
        if self._is_cloud and not self._worker_group:
            await self._detect_worker_group()
        return self

    async def _detect_worker_group(self) -> None:
        if not self._client:
            return

        if await self._try_api_discovery():
            return

        await self._try_fallback_candidates()

    async def _try_api_discovery(self) -> bool:
        if not self._client:
            return False
        try:
            response = await self._client.get("/api/v1/master/groups")
            if response.status_code == 200:
                groups = response.json() or []
                return await self._test_available_groups(groups)
        except Exception:
            pass
        return False

    async def _test_available_groups(self, groups: list) -> bool:
        for group in groups:
            if isinstance(group, dict):
                group_id = group.get("id", "")
                if self._is_stream_group(group_id) and await self._test_group_access(group_id):
                    self._worker_group = group_id
                    self._deployment_detected = True
                    return True
        return False

    def _is_stream_group(self, group_id: str | None) -> bool:
        return bool(group_id and not group_id.startswith("edge_"))

    async def _test_group_access(self, group_id: str) -> bool:
        if not self._client:
            return False
        try:
            test_endpoint = f"/api/v1/m/{group_id}/pipelines"
            test_response = await self._client.get(test_endpoint)
            return test_response.status_code == 200
        except Exception:
            return False

    async def _try_fallback_candidates(self) -> None:
        candidates = ["default", "defaultGroup", "workers", "main"]
        for group_name in candidates:
            if await self._test_group_access(group_name):
                self._worker_group = group_name
                self._deployment_detected = True
                return
        self._worker_group = "default"
        self._deployment_detected = True

    @property
    def is_cloud(self) -> bool:
        return self._is_cloud

    @property
    def worker_group(self) -> str:
        return self._worker_group or "default"

    @property
    def product_type(self) -> Optional[str]:
        return self._product_type

    @property
    def is_stream(self) -> bool:
        return self._product_type == "stream"

    @property
    def is_edge(self) -> bool:
        return self._product_type == "edge"

    @property
    def is_lake(self) -> bool:
        return self._product_type == "lake"

    @property
    def product_version(self) -> Optional[str]:
        return self._product_version

    async def _detect_product_type(self, version_info: dict[str, Any]) -> None:
        if not version_info:
            self._product_type = "stream"
            return
        product = version_info.get("product", "").lower()
        if product in ["stream", "edge", "lake"]:
            self._product_type = product
            self._product_version = version_info.get("version")
            return
        if self._client:
            try:
                response = await self._client.get("/api/v1/edge/fleets")
                if response.status_code in [200, 401, 403]:
                    self._product_type = "edge"
                    self._product_version = version_info.get("version")
                    return
            except Exception:
                pass
            try:
                response = await self._client.get("/api/v1/datasets")
                if response.status_code in [200, 401, 403]:
                    self._product_type = "lake"
                    self._product_version = version_info.get("version")
                    return
            except Exception:
                pass
        self._product_type = "stream"
        self._product_version = version_info.get("version")

    def _build_config_endpoint(self, resource: str, fleet: Optional[str] = None) -> str:
        if self.is_edge:
            return f"/api/v1/e/{fleet}/{resource}" if fleet else f"/api/v1/edge/{resource}"
        elif self._is_cloud:
            group = self.worker_group
            if resource in ("inputs", "outputs"):
                return f"/api/v1/m/{group}/system/{resource}"
            return f"/api/v1/m/{group}/{resource}"
        return f"/api/v1/master/{resource}"

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def test_connection(self) -> ConnectionTestResult:
        if not self._client:
            return ConnectionTestResult(
                success=False,
                message="Client not initialized",
                api_url=self.base_url,
                error="Client not initialized",
            )
        endpoint = "/api/v1/system/info"
        test_url = urljoin(self.base_url, endpoint)
        start_time = datetime.utcnow()
        try:
            async with self.rate_limiter:
                response = await self._client.get(endpoint)
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            if response.status_code == 200:
                data = response.json()
                version = "unknown"
                items = data.get("items", [])
                if items and len(items) > 0:
                    version = items[0].get("BUILD", {}).get("VERSION", "unknown")
                if version == "unknown":
                    version = data.get("version", "unknown")
                if not self._product_type:
                    await self._detect_product_type(data)
                product_name = {
                    "stream": "Cribl Stream",
                    "edge": "Cribl Edge",
                    "lake": "Cribl Lake",
                }.get(self._product_type or "stream", "Cribl")
                return ConnectionTestResult(
                    success=True,
                    message=f"Successfully connected to {product_name} {version}",
                    response_time_ms=round(elapsed_ms, 2),
                    cribl_version=version,
                    api_url=test_url,
                )
            return ConnectionTestResult(
                success=False,
                message=f"Unexpected response code: {response.status_code}",
                response_time_ms=round(elapsed_ms, 2),
                cribl_version=None,
                api_url=test_url,
                error=f"HTTP {response.status_code}: {response.text}",
            )
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message="Connection test failed",
                response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                cribl_version=None,
                api_url=test_url,
                error=str(e),
            )

    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        if not self._client:
            raise RuntimeError("Client not initialized")
        async with self.rate_limiter:
            return await self._client.get(endpoint, **kwargs)

    async def get_pipelines(self) -> list[dict[str, Any]]:
        response = await self.get(self._build_config_endpoint("pipelines"))
        response.raise_for_status()
        return response.json().get("items", [])

    async def get_routes(self) -> list[dict[str, Any]]:
        response = await self.get(self._build_config_endpoint("routes"))
        response.raise_for_status()
        return response.json().get("items", [])

    async def get_inputs(self) -> list[dict[str, Any]]:
        response = await self.get(self._build_config_endpoint("inputs"))
        response.raise_for_status()
        return response.json().get("items", [])

    async def get_outputs(self) -> list[dict[str, Any]]:
        response = await self.get(self._build_config_endpoint("outputs"))
        response.raise_for_status()
        return response.json().get("items", [])

    async def get_parsers(self) -> list[dict[str, Any]]:
        endpoint = self._build_config_endpoint("parsers")
        response = await self.get(endpoint)
        response.raise_for_status()
        return response.json().get("items", [])

    async def get_workers(self) -> list[dict[str, Any]]:
        response = await self.get("/api/v1/master/workers")
        response.raise_for_status()
        return response.json().get("items", [])

    async def get_worker_groups(self) -> list[dict[str, Any]]:
        response = await self.get("/api/v1/master/groups")
        response.raise_for_status()
        return response.json().get("items", [])

    def get_worker_group_type(self, group: dict[str, Any]) -> str:
        """
        Determine the type of a worker group based on its properties.

        Args:
            group: Worker group object from API

        Returns:
            str: One of 'on_prem', 'cloud_managed', or 'hybrid'
        """
        # Check if it's an Edge Fleet (different from worker groups)
        if group.get("isFleet", False):
            return "edge_fleet"

        # Check if it's a Search group
        if group.get("isSearch", False):
            return "search_group"

        # For Stream worker groups, determine deployment type
        on_prem = group.get("onPrem", True)  # Default to True for backward compatibility
        provisioned = group.get("provisioned", False)

        if on_prem:
            return "on_prem"
        elif provisioned:
            return "cloud_managed"  # Cribl-managed workers in cloud
        else:
            return "hybrid"  # Customer-managed workers in cloud deployment

    async def get_worker_groups_by_type(self) -> dict[str, list[dict[str, Any]]]:
        """
        Get worker groups categorized by their deployment type.

        Returns:
            dict: Worker groups categorized by type:
                - on_prem: Traditional on-premises worker groups
                - cloud_managed: Cribl-managed workers in Cribl.Cloud
                - hybrid: Customer-managed workers in cloud deployments
                - edge_fleet: Cribl Edge fleets
                - search_group: Cribl Search groups
        """
        groups = await self.get_worker_groups()
        by_type = {
            "on_prem": [],
            "cloud_managed": [],
            "hybrid": [],
            "edge_fleet": [],
            "search_group": [],
        }

        for group in groups:
            group_type = self.get_worker_group_type(group)
            by_type[group_type].append(group)

        return by_type

    async def get_master_summary(self) -> dict[str, Any]:
        response = await self.get("/api/v1/master/summary")
        response.raise_for_status()
        return response.json()

    async def get_nodes(self) -> list[dict[str, Any]]:
        endpoint = "/api/v1/edge/nodes" if self.is_edge else "/api/v1/master/workers"
        response = await self.get(endpoint)
        response.raise_for_status()
        return response.json().get("items", [])

    def _normalize_node_data(self, node: dict[str, Any]) -> dict[str, Any]:
        return node

    async def get_system_status(self) -> dict[str, Any]:
        try:
            response = await self.get("/api/v1/system/status")
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}

    async def get_auth_config(self) -> dict[str, Any]:
        try:
            response = await self.get("/api/v1/system/auth")
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}

    async def get_system_messages(self) -> list[dict[str, Any]]:
        try:
            response = await self.get("/api/v1/system/messages")
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception:
            return []

    async def get_banners(self) -> list[dict[str, Any]]:
        try:
            response = await self.get("/api/v1/system/banners")
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception:
            return []

    async def get_certificates(self) -> list[dict[str, Any]]:
        try:
            response = await self.get("/api/v1/system/certificates")
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception:
            return []

    async def get_roles(self) -> list[dict[str, Any]]:
        try:
            response = await self.get("/api/v1/system/roles")
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception:
            return []

    async def get_users(self) -> list[dict[str, Any]]:
        try:
            response = await self.get("/api/v1/system/users")
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception:
            return []

    async def get_api_keys(self) -> list[dict[str, Any]]:
        try:
            response = await self.get("/api/v1/system/keys")
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception:
            return []

    async def get_teams(self) -> list[dict[str, Any]]:
        try:
            response = await self.get("/api/v1/system/teams")
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception:
            return []

    async def get_lookups(self) -> list[dict[str, Any]]:
        endpoint = self._build_config_endpoint("lookups")
        response = await self.get(endpoint)
        response.raise_for_status()
        return response.json().get("items", [])

    async def get_notification_targets(self) -> list[dict[str, Any]]:
        try:
            response = await self.get("/api/v1/system/notifications/targets")
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception:
            return []

    async def get_notifications(self) -> list[dict[str, Any]]:
        try:
            response = await self.get("/api/v1/system/notifications")
            response.raise_for_status()
            return response.json().get("items", [])
        except Exception:
            return []

    async def get_metrics(self, time_range: str = "1h") -> dict[str, Any]:
        if self._is_cloud:
            endpoint = f"/api/v1/m/{self.worker_group}/system/metrics"
        else:
            endpoint = "/api/v1/system/metrics"

        params = {}

        try:
            response = await self.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except Exception:
            log.warning(
                "metrics_unavailable",
                endpoint=endpoint,
                cloud=self._is_cloud,
                error="Metrics endpoint not available or failed",
            )
            return {}

    async def get_version_info(self) -> dict[str, Any]:
        try:
            response = await self.get("/api/v1/system/info")
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}

    async def get_search_jobs(self, workspace: str = "default_search") -> dict:
        response = await self.get(f"/api/v1/m/{workspace}/search/jobs")
        response.raise_for_status()
        return response.json()

    async def get_search_datasets(self, workspace: str = "default_search") -> dict:
        response = await self.get(f"/api/v1/m/{workspace}/search/datasets")
        response.raise_for_status()
        return response.json()

    async def get_search_dashboards(self, workspace: str = "default_search") -> dict:
        response = await self.get(f"/api/v1/m/{workspace}/search/dashboards")
        response.raise_for_status()
        return response.json()

    async def get_search_saved_searches(self, workspace: str = "default_search") -> dict:
        response = await self.get(f"/api/v1/m/{workspace}/search/saved")
        response.raise_for_status()
        return response.json()

    async def get_search_groups(self, workspace: str = "default_search") -> dict:
        response = await self.get(f"/api/v1/m/{workspace}/search/groups")
        response.raise_for_status()
        return response.json()

    async def get_search_cost(self, workspace: str = "default_search", days: int = 30) -> dict:
        response = await self.get(f"/api/v1/m/{workspace}/search/cost", params={"days": days})
        response.raise_for_status()
        return response.json()

    async def get_search_datatypes(self, workspace: str = "default_search") -> dict:
        response = await self.get(f"/api/v1/m/{workspace}/search/datatypes")
        response.raise_for_status()
        return response.json()

    async def get_lake_datasets(self, include_metrics: bool = False) -> dict:
        params = {"includeMetrics": str(include_metrics).lower()}
        response = await self.get("/api/v1/products/lake/datasets", params=params)
        response.raise_for_status()
        return response.json()

    async def get_lake_lakehouses(self) -> dict:
        response = await self.get("/api/v1/products/lake/lakehouses")
        response.raise_for_status()
        return response.json()

    async def get_lake_storage_locations(self, lake_name: str = "default") -> dict:
        response = await self.get(f"/api/v1/products/lake/lakes/{lake_name}/storage_locations")
        response.raise_for_status()
        return response.json()

    async def capture_events(
        self,
        filter_expr: str = "true",
        max_events: int = 10,
        duration: int = 10,
        level: int = 1,
        worker_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        if not self._client:
            raise RuntimeError("Client not initialized")

        if self._is_cloud:
            endpoint = f"/api/v1/m/{self.worker_group}/system/capture"
        else:
            endpoint = "/api/v1/system/capture"

        payload = {
            "filter": filter_expr,
            "maxEvents": max_events,
            "duration": duration * 1000,
            "level": level,
        }
        if worker_id:
            payload["workerId"] = worker_id

        async with self.rate_limiter:
            response = await self._client.post(endpoint, json=payload)

        response.raise_for_status()
        data = response.json()
        return data.get("items", [])

    def get_api_calls_used(self) -> int:
        return self.rate_limiter.total_calls_made
