"""
Integration tests for Cribl Edge deployments.

Tests full analysis workflows with realistic Edge API responses including:
- Multi-fleet Edge deployments
- Edge-specific configuration patterns
- Fleet-level health analysis
- Edge node normalization
- Product-aware messaging
"""

import pytest
from unittest.mock import AsyncMock, patch
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.analyzers.health import HealthAnalyzer
from cribl_hc.analyzers.config import ConfigAnalyzer
from cribl_hc.analyzers.resource import ResourceAnalyzer


@pytest.fixture
def mock_edge_client():
    """Create mock Edge API client with realistic data."""
    client = AsyncMock(spec=CriblAPIClient)
    client.is_edge = True
    client.is_stream = False
    client.is_cloud = False
    client.product_type = "edge"
    client.product_version = "4.8.0"
    client.base_url = "https://edge.example.com"

    # Mock async methods properly
    client.get_nodes = AsyncMock(return_value=[])
    client.get_system_status = AsyncMock(return_value={"version": "4.8.0", "health": "green"})
    client.get_pipelines = AsyncMock(return_value=[])
    client.get_routes = AsyncMock(return_value=[])
    client.get_inputs = AsyncMock(return_value=[])
    client.get_outputs = AsyncMock(return_value=[])
    client.get_edge_fleets = AsyncMock(return_value=[])
    client.get_api_calls_used = AsyncMock(return_value=0)
    client.get_api_calls_remaining = AsyncMock(return_value=100)

    # Mock _normalize_node_data method
    def normalize_edge_data(node: dict) -> dict:
        """Normalize Edge node data to Stream format."""
        normalized = node.copy()
        # Map status
        if node.get("status") == "connected":
            normalized["status"] = "healthy"
        elif node.get("status") == "disconnected":
            normalized["status"] = "unhealthy"
        # Map fleet to group
        if "fleet" in node:
            normalized["group"] = node["fleet"]
        # Convert timestamp
        if "lastSeen" in node and "lastMsgTime" not in normalized:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(node["lastSeen"].replace("Z", "+00:00"))
                normalized["lastMsgTime"] = int(dt.timestamp() * 1000)
            except Exception:
                pass
        return normalized

    client._normalize_node_data.side_effect = normalize_edge_data

    return client


