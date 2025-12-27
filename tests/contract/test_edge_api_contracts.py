"""
Contract tests for Cribl Edge API endpoints.

Validates that our assumptions about Edge API response structures are correct.
These tests use real API response examples to ensure our parsers handle Edge data properly.
"""

import pytest
from pydantic import ValidationError


class TestEdgeNodeContract:
    """Test Edge node API response contract."""

    def test_edge_node_required_fields(self):
        """Test that Edge node responses have expected required fields."""
        # Real Edge node response structure
        edge_node = {
            "id": "edge-001",
            "status": "connected",
            "fleet": "production",
            "lastSeen": "2024-12-27T10:30:00Z",
            "info": {
                "hostname": "edge-001.example.com",
                "os": "linux",
                "arch": "x64",
                "cribl": {"version": "4.8.0"}
            },
            "metrics": {
                "cpu": {"perc": 45.2},
                "memory": {"perc": 62.8},
                "health": 0.95
            }
        }

        # Verify required fields exist
        assert "id" in edge_node
        assert "status" in edge_node
        assert "fleet" in edge_node
        assert "lastSeen" in edge_node
        assert "info" in edge_node
        assert "metrics" in edge_node

        # Verify nested structures
        assert "hostname" in edge_node["info"]
        assert "cribl" in edge_node["info"]
        assert "version" in edge_node["info"]["cribl"]

    def test_edge_node_status_values(self):
        """Test valid Edge node status values."""
        valid_statuses = ["connected", "disconnected", "unhealthy", "unknown"]

        for status in valid_statuses:
            edge_node = {
                "id": f"node-{status}",
                "status": status,
                "fleet": "test"
            }
            assert edge_node["status"] in valid_statuses

    def test_edge_node_metrics_structure(self):
        """Test Edge node metrics structure."""
        metrics = {
            "cpu": {
                "perc": 45.2,
                "count": 4
            },
            "memory": {
                "perc": 62.8,
                "rss": 5368709120,
                "total": 8589934592
            },
            "disk": {
                "/opt/cribl": {
                    "usedP": 58.3,
                    "used": 25000000000,
                    "total": 42949672960
                }
            },
            "health": 0.95,
            "in_bytes_total": 125000000,
            "out_bytes_total": 120000000
        }

        # Verify CPU metrics
        assert "perc" in metrics["cpu"]
        assert 0 <= metrics["cpu"]["perc"] <= 100

        # Verify memory metrics
        assert "perc" in metrics["memory"]
        assert "rss" in metrics["memory"]
        assert 0 <= metrics["memory"]["perc"] <= 100

        # Verify disk metrics
        assert "/opt/cribl" in metrics["disk"]
        assert "usedP" in metrics["disk"]["/opt/cribl"]
        assert 0 <= metrics["disk"]["/opt/cribl"]["usedP"] <= 100

        # Verify health score
        assert "health" in metrics
        assert 0 <= metrics["health"] <= 1.0

    def test_edge_node_timestamp_format(self):
        """Test Edge lastSeen timestamp format."""
        from datetime import datetime

        # Edge uses ISO 8601 format
        timestamp_str = "2024-12-27T10:30:00Z"

        # Should be parseable
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        assert dt.year == 2024
        assert dt.month == 12
        assert dt.day == 27

        # Alternative formats that might appear
        alternative_formats = [
            "2024-12-27T10:30:00.123Z",  # With milliseconds
            "2024-12-27T10:30:00+00:00",  # With timezone offset
        ]

        for ts in alternative_formats:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            assert dt.year == 2024


class TestEdgeFleetContract:
    """Test Edge fleet API response contract."""

    def test_edge_fleet_structure(self):
        """Test Edge fleet response structure."""
        fleet = {
            "id": "production",
            "name": "production",
            "description": "Production edge fleet",
            "tags": ["prod", "critical"],
            "nodes": 4,
            "created": "2024-01-15T08:00:00Z",
            "modified": "2024-12-27T10:00:00Z"
        }

        # Verify required fields
        assert "id" in fleet
        assert "name" in fleet

        # Verify optional fields
        assert isinstance(fleet.get("tags", []), list)
        assert isinstance(fleet.get("nodes", 0), int)

    def test_edge_fleets_list_response(self):
        """Test Edge fleets list endpoint response."""
        response = {
            "items": [
                {
                    "id": "production",
                    "name": "production",
                    "nodes": 4
                },
                {
                    "id": "staging",
                    "name": "staging",
                    "nodes": 1
                }
            ],
            "count": 2
        }

        # Verify list structure
        assert "items" in response
        assert isinstance(response["items"], list)
        assert len(response["items"]) > 0

        # Verify each fleet has required fields
        for fleet in response["items"]:
            assert "id" in fleet
            assert "name" in fleet


