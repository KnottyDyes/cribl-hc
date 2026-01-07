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
        candidates = ["default", "defaultGroup", "workers", "main"]
        for group_name in candidates:
            try:
                test_endpoint = f"/api/v1/m/{group_name}/pipelines"
                response = await self._client.get(test_endpoint)
                if response.status_code == 200:
                    self._worker_group = group_name
                    self._deployment_detected = True
                    return
            except Exception:
                continue
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
                    version = items[0].get("BUILD", {}).get("version", "unknown")
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

    async def get_workers(self) -> list[dict[str, Any]]:
        response = await self.get("/api/v1/master/workers")
        response.raise_for_status()
        return response.json().get("items", [])

    async def get_worker_groups(self) -> list[dict[str, Any]]:
        response = await self.get("/api/v1/master/groups")
        response.raise_for_status()
        return response.json().get("items", [])

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

    def get_api_calls_used(self) -> int:
        return self.rate_limiter.total_calls_made