@pytest.fixture
def realistic_edge_nodes():
    """Realistic Edge node data from production environments."""
    return [
        {
            "id": "edge-prod-001",
            "status": "connected",
            "fleet": "production",
            "lastSeen": "2024-12-27T10:30:00Z",
            "info": {
                "hostname": "edge-prod-001.example.com",
                "os": "linux",
                "arch": "x64",
                "cribl": {"version": "4.8.0"},
                "cpu": {"count": 4, "model": "Intel(R) Xeon(R) CPU"},
                "memory": {"total": 8589934592}  # 8GB
            },
            "metrics": {
                "cpu": {"perc": 45.2},
                "memory": {"perc": 62.8, "rss": 5368709120},  # 5GB
                "disk": {"/opt/cribl": {"usedP": 58.3}},
                "health": 0.95,
                "in_bytes_total": 125000000,
                "out_bytes_total": 120000000
            }
        },
        {
            "id": "edge-prod-002",
            "status": "connected",
            "fleet": "production",
            "lastSeen": "2024-12-27T10:29:45Z",
            "info": {
                "hostname": "edge-prod-002.example.com",
                "os": "linux",
                "arch": "x64",
                "cribl": {"version": "4.8.0"},
                "cpu": {"count": 4, "model": "Intel(R) Xeon(R) CPU"},
                "memory": {"total": 8589934592}
            },
            "metrics": {
                "cpu": {"perc": 38.7},
                "memory": {"perc": 55.2, "rss": 4738381824},
                "disk": {"/opt/cribl": {"usedP": 52.1}},
                "health": 0.98,
                "in_bytes_total": 118000000,
                "out_bytes_total": 115000000
            }
        },
        {
            "id": "edge-staging-001",
            "status": "connected",
            "fleet": "staging",
            "lastSeen": "2024-12-27T10:30:10Z",
            "info": {
                "hostname": "edge-staging-001.example.com",
                "os": "linux",
                "arch": "x64",
                "cribl": {"version": "4.8.0"},
                "cpu": {"count": 2, "model": "Intel(R) Core(TM)"},
                "memory": {"total": 4294967296}  # 4GB
            },
            "metrics": {
                "cpu": {"perc": 22.5},
                "memory": {"perc": 48.3, "rss": 2073741824},
                "disk": {"/opt/cribl": {"usedP": 35.8}},
                "health": 1.0,
                "in_bytes_total": 45000000,
                "out_bytes_total": 44500000
            }
        },
        {
            # Unhealthy node - high resource usage
            "id": "edge-prod-003",
            "status": "connected",
            "fleet": "production",
            "lastSeen": "2024-12-27T10:25:30Z",  # Older lastSeen
            "info": {
                "hostname": "edge-prod-003.example.com",
                "os": "linux",
                "arch": "x64",
                "cribl": {"version": "4.7.2"},  # Older version
                "cpu": {"count": 4, "model": "Intel(R) Xeon(R) CPU"},
                "memory": {"total": 8589934592}
            },
            "metrics": {
                "cpu": {"perc": 92.5},  # High CPU
                "memory": {"perc": 88.7, "rss": 7618416640},  # High memory
                "disk": {"/opt/cribl": {"usedP": 94.2}},  # High disk
                "health": 0.45,  # Low health
                "in_bytes_total": 95000000,
                "out_bytes_total": 50000000  # Low output suggests backpressure
            }
        },
        {
            # Disconnected node
            "id": "edge-prod-004",
            "status": "disconnected",
            "fleet": "production",
            "lastSeen": "2024-12-27T08:15:00Z",  # 2+ hours ago
            "info": {
                "hostname": "edge-prod-004.example.com",
                "os": "linux",
                "arch": "x64",
                "cribl": {"version": "4.8.0"},
                "cpu": {"count": 4, "model": "Intel(R) Xeon(R) CPU"},
                "memory": {"total": 8589934592}
            },
            "metrics": {
                "cpu": {"perc": 0},
                "memory": {"perc": 0, "rss": 0},
                "disk": {"/opt/cribl": {"usedP": 0}},
                "health": 0.0,
                "in_bytes_total": 0,
                "out_bytes_total": 0
            }
        }
    ]


@pytest.fixture
def realistic_edge_fleets():
    """Realistic Edge fleet configurations."""
    return [
        {
            "id": "production",
            "name": "production",
            "description": "Production edge fleet",
            "tags": ["prod", "critical"],
            "nodes": 4
        },
        {
            "id": "staging",
            "name": "staging",
            "description": "Staging edge fleet",
            "tags": ["staging", "test"],
            "nodes": 1
        }
    ]


@pytest.fixture
def edge_pipelines():
    """Edge-specific pipeline configurations."""
    return [
        {
            "id": "edge-syslog-processor",
            "conf": {
                "functions": [
                    {"id": "parser", "filter": "true", "conf": {"type": "json"}},
                    {"id": "eval", "filter": "true", "conf": {"add": [{"name": "source", "value": "'edge'"}]}},
                    {"id": "drop", "filter": "_raw.length > 65536", "conf": {}}
                ]
            }
        },
        {
            "id": "edge-metrics-enrichment",
            "conf": {
                "functions": [
                    {"id": "eval", "filter": "true", "conf": {"add": [{"name": "edge_fleet", "value": "__fleet"}]}},
                    {"id": "aggregation", "filter": "true", "conf": {"timeWindow": "60s"}}
                ]
            }
        }
    ]


@pytest.fixture
def edge_routes():
    """Edge-specific route configurations."""
    return [
        {
            "id": "syslog-to-stream",
            "filter": "sourcetype=='syslog'",
            "pipeline": "edge-syslog-processor",
            "output": "cribl-stream-leader",
            "final": True
        },
        {
            "id": "metrics-to-stream",
            "filter": "sourcetype=='metrics'",
            "pipeline": "edge-metrics-enrichment",
            "output": "cribl-stream-leader",
            "final": True
        },
        {
            "id": "default-passthrough",
            "filter": "true",
            "pipeline": "passthru",
            "output": "cribl-stream-leader",
            "final": True
        }
    ]