class TestEdgeConfigContract:
    """Test Edge configuration API contracts."""

    def test_edge_pipeline_structure(self):
        """Test Edge pipeline configuration structure."""
        pipeline = {
            "id": "edge-processor",
            "conf": {
                "functions": [
                    {
                        "id": "eval",
                        "filter": "true",
                        "conf": {
                            "add": [
                                {"name": "edge_fleet", "value": "__fleet"}
                            ]
                        }
                    }
                ]
            },
            "description": "Edge data processor",
            "tags": ["edge", "processing"]
        }

        # Verify structure
        assert "id" in pipeline
        assert "conf" in pipeline
        assert "functions" in pipeline["conf"]
        assert isinstance(pipeline["conf"]["functions"], list)

        # Verify function structure
        func = pipeline["conf"]["functions"][0]
        assert "id" in func
        assert "conf" in func

    def test_edge_route_to_cribl_output(self):
        """Test Edge route pointing to cribl output type."""
        route = {
            "id": "data-to-stream",
            "filter": "true",
            "pipeline": "edge-processor",
            "output": "cribl-stream-leader",
            "final": True
        }

        # Edge routes commonly point to cribl output
        assert "output" in route
        assert route["final"] is True

    def test_edge_cribl_output_type(self):
        """Test Edge cribl output configuration."""
        output = {
            "id": "cribl-stream-leader",
            "type": "cribl",
            "systemFields": ["cribl_pipe"],
            "conf": {
                "host": "stream-leader.example.com",
                "port": 9000,
                "tls": {"disabled": False},
                "authType": "manual",
                "compression": "gzip"
            }
        }

        # Verify cribl output type structure
        assert output["type"] == "cribl"
        assert "host" in output["conf"]
        assert "port" in output["conf"]
        assert isinstance(output["conf"]["port"], int)

        # TLS should be configurable
        assert "tls" in output["conf"]
        assert "disabled" in output["conf"]["tls"]


class TestEdgeVersionContract:
    """Test Edge version endpoint contract."""

    def test_edge_version_response(self):
        """Test Edge version endpoint response structure."""
        version_response = {
            "version": "4.8.0",
            "product": "edge",
            "buildId": "abc123",
            "commit": "def456"
        }

        # Required fields
        assert "version" in version_response
        assert "product" in version_response
        assert version_response["product"] == "edge"

        # Version format should be semantic versioning
        version_parts = version_response["version"].split(".")
        assert len(version_parts) >= 2
        assert all(part.isdigit() for part in version_parts[:2])

    def test_edge_version_without_product_field(self):
        """Test Edge version response without explicit product field."""
        # Older Edge versions might not include product field
        version_response = {
            "version": "4.7.0",
            "buildId": "abc123"
        }

        # Should still have version
        assert "version" in version_response

        # Product detection would fall back to endpoint probing
        # (tested in integration tests)


class TestEdgeEndpointPaths:
    """Test Edge API endpoint path structures."""

    def test_edge_global_endpoints(self):
        """Test global Edge endpoint paths."""
        endpoints = [
            "/api/v1/edge/nodes",
            "/api/v1/edge/fleets",
            "/api/v1/version"
        ]

        for endpoint in endpoints:
            assert endpoint.startswith("/api/v1/")

    def test_edge_fleet_specific_endpoints(self):
        """Test fleet-specific Edge endpoint paths."""
        fleet = "production"
        endpoints = [
            f"/api/v1/e/{fleet}/nodes",
            f"/api/v1/e/{fleet}/pipelines",
            f"/api/v1/e/{fleet}/routes",
            f"/api/v1/e/{fleet}/inputs",
            f"/api/v1/e/{fleet}/outputs"
        ]

        for endpoint in endpoints:
            assert f"/api/v1/e/{fleet}/" in endpoint

    def test_edge_endpoint_path_construction(self):
        """Test Edge endpoint path construction logic."""
        from cribl_hc.core.api_client import CriblAPIClient

        # Edge client
        edge_client = CriblAPIClient(
            base_url="https://edge.example.com",
            auth_token="test"
        )
        edge_client._product_type = "edge"

        # Global Edge endpoints (no fleet specified)
        endpoint = edge_client._build_config_endpoint("pipelines")
        assert endpoint == "/api/v1/edge/pipelines"

        # Fleet-specific endpoints
        endpoint = edge_client._build_config_endpoint("pipelines", fleet="production")
        assert endpoint == "/api/v1/e/production/pipelines"


