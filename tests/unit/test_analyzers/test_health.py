"""
Unit tests for HealthAnalyzer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cribl_hc.analyzers.health import HealthAnalyzer
from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation


# Helper function to create realistic worker data matching Cribl Cloud API
def create_worker(worker_id: str, status: str = "healthy", disconnected: bool = False,
                  total_disk: int = 30 * 1024**3, free_disk: int = 20 * 1024**3,
                  total_mem: int = 8 * 1024**3, worker_processes: int = 3, cpus: int = 4,
                  first_msg_time: int = 1000000000000) -> dict:
    """Create a realistic worker data structure matching Cribl Cloud API."""
    return {
        "id": worker_id,
        "status": status,
        "group": "default",
        "disconnected": disconnected,
        "workerProcesses": worker_processes,
        "firstMsgTime": first_msg_time,
        "lastMsgTime": first_msg_time + 60000,
        "deployable": True,
        "info": {
            "hostname": f"worker-{worker_id}",
            "platform": "linux",
            "architecture": "x64",
            "cpus": cpus,
            "totalmem": total_mem,
            "totalDiskSpace": total_disk,
            "freeDiskSpace": free_disk,
            "cribl": {
                "version": "4.15.0-f275b803"
            }
        }
    }


def setup_mock_client_for_stream(mock_client: AsyncMock) -> None:
    """Configure mock client for Stream product."""
    mock_client.is_edge = False
    mock_client.is_stream = True
    mock_client.product_type = "stream"
    mock_client._normalize_node_data.side_effect = lambda n: n  # No-op for Stream


class TestHealthAnalyzer:
    """Test suite for HealthAnalyzer."""

    def test_objective_name(self):
        """Test that objective name is 'health'."""
        analyzer = HealthAnalyzer()
        assert analyzer.objective_name == "health"

    def test_description(self):
        """Test analyzer description."""
        analyzer = HealthAnalyzer()
        description = analyzer.get_description()
        assert "health" in description.lower()
        assert "worker" in description.lower()

    def test_estimated_api_calls(self):
        """Test estimated API call count."""
        analyzer = HealthAnalyzer()
        assert analyzer.get_estimated_api_calls() == 3

    def test_required_permissions(self):
        """Test required permissions list."""
        analyzer = HealthAnalyzer()
        permissions = analyzer.get_required_permissions()
        assert "read:workers" in permissions
        assert "read:system" in permissions
        assert "read:metrics" in permissions

    @pytest.mark.asyncio
    async def test_analyze_all_healthy_workers(self):
        """Test analysis with all healthy workers."""
        # Create mock client
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        # Mock product detection (Stream)
        mock_client.is_edge = False
        mock_client.is_stream = True
        mock_client.product_type = "stream"

        # Mock healthy workers with realistic data
        workers = [
            create_worker("worker-1"),
            create_worker("worker-2"),
        ]
        mock_client.get_nodes.return_value = workers
        mock_client._normalize_node_data.side_effect = lambda n: n  # No-op for Stream

        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        # Run analysis
        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify result
        assert result.success is True
        assert result.objective == "health"
        assert result.metadata["worker_count"] == 2
        assert result.metadata["unhealthy_workers"] == 0
        assert result.metadata["health_score"] == 100.0
        assert result.metadata["health_status"] == "healthy"

        # Should have 1 finding (overall health summary)
        assert len(result.findings) == 1
        assert result.findings[0].category == "health"
        assert result.findings[0].severity == "info"

    @pytest.mark.asyncio
    async def test_analyze_unhealthy_worker_disconnected(self):
        """Test analysis with disconnected worker."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        # Mock workers with one disconnected
        mock_client.get_nodes.return_value = [
            create_worker("worker-1", status="shutting down", disconnected=True),
        ]

        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["unhealthy_workers"] == 1

        # Should have 2 findings: unhealthy worker + overall health
        assert len(result.findings) >= 2

        # Find worker health finding
        worker_finding = next(
            (f for f in result.findings if f.id == "health-worker-worker-1"),
            None,
        )
        assert worker_finding is not None
        assert worker_finding.severity == "critical"  # 2 issues: status + disconnected
        assert "shutting down" in worker_finding.description.lower()

        # Should have recommendations
        assert len(result.recommendations) == 1

    @pytest.mark.asyncio
    async def test_analyze_critical_worker_high_disk(self):
        """Test analysis with worker having high disk usage."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        # Mock worker with high disk usage (>90%)
        total_disk = 100 * 1024**3
        free_disk = 5 * 1024**3  # 95% used
        mock_client.get_nodes.return_value = [
            create_worker("worker-1", total_disk=total_disk, free_disk=free_disk),
        ]

        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True

        # Find worker finding
        worker_finding = next(
            (f for f in result.findings if f.id == "health-worker-worker-1"),
            None,
        )

        # Should be high severity (1 issue)
        assert worker_finding.severity == "high"
        assert "disk" in worker_finding.description.lower()

    @pytest.mark.asyncio
    async def test_analyze_mixed_worker_health(self):
        """Test analysis with mix of healthy and unhealthy workers."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        mock_client.get_nodes.return_value = [
            create_worker("worker-1"),  # Healthy
            create_worker("worker-2", status="unhealthy"),  # Unhealthy
            create_worker("worker-3"),  # Healthy
        ]

        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["worker_count"] == 3
        assert result.metadata["unhealthy_workers"] == 1

        # Health score should be good but not perfect
        health_score = result.metadata["health_score"]
        assert 60.0 < health_score < 90.0

        # Should have 1 recommendation for unhealthy worker
        assert len(result.recommendations) == 1

    @pytest.mark.asyncio
    async def test_analyze_no_workers(self):
        """Test analysis with no workers."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        mock_client.get_nodes.return_value = []
        mock_client.get_system_status.return_value = {"version": "4.5.0"}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["worker_count"] == 0
        assert result.metadata["health_score"] == 0.0

    @pytest.mark.asyncio
    async def test_analyze_api_error(self):
        """Test analysis when API call fails."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        # Simulate API error
        mock_client.get_nodes.side_effect = Exception("API connection failed")
        mock_client.get_system_status.return_value = {}

        # Mock leader health with proper async behavior
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"status": "unknown"})
        mock_client.get = AsyncMock(return_value=mock_response)

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should handle error gracefully per Constitution Principle #6 (Graceful Degradation)
        # The analyzer returns success=True but with a finding about having no workers
        assert result.success is True
        assert result.metadata["worker_count"] == 0
        assert result.metadata["health_score"] == 0.0

        # Should have at least one finding about no workers
        assert len(result.findings) >= 1

    @pytest.mark.asyncio
    async def test_health_score_calculation(self):
        """Test health score calculation algorithm."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        # 10 workers: 8 healthy, 2 unhealthy (1 with multiple issues)
        workers = []

        # 8 healthy workers
        for i in range(8):
            workers.append(create_worker(f"worker-{i}"))

        # 1 unhealthy worker (single issue)
        workers.append(create_worker("worker-8", status="unhealthy"))

        # 1 critical worker (multiple issues: status + disconnected)
        workers.append(create_worker("worker-9", status="unhealthy", disconnected=True))

        mock_client.get_nodes.return_value = workers
        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # With 80% healthy workers but 1 critical (2 issues):
        # - Base score: 80
        # - Critical penalty: (1/10) * 30 = 3
        # - Expected: ~77
        health_score = result.metadata["health_score"]
        assert 70.0 <= health_score <= 80.0

    def test_count_worker_issues(self):
        """Test worker issue counting."""
        analyzer = HealthAnalyzer()

        # Worker with no issues
        worker1 = create_worker("w1")
        assert analyzer._count_worker_issues(worker1) == 0

        # Worker with 1 issue (status)
        worker2 = create_worker("w2", status="unhealthy")
        assert analyzer._count_worker_issues(worker2) == 1

        # Worker with 2 issues (status + disconnected)
        worker3 = create_worker("w3", status="unhealthy", disconnected=True)
        assert analyzer._count_worker_issues(worker3) == 2

        # Worker with 3 issues (status + disconnected + disk)
        worker4 = create_worker("w4", status="unhealthy", disconnected=True,
                               total_disk=100*1024**3, free_disk=5*1024**3)
        assert analyzer._count_worker_issues(worker4) == 3

    def test_get_health_status(self):
        """Test health status categorization."""
        analyzer = HealthAnalyzer()

        assert analyzer._get_health_status(95.0) == "healthy"
        assert analyzer._get_health_status(90.0) == "healthy"
        assert analyzer._get_health_status(75.0) == "degraded"
        assert analyzer._get_health_status(70.0) == "degraded"
        assert analyzer._get_health_status(55.0) == "unhealthy"
        assert analyzer._get_health_status(50.0) == "unhealthy"
        assert analyzer._get_health_status(30.0) == "critical"
        assert analyzer._get_health_status(0.0) == "critical"

    @pytest.mark.asyncio
    async def test_remediation_steps_status(self):
        """Test status-specific remediation steps."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        mock_client.get_nodes.return_value = [
            create_worker("worker-1", status="unhealthy"),
        ]

        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        rec = result.recommendations[0]
        steps = "\n".join(rec.implementation_steps).lower()

        assert "status" in steps or "logs" in steps
        assert len(rec.documentation_links) > 0
        assert "docs.cribl.io" in rec.documentation_links[0]

    @pytest.mark.asyncio
    async def test_remediation_steps_disconnected(self):
        """Test disconnection-specific remediation steps."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        mock_client.get_nodes.return_value = [
            create_worker("worker-1", disconnected=True),
        ]

        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        rec = result.recommendations[0]
        steps = "\n".join(rec.implementation_steps).lower()

        assert "network" in steps or "connectivity" in steps

    @pytest.mark.asyncio
    async def test_remediation_steps_disk(self):
        """Test disk-specific remediation steps."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        # Create worker with high disk usage
        total_disk = 100 * 1024**3
        free_disk = 5 * 1024**3  # 95% used
        mock_client.get_nodes.return_value = [
            create_worker("worker-1", total_disk=total_disk, free_disk=free_disk),
        ]

        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        rec = result.recommendations[0]
        steps = "\n".join(rec.implementation_steps).lower()

        assert "disk" in steps or "persistent queue" in steps

    @pytest.mark.asyncio
    async def test_overall_health_finding_severity(self):
        """Test overall health finding has correct severity."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        # Test healthy status
        mock_client.get_nodes.return_value = [create_worker("w1")]
        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        overall_finding = next(
            (f for f in result.findings if "overall_health" in f.affected_components),
            None,
        )
        assert overall_finding.severity == "info"

    @pytest.mark.asyncio
    async def test_metadata_includes_version(self):
        """Test that Cribl version is captured in metadata."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        mock_client.get_nodes.return_value = [create_worker("w1")]
        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.metadata["cribl_version"] == "4.15.0-f275b803"

    @pytest.mark.asyncio
    async def test_leader_health_check(self):
        """Test leader health monitoring."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        mock_client.get_nodes.return_value = [create_worker("w1")]
        mock_client.get_system_status.return_value = {}

        # Mock unhealthy leader
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "degraded", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have leader health finding
        leader_finding = next(
            (f for f in result.findings if f.id == "health-leader-unhealthy"),
            None,
        )
        assert leader_finding is not None
        assert leader_finding.severity == "critical"
        assert result.metadata["leader_status"] == "degraded"

    @pytest.mark.asyncio
    async def test_single_worker_detection(self):
        """Test detection of single worker deployments."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        mock_client.get_nodes.return_value = [create_worker("w1")]
        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have single worker finding
        single_worker_finding = next(
            (f for f in result.findings if f.id == "health-single-worker"),
            None,
        )
        assert single_worker_finding is not None
        assert single_worker_finding.severity == "medium"
        assert "redundancy" in single_worker_finding.description.lower()

    @pytest.mark.asyncio
    async def test_worker_process_count_check(self):
        """Test worker process count validation."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_stream(mock_client)

        # Worker with suboptimal process count (3 processes but 8 CPUs)
        mock_client.get_nodes.return_value = [
            create_worker("w1", worker_processes=3, cpus=8)
        ]
        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have worker process finding
        process_finding = next(
            (f for f in result.findings if "health-worker-processes" in f.id),
            None,
        )
        assert process_finding is not None
        assert process_finding.severity == "low"
        assert "6 processes" in process_finding.description  # Recommended: CPUs - 2 (n-2)


def create_edge_node(
    node_id: str,
    status: str = "connected",
    cpu_usage: float = 45.0,
    memory_usage: float = 60.0,
    disk_usage: float = 40.0,
    fleet: str = "default",
) -> dict:
    """Create realistic Edge node data structure."""
    # Calculate disk space based on usage percentage
    total_disk_bytes = 100 * 1024**3  # 100GB total
    used_disk_bytes = int(total_disk_bytes * (disk_usage / 100.0))
    free_disk_bytes = total_disk_bytes - used_disk_bytes

    return {
        "id": node_id,
        "guid": f"guid-{node_id}",
        "status": status,  # "connected", "disconnected", "unreachable"
        "fleet": fleet,
        "hostname": f"edge-{node_id}",
        "lastSeen": "2024-12-13T12:00:00Z",
        "info": {
            "hostname": f"edge-{node_id}",
            "platform": "linux",
            "architecture": "x64",
            "cpus": 4,
            "totalmem": 8 * 1024**3,
            "totalDiskSpace": total_disk_bytes,
            "freeDiskSpace": free_disk_bytes,
            "cribl": {"version": "4.15.0"},
        },
        "metrics": {
            "cpu": {"perc": cpu_usage / 100.0},
            "memory": {"used_percent": memory_usage},
            "disk": {"used_percent": disk_usage},
        },
    }


def setup_mock_client_for_edge(mock_client: AsyncMock) -> None:
    """Configure mock client for Edge product."""
    mock_client.is_edge = True
    mock_client.is_stream = False
    mock_client.product_type = "edge"

    # Mock normalization: Edge "connected" → Stream "healthy"
    def normalize_edge_data(node: dict) -> dict:
        normalized = node.copy()
        if node.get("status") == "connected":
            normalized["status"] = "healthy"
        elif node.get("status") == "disconnected":
            normalized["status"] = "unhealthy"

        # Map fleet to group
        if "fleet" in node:
            normalized["group"] = node["fleet"]

        # Convert lastSeen to lastMsgTime
        if "lastSeen" in node:
            from datetime import datetime

            try:
                dt = datetime.fromisoformat(node["lastSeen"].replace("Z", "+00:00"))
                normalized["lastMsgTime"] = int(dt.timestamp() * 1000)
            except Exception:
                pass

        return normalized

    mock_client._normalize_node_data.side_effect = normalize_edge_data


class TestHealthAnalyzerEdgeSupport:
    """Test HealthAnalyzer with Cribl Edge."""

    @pytest.mark.asyncio
    async def test_analyze_edge_all_healthy_nodes(self):
        """Test health analysis on healthy Edge nodes."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_edge(mock_client)

        # Mock Edge node data
        edge_nodes = [
            create_edge_node("node-1", status="connected"),
            create_edge_node("node-2", status="connected"),
        ]
        mock_client.get_nodes.return_value = edge_nodes

        # Mock system status
        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        # Run analysis
        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify Edge-specific behavior
        assert result.success is True
        assert result.metadata["worker_count"] == 2
        assert result.metadata["health_score"] == 100.0
        assert result.metadata["unhealthy_workers"] == 0

        # Verify overall health finding exists
        overall_finding = next(
            (f for f in result.findings if "health-overall" in f.id), None
        )
        assert overall_finding is not None
        assert "operating normally" in overall_finding.description.lower() or "healthy" in overall_finding.description.lower()

    @pytest.mark.asyncio
    async def test_analyze_edge_unhealthy_node_disconnected(self):
        """Test Edge node with disconnected status."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_edge(mock_client)

        # Disconnected Edge node
        edge_nodes = [
            create_edge_node("node-1", status="disconnected", cpu_usage=95.0),
        ]
        mock_client.get_nodes.return_value = edge_nodes
        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect unhealthy node
        assert result.success is True
        assert result.metadata.get("unhealthy_workers", 0) == 1
        assert result.metadata["health_score"] < 100.0

        # Finding should mention "Edge Node"
        node_finding = next(
            (f for f in result.findings if "health-worker-node-1" in f.id),
            None,
        )
        assert node_finding is not None
        assert node_finding.severity in ["high", "critical"]
        assert "Edge Node" in node_finding.title

    @pytest.mark.asyncio
    async def test_analyze_edge_high_disk_usage(self):
        """Test Edge node with high disk usage (>90% threshold)."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_edge(mock_client)

        # Edge node with critical disk usage
        # Note: HealthAnalyzer checks disk >90%, not CPU/memory percentages
        # (CPU/memory usage would be checked by ResourceAnalyzer)
        edge_nodes = [
            create_edge_node(
                "node-1",
                status="connected",
                cpu_usage=45.0,
                memory_usage=60.0,
                disk_usage=95.0,  # >90% = critical
            ),
        ]
        mock_client.get_nodes.return_value = edge_nodes
        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect disk issue
        assert result.success is True
        assert result.metadata.get("unhealthy_workers", 0) == 1

        # Check for disk-related finding
        node_finding = next(
            (f for f in result.findings if "health-worker-node-1" in f.id),
            None,
        )
        assert node_finding is not None
        assert "Edge Node" in node_finding.title
        # Should mention disk issue
        assert "disk" in node_finding.description.lower()

    @pytest.mark.asyncio
    async def test_analyze_edge_mixed_fleet_health(self):
        """Test Edge nodes across different fleets with mixed health."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_edge(mock_client)

        # Nodes in different fleets with different health
        edge_nodes = [
            create_edge_node("node-1", status="connected", fleet="production"),
            create_edge_node("node-2", status="connected", fleet="production"),
            create_edge_node(
                "node-3",
                status="disconnected",
                cpu_usage=95.0,
                fleet="staging",
            ),
        ]
        mock_client.get_nodes.return_value = edge_nodes
        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect mixed health
        assert result.success is True
        assert result.metadata["worker_count"] == 3
        assert result.metadata.get("unhealthy_workers", 0) == 1
        assert result.metadata["health_score"] < 100.0

        # Should have finding for unhealthy node
        node_finding = next(
            (f for f in result.findings if "node-3" in f.id),
            None,
        )
        assert node_finding is not None
        assert "staging" in node_finding.description  # Fleet name

    @pytest.mark.asyncio
    async def test_analyze_edge_product_aware_messaging(self):
        """Test that Edge findings use product-aware terminology."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        setup_mock_client_for_edge(mock_client)

        # Unhealthy Edge node to trigger finding
        edge_nodes = [
            create_edge_node("node-1", status="disconnected"),
        ]
        mock_client.get_nodes.return_value = edge_nodes
        mock_client.get_system_status.return_value = {}

        # Mock leader health
        mock_get = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy", "role": "primary"}
        mock_get.return_value = mock_response
        mock_client.get = mock_get

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify Edge terminology in findings
        node_finding = next(
            (f for f in result.findings if "health-worker-node-1" in f.id),
            None,
        )
        assert node_finding is not None

        # Should use "Edge Node" not "Worker"
        assert "Edge Node" in node_finding.title
        assert "Edge Node" in node_finding.description

        # Should NOT use Stream terminology
        assert "Worker" not in node_finding.title or "Edge" in node_finding.title