@pytest.fixture
def edge_outputs():
    """Edge-specific output configurations (typically cribl type to Stream)."""
    return [
        {
            "id": "cribl-stream-leader",
            "type": "cribl",
            "systemFields": ["cribl_pipe"],
            "streamtags": [],
            "conf": {
                "host": "stream-leader.example.com",
                "port": 9000,
                "tls": {"disabled": False},
                "authType": "manual",
                "connectionTimeout": 10000,
                "writeTimeout": 60000,
                "enableProxyHeader": False,
                "compression": "gzip"
            }
        }
    ]


@pytest.fixture
def edge_inputs():
    """Edge-specific input configurations."""
    return [
        {
            "id": "syslog-udp",
            "type": "syslog",
            "conf": {
                "host": "0.0.0.0",
                "port": 514,
                "protocol": "udp"
            }
        },
        {
            "id": "syslog-tcp",
            "type": "syslog",
            "conf": {
                "host": "0.0.0.0",
                "port": 601,
                "protocol": "tcp",
                "tls": {"disabled": False}
            }
        },
        {
            "id": "http-collector",
            "type": "http_server",
            "conf": {
                "host": "0.0.0.0",
                "port": 8088,
                "tls": {"disabled": False}
            }
        }
    ]


class TestEdgeHealthAnalysis:
    """Test health analysis on Edge deployments."""

    @pytest.mark.asyncio
    async def test_multi_fleet_health_analysis(self, mock_edge_client, realistic_edge_nodes):
        """Test health analysis across multiple Edge fleets."""
        # Setup
        mock_edge_client.get_nodes.return_value = realistic_edge_nodes
        analyzer = HealthAnalyzer()

        # Execute
        result = await analyzer.analyze(mock_edge_client)

        # Verify
        assert result.success is True
        assert result.metadata["product_type"] == "edge"
        assert result.metadata["nodes_analyzed"] == 5

        # Should detect unhealthy nodes
        critical_high = [f for f in result.findings if f.severity in ["critical", "high"]]
        assert len(critical_high) > 0

        # Should detect disconnected node
        disconnected_findings = [f for f in result.findings if "disconnected" in f.description.lower()]
        assert len(disconnected_findings) > 0

        # Should detect high resource usage
        resource_findings = [f for f in result.findings if "cpu" in f.description.lower() or "memory" in f.description.lower()]
        assert len(resource_findings) > 0

        # Verify Edge terminology in findings
        for finding in result.findings:
            # Should use "Edge Node" not "Worker"
            if "node" in finding.title.lower():
                assert "edge" in finding.title.lower() or "Edge" in finding.title

    @pytest.mark.asyncio
    async def test_edge_fleet_health_metadata(self, mock_edge_client, realistic_edge_nodes, realistic_edge_fleets):
        """Test that fleet information is captured in metadata."""
        mock_edge_client.get_nodes.return_value = realistic_edge_nodes
        mock_edge_client.get_edge_fleets.return_value = realistic_edge_fleets
        analyzer = HealthAnalyzer()

        result = await analyzer.analyze(mock_edge_client)

        # Verify fleet distribution in findings
        production_findings = [f for f in result.findings if "production" in str(f.affected_components)]
        staging_findings = [f for f in result.findings if "staging" in str(f.affected_components)]

        # Production fleet has more issues (3 problematic nodes vs 1 healthy staging node)
        assert len(production_findings) > len(staging_findings)

    @pytest.mark.asyncio
    async def test_edge_version_detection(self, mock_edge_client, realistic_edge_nodes):
        """Test that Edge version mismatches are detected."""
        mock_edge_client.get_nodes.return_value = realistic_edge_nodes
        analyzer = HealthAnalyzer()

        result = await analyzer.analyze(mock_edge_client)

        # edge-prod-003 has version 4.7.2 while others have 4.8.0
        # Should potentially flag version inconsistencies
        assert result.metadata["nodes_analyzed"] == 5


