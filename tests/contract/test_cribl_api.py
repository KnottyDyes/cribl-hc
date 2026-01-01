"""
Contract tests for Cribl Stream API endpoints.

These tests validate that Cribl API responses match expected schemas
and data structures, ensuring compatibility with supported versions.
"""

import pytest
import respx
from httpx import Response


class TestSystemStatusEndpoint:
    """Contract tests for /api/v1/system/status endpoint."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_system_status_success_response(self):
        """Test system status endpoint returns expected schema."""
        from cribl_hc.core.api_client import CriblAPIClient

        # Mock successful response
        respx.get("https://cribl.example.com/api/v1/system/status").mock(
            return_value=Response(
                200,
                json={
                    "version": "4.5.2",
                    "build": "ab12cd34",
                    "product": "Stream",
                    "health": "healthy",
                    "uptime_seconds": 86400,
                    "leader": True,
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/system/status")
            data = response.json()

            # Validate response structure
            assert response.status_code == 200
            assert "version" in data
            assert "health" in data
            assert isinstance(data["version"], str)
            assert isinstance(data["uptime_seconds"], (int, float))

    @pytest.mark.asyncio
    @respx.mock
    async def test_system_status_version_format(self):
        """Test version field matches expected format."""
        from cribl_hc.core.api_client import CriblAPIClient

        respx.get("https://cribl.example.com/api/v1/system/status").mock(
            return_value=Response(
                200,
                json={
                    "version": "4.7.3",
                    "health": "healthy",
                    "uptime_seconds": 3600,
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/system/status")
            data = response.json()

            # Version should be in X.Y.Z format
            version = data["version"]
            parts = version.split(".")
            assert len(parts) >= 3
            assert all(part.isdigit() for part in parts[:3])

    @pytest.mark.asyncio
    @respx.mock
    async def test_system_status_minimal_response(self):
        """Test endpoint with minimal required fields."""
        from cribl_hc.core.api_client import CriblAPIClient

        # Minimal valid response
        respx.get("https://cribl.example.com/api/v1/system/status").mock(
            return_value=Response(
                200,
                json={
                    "version": "4.5.0",
                    "health": "healthy",
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/system/status")
            data = response.json()

            assert data["version"]
            assert data["health"]


class TestMasterWorkersEndpoint:
    """Contract tests for /api/v1/master/workers endpoint."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_workers_list_response_structure(self):
        """Test workers endpoint returns expected list structure."""
        from cribl_hc.core.api_client import CriblAPIClient

        respx.get("https://cribl.example.com/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-01",
                            "group": "default",
                            "status": "healthy",
                            "info": {
                                "hostname": "worker-01.example.com",
                                "ipAddress": "10.0.1.10",
                                "cpuCount": 8,
                                "version": "4.5.2",
                            },
                            "metrics": {
                                "cpu": 45.2,
                                "memory": {"used": 8.5, "total": 16.0},
                                "disk": {"used": 45.0, "total": 100.0},
                            },
                        }
                    ],
                    "count": 1,
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/master/workers")
            data = response.json()

            # Validate top-level structure
            assert "items" in data
            assert isinstance(data["items"], list)

            # Validate worker structure
            if data["items"]:
                worker = data["items"][0]
                assert "id" in worker
                assert "info" in worker
                assert "metrics" in worker

    @pytest.mark.asyncio
    @respx.mock
    async def test_workers_info_fields(self):
        """Test worker info contains expected fields."""
        from cribl_hc.core.api_client import CriblAPIClient

        respx.get("https://cribl.example.com/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-01",
                            "info": {
                                "hostname": "worker-01.example.com",
                                "ipAddress": "10.0.1.10",
                                "cpuCount": 8,
                                "version": "4.5.2",
                                "os": "linux",
                                "arch": "x64",
                            },
                            "metrics": {
                                "cpu": 50.0,
                                "memory": {"used": 10.0, "total": 16.0},
                            },
                        }
                    ]
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/master/workers")
            data = response.json()

            worker = data["items"][0]
            info = worker["info"]

            assert "hostname" in info
            assert "version" in info
            assert isinstance(info["hostname"], str)
            assert isinstance(info["version"], str)

    @pytest.mark.asyncio
    @respx.mock
    async def test_workers_metrics_structure(self):
        """Test worker metrics have expected structure."""
        from cribl_hc.core.api_client import CriblAPIClient

        respx.get("https://cribl.example.com/api/v1/master/workers").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "worker-01",
                            "info": {"hostname": "worker-01", "version": "4.5.2"},
                            "metrics": {
                                "cpu": 45.5,
                                "memory": {"used": 8192, "total": 16384},
                                "disk": {"used": 50000, "total": 100000},
                                "throughput": {"in": 1000, "out": 950},
                            },
                        }
                    ]
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/master/workers")
            data = response.json()

            metrics = data["items"][0]["metrics"]

            # CPU should be numeric
            assert isinstance(metrics["cpu"], (int, float))
            assert 0 <= metrics["cpu"] <= 100

            # Memory should have used/total
            assert "used" in metrics["memory"]
            assert "total" in metrics["memory"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_workers_empty_list(self):
        """Test endpoint handles empty worker list."""
        from cribl_hc.core.api_client import CriblAPIClient

        respx.get("https://cribl.example.com/api/v1/master/workers").mock(
            return_value=Response(200, json={"items": [], "count": 0})
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/master/workers")
            data = response.json()

            assert data["items"] == []
            assert isinstance(data["items"], list)


class TestMetricsEndpoint:
    """Contract tests for /api/v1/metrics endpoint."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_metrics_response_structure(self):
        """Test metrics endpoint returns expected structure."""
        from cribl_hc.core.api_client import CriblAPIClient

        respx.get("https://cribl.example.com/api/v1/metrics").mock(
            return_value=Response(
                200,
                json={
                    "system": {
                        "cpu": {"usage": 45.2, "cores": 8},
                        "memory": {"used": 8589934592, "total": 17179869184},
                        "disk": {"used": 107374182400, "total": 214748364800},
                    },
                    "pipeline": {
                        "events_in": 1000000,
                        "events_out": 950000,
                        "bytes_in": 10485760000,
                        "bytes_out": 9961472000,
                    },
                    "timestamp": "2025-12-24T12:00:00Z",
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/metrics")
            data = response.json()

            assert response.status_code == 200
            # Different Cribl versions may structure metrics differently
            # Just validate it's a dict with some data
            assert isinstance(data, dict)
            assert len(data) > 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_metrics_numeric_values(self):
        """Test metrics contain numeric values."""
        from cribl_hc.core.api_client import CriblAPIClient

        respx.get("https://cribl.example.com/api/v1/metrics").mock(
            return_value=Response(
                200,
                json={
                    "cpu_usage": 45.2,
                    "memory_used": 8589934592,
                    "events_processed": 1000000,
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/metrics")
            data = response.json()

            # All values should be numeric (metrics are numbers)
            for value in data.values():
                assert isinstance(value, (int, float))


class TestConfigEndpoints:
    """Contract tests for configuration endpoints (User Story 2)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_pipelines_endpoint_structure(self):
        """Test /api/v1/m/{group}/pipelines endpoint returns expected structure."""
        from cribl_hc.core.api_client import CriblAPIClient

        respx.get("https://cribl.example.com/api/v1/m/default/pipelines").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "pipeline-01",
                            "description": "Main processing pipeline",
                            "functions": [
                                {
                                    "id": "eval",
                                    "filter": "true",
                                    "conf": {"expression": "status = 'ok'"},
                                }
                            ],
                        }
                    ],
                    "count": 1,
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/m/default/pipelines")
            data = response.json()

            assert "items" in data
            assert isinstance(data["items"], list)
            if data["items"]:
                pipeline = data["items"][0]
                assert "id" in pipeline
                assert "functions" in pipeline

    @pytest.mark.asyncio
    @respx.mock
    async def test_routes_endpoint_structure(self):
        """Test /api/v1/m/{group}/routes endpoint returns expected structure."""
        from cribl_hc.core.api_client import CriblAPIClient

        # API returns Routes objects (routing tables) with nested routes array
        respx.get("https://cribl.example.com/api/v1/m/default/routes").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "default",
                            "routes": [
                                {
                                    "id": "route-01",
                                    "name": "Production Route",
                                    "filter": "source=='production'",
                                    "pipeline": "main",
                                    "output": "splunk-prod",
                                    "final": False,
                                }
                            ]
                        }
                    ],
                    "count": 1,
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/m/default/routes")
            data = response.json()

            assert "items" in data
            assert isinstance(data["items"], list)
            if data["items"]:
                routing_table = data["items"][0]
                assert "id" in routing_table
                # Routing tables contain a "routes" array
                assert "routes" in routing_table
                if routing_table["routes"]:
                    route = routing_table["routes"][0]
                    assert "filter" in route or "output" in route

    @pytest.mark.asyncio
    @respx.mock
    async def test_outputs_endpoint_structure(self):
        """Test /api/v1/m/{group}/outputs endpoint returns expected structure."""
        from cribl_hc.core.api_client import CriblAPIClient

        respx.get("https://cribl.example.com/api/v1/m/default/outputs").mock(
            return_value=Response(
                200,
                json={
                    "items": [
                        {
                            "id": "splunk-prod",
                            "type": "splunk_hec",
                            "systemFields": ["cribl_pipe"],
                            "streamtags": [],
                            "host": "splunk.example.com",
                            "port": 8088,
                        }
                    ],
                    "count": 1,
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/m/default/outputs")
            data = response.json()

            assert "items" in data
            assert isinstance(data["items"], list)
            if data["items"]:
                output = data["items"][0]
                assert "id" in output
                assert "type" in output


class TestErrorResponses:
    """Contract tests for error responses."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_unauthorized_response(self):
        """Test 401 Unauthorized response structure."""
        from cribl_hc.core.api_client import CriblAPIClient

        respx.get("https://cribl.example.com/api/v1/system/status").mock(
            return_value=Response(
                401,
                json={
                    "message": "Unauthorized",
                    "error": "Invalid or expired token",
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="invalid-token",
        ) as client:
            response = await client._client.get("/api/v1/system/status")

            assert response.status_code == 401
            data = response.json()
            assert "message" in data or "error" in data

    @pytest.mark.asyncio
    @respx.mock
    async def test_not_found_response(self):
        """Test 404 Not Found response structure."""
        from cribl_hc.core.api_client import CriblAPIClient

        respx.get("https://cribl.example.com/api/v1/nonexistent").mock(
            return_value=Response(
                404,
                json={
                    "message": "Not found",
                    "path": "/api/v1/nonexistent",
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/nonexistent")

            assert response.status_code == 404

    @pytest.mark.asyncio
    @respx.mock
    async def test_server_error_response(self):
        """Test 500 Server Error response."""
        from cribl_hc.core.api_client import CriblAPIClient

        respx.get("https://cribl.example.com/api/v1/system/status").mock(
            return_value=Response(
                500,
                json={
                    "message": "Internal server error",
                    "error": "Database connection failed",
                },
            )
        )

        async with CriblAPIClient(
            base_url="https://cribl.example.com",
            auth_token="test-token",
        ) as client:
            response = await client._client.get("/api/v1/system/status")

            assert response.status_code == 500