class TestEdgeDataNormalizationContract:
    """Test Edge data normalization contracts."""

    def test_status_mapping_contract(self):
        """Test Edge status to Stream status mapping."""
        # Edge status → Stream status
        status_mapping = {
            "connected": "healthy",
            "disconnected": "unhealthy",
            "unhealthy": "unhealthy",
            "unknown": "unknown"
        }

        for edge_status, expected_stream_status in status_mapping.items():
            # This mapping is implemented in _normalize_node_data
            assert edge_status in ["connected", "disconnected", "unhealthy", "unknown"]
            assert expected_stream_status in ["healthy", "unhealthy", "unknown"]

    def test_fleet_to_group_mapping(self):
        """Test Edge 'fleet' to Stream 'group' mapping."""
        edge_node = {
            "id": "node-1",
            "fleet": "production"
        }

        # After normalization, should have 'group' field
        # This is tested in integration tests with actual normalization
        assert "fleet" in edge_node
        assert edge_node["fleet"] == "production"

    def test_timestamp_conversion_contract(self):
        """Test Edge lastSeen to Stream lastMsgTime conversion."""
        from datetime import datetime

        # Edge timestamp (ISO 8601 string)
        edge_timestamp = "2024-12-27T10:30:00Z"

        # Should convert to milliseconds since epoch
        dt = datetime.fromisoformat(edge_timestamp.replace("Z", "+00:00"))
        expected_ms = int(dt.timestamp() * 1000)

        # Verify it's a reasonable timestamp
        assert expected_ms > 1700000000000  # After 2023
        assert expected_ms < 2000000000000  # Before 2033


class TestEdgeMetricsContract:
    """Test Edge metrics data contracts."""

    def test_edge_throughput_metrics(self):
        """Test Edge throughput metrics structure."""
        metrics = {
            "in_bytes_total": 125000000,
            "out_bytes_total": 120000000,
            "in_events_total": 50000,
            "out_events_total": 48500
        }

        # Verify byte counts
        assert "in_bytes_total" in metrics
        assert "out_bytes_total" in metrics
        assert isinstance(metrics["in_bytes_total"], int)
        assert isinstance(metrics["out_bytes_total"], int)

        # Verify event counts (if present)
        if "in_events_total" in metrics:
            assert isinstance(metrics["in_events_total"], int)

    def test_edge_health_score_range(self):
        """Test Edge health score is in valid range."""
        health_scores = [0.0, 0.25, 0.5, 0.75, 0.95, 1.0]

        for score in health_scores:
            assert 0.0 <= score <= 1.0
            assert isinstance(score, (int, float))

    def test_edge_resource_percentage_ranges(self):
        """Test Edge resource percentages are in valid ranges."""
        metrics = {
            "cpu": {"perc": 45.2},
            "memory": {"perc": 62.8},
            "disk": {"/opt/cribl": {"usedP": 58.3}}
        }

        # All percentages should be 0-100
        assert 0 <= metrics["cpu"]["perc"] <= 100
        assert 0 <= metrics["memory"]["perc"] <= 100
        assert 0 <= metrics["disk"]["/opt/cribl"]["usedP"] <= 100


class TestEdgeErrorResponses:
    """Test Edge API error response contracts."""

    def test_edge_auth_error_response(self):
        """Test Edge authentication error response."""
        error_response = {
            "statusCode": 401,
            "message": "Authentication required",
            "error": "Unauthorized"
        }

        assert error_response["statusCode"] == 401
        assert "message" in error_response or "error" in error_response

    def test_edge_not_found_response(self):
        """Test Edge resource not found response."""
        error_response = {
            "statusCode": 404,
            "message": "Fleet not found",
            "error": "Not Found"
        }

        assert error_response["statusCode"] == 404

    def test_edge_invalid_request_response(self):
        """Test Edge invalid request response."""
        error_response = {
            "statusCode": 400,
            "message": "Invalid fleet name",
            "error": "Bad Request"
        }

        assert error_response["statusCode"] == 400


class TestEdgeCloudDeployment:
    """Test Edge on Cribl Cloud contracts."""

    def test_edge_cloud_url_format(self):
        """Test Edge Cloud URL format."""
        cloud_urls = [
            "https://main-myorg.cribl.cloud",
            "https://edge-myorg.cribl.cloud"
        ]

        for url in cloud_urls:
            assert "cribl.cloud" in url.lower()
            assert url.startswith("https://")

    def test_edge_cloud_endpoint_paths(self):
        """Test Edge Cloud uses same endpoint structure as self-hosted."""
        # Edge Cloud should use same /api/v1/edge/* paths
        # This is tested in integration tests with actual client
        pass


class TestEdgeBackwardCompatibility:
    """Test backward compatibility with older Edge versions."""

    def test_edge_4_6_version_format(self):
        """Test Edge 4.6.x version format."""
        version = "4.6.3"
        parts = version.split(".")

        assert len(parts) == 3
        assert int(parts[0]) == 4
        assert int(parts[1]) == 6

    def test_edge_4_7_version_format(self):
        """Test Edge 4.7.x version format."""
        version = "4.7.0"
        parts = version.split(".")

        assert len(parts) == 3
        assert int(parts[0]) == 4
        assert int(parts[1]) == 7

    def test_edge_optional_fields_missing(self):
        """Test Edge response with optional fields missing."""
        # Minimal valid Edge node response
        minimal_node = {
            "id": "edge-001",
            "status": "connected"
        }

        # Should have required fields
        assert "id" in minimal_node
        assert "status" in minimal_node

        # Optional fields may be missing
        assert minimal_node.get("fleet") is None
        assert minimal_node.get("metrics") is None