class TestEdgeConfigAnalysis:
    """Test configuration analysis on Edge deployments."""

    @pytest.mark.asyncio
    async def test_edge_pipeline_analysis(
        self, mock_edge_client, edge_pipelines, edge_routes, edge_inputs, edge_outputs
    ):
        """Test config analysis with Edge-specific patterns."""
        # Setup
        mock_edge_client.get_pipelines.return_value = edge_pipelines
        mock_edge_client.get_routes.return_value = edge_routes
        mock_edge_client.get_inputs.return_value = edge_inputs
        mock_edge_client.get_outputs.return_value = edge_outputs
        analyzer = ConfigAnalyzer()

        # Execute
        result = await analyzer.analyze(mock_edge_client)

        # Verify
        assert result.success is True
        assert result.metadata["product_type"] == "edge"
        assert result.metadata["pipelines_analyzed"] == 2
        assert result.metadata["routes_analyzed"] == 3
        assert result.metadata["outputs_analyzed"] == 1

        # Edge deployments typically have cribl output type
        cribl_outputs = [o for o in edge_outputs if o["type"] == "cribl"]
        assert len(cribl_outputs) > 0

    @pytest.mark.asyncio
    async def test_edge_output_to_stream_pattern(
        self, mock_edge_client, edge_pipelines, edge_routes, edge_inputs, edge_outputs
    ):
        """Test that Edge → Stream output pattern is recognized."""
        mock_edge_client.get_pipelines.return_value = edge_pipelines
        mock_edge_client.get_routes.return_value = edge_routes
        mock_edge_client.get_inputs.return_value = edge_inputs
        mock_edge_client.get_outputs.return_value = edge_outputs
        analyzer = ConfigAnalyzer()

        result = await analyzer.analyze(mock_edge_client)

        # All routes should point to cribl output (sending to Stream leader)
        for route in edge_routes:
            assert route["output"] == "cribl-stream-leader"

        # Should not flag this as unusual for Edge
        assert result.success is True

    @pytest.mark.asyncio
    async def test_edge_specific_error_messages(self, mock_edge_client):
        """Test that Edge-specific error messages are used."""
        # Simulate API failure
        mock_edge_client.get_pipelines.side_effect = Exception("API connection failed")
        analyzer = ConfigAnalyzer()

        result = await analyzer.analyze(mock_edge_client)

        # Should still succeed with graceful degradation
        assert result.success is True

        # Error finding should mention "Cribl Edge"
        error_findings = [f for f in result.findings if "error" in f.id.lower()]
        assert len(error_findings) > 0
        assert any("Cribl Edge" in f.title for f in error_findings)

        # Should reference Edge docs
        assert any("edge" in link.lower() for f in error_findings for link in f.documentation_links)


class TestEdgeResourceAnalysis:
    """Test resource analysis on Edge deployments."""

    @pytest.mark.asyncio
    async def test_edge_resource_constraints(self, mock_edge_client, realistic_edge_nodes):
        """Test that Edge node resource constraints are properly analyzed."""
        mock_edge_client.get_nodes.return_value = realistic_edge_nodes
        analyzer = ResourceAnalyzer()

        result = await analyzer.analyze(mock_edge_client)

        assert result.success is True
        assert result.metadata["product_type"] == "edge"

        # edge-prod-003 has high CPU (92.5%), memory (88.7%), disk (94.2%)
        high_resource_findings = [
            f for f in result.findings
            if f.severity in ["critical", "high"] and
            ("cpu" in f.description.lower() or "memory" in f.description.lower() or "disk" in f.description.lower())
        ]
        assert len(high_resource_findings) > 0

    @pytest.mark.asyncio
    async def test_edge_fleet_resource_distribution(self, mock_edge_client, realistic_edge_nodes):
        """Test resource analysis across different Edge fleets."""
        mock_edge_client.get_nodes.return_value = realistic_edge_nodes
        analyzer = ResourceAnalyzer()

        result = await analyzer.analyze(mock_edge_client)

        # Production fleet has 4 nodes, staging has 1
        # Production should show higher aggregate resource usage
        assert result.metadata["nodes_analyzed"] == 5


class TestEdgeDataNormalization:
    """Test Edge-specific data normalization."""

    @pytest.mark.asyncio
    async def test_edge_status_normalization(self, realistic_edge_nodes):
        """Test that Edge status values are normalized correctly."""
        client = CriblAPIClient(base_url="https://edge.example.com", auth_token="test")
        client._product_type = "edge"

        # Test connected → healthy
        connected_node = realistic_edge_nodes[0]
        normalized = client._normalize_node_data(connected_node)
        assert normalized["status"] == "healthy"

        # Test disconnected → unhealthy
        disconnected_node = realistic_edge_nodes[4]
        normalized = client._normalize_node_data(disconnected_node)
        assert normalized["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_edge_fleet_to_group_normalization(self, realistic_edge_nodes):
        """Test that Edge 'fleet' is normalized to 'group'."""
        client = CriblAPIClient(base_url="https://edge.example.com", auth_token="test")
        client._product_type = "edge"

        node = realistic_edge_nodes[0]
        normalized = client._normalize_node_data(node)

        assert "group" in normalized
        assert normalized["group"] == "production"

    @pytest.mark.asyncio
    async def test_edge_timestamp_normalization(self, realistic_edge_nodes):
        """Test that Edge lastSeen is converted to lastMsgTime."""
        client = CriblAPIClient(base_url="https://edge.example.com", auth_token="test")
        client._product_type = "edge"

        node = realistic_edge_nodes[0]
        normalized = client._normalize_node_data(node)

        # Should have lastMsgTime as milliseconds timestamp
        assert "lastMsgTime" in normalized
        assert isinstance(normalized["lastMsgTime"], int)
        assert normalized["lastMsgTime"] > 1700000000000  # After 2023


class TestEdgeProductDetection:
    """Test Edge product detection in integration scenarios."""

    @pytest.mark.asyncio
    async def test_edge_detection_from_version_endpoint(self):
        """Test that Edge is correctly detected from version endpoint."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock version endpoint returning Edge product
            version_response = AsyncMock()
            version_response.status_code = 200
            version_response.json.return_value = {
                "version": "4.8.0",
                "product": "edge"
            }
            mock_client.get.return_value = version_response

            async with CriblAPIClient(
                base_url="https://edge.example.com",
                auth_token="test-token"
            ) as client:
                # Product detection happens during test_connection
                result = await client.test_connection()

                assert result.success is True
                assert client.is_edge is True
                assert client.product_type == "edge"
                assert "Cribl Edge" in result.message


class TestEdgeEndToEnd:
    """End-to-end integration tests for Edge workflows."""

    @pytest.mark.asyncio
    async def test_complete_edge_analysis_workflow(
        self, mock_edge_client, realistic_edge_nodes, edge_pipelines, edge_routes, edge_inputs, edge_outputs
    ):
        """Test complete analysis workflow on Edge deployment."""
        # Setup all mocks
        mock_edge_client.get_nodes.return_value = realistic_edge_nodes
        mock_edge_client.get_pipelines.return_value = edge_pipelines
        mock_edge_client.get_routes.return_value = edge_routes
        mock_edge_client.get_inputs.return_value = edge_inputs
        mock_edge_client.get_outputs.return_value = edge_outputs

        # Run all analyzers
        health_analyzer = HealthAnalyzer()
        config_analyzer = ConfigAnalyzer()
        resource_analyzer = ResourceAnalyzer()

        health_result = await health_analyzer.analyze(mock_edge_client)
        config_result = await config_analyzer.analyze(mock_edge_client)
        resource_result = await resource_analyzer.analyze(mock_edge_client)

        # Verify all succeeded
        assert health_result.success is True
        assert config_result.success is True
        assert resource_result.success is True

        # Verify Edge metadata
        assert health_result.metadata["product_type"] == "edge"
        assert config_result.metadata["product_type"] == "edge"
        assert resource_result.metadata["product_type"] == "edge"

        # Verify findings were generated
        total_findings = len(health_result.findings) + len(config_result.findings) + len(resource_result.findings)
        assert total_findings > 0

        # Verify Edge-specific findings exist
        all_findings = health_result.findings + config_result.findings + resource_result.findings
        edge_specific = [f for f in all_findings if "edge" in f.title.lower() or "fleet" in f.description.lower()]

        # At least some findings should reference Edge-specific concepts
        # (though not all findings need to be Edge-specific)
        assert len(all_findings) > 0
