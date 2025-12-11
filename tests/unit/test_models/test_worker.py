"""
Unit tests for WorkerNode and ResourceUtilization models.
"""

import pytest
from pydantic import ValidationError

from cribl_hc.models.worker import ResourceUtilization, WorkerNode


class TestResourceUtilization:
    """Test ResourceUtilization model validation."""

    def test_valid_resource_utilization(self):
        """Test creating valid resource utilization."""
        resources = ResourceUtilization(
            cpu_percent=68.5,
            memory_used_gb=14.7,
            memory_total_gb=16.0,
            memory_percent=91.9,
            disk_used_gb=45.2,
            disk_total_gb=100.0,
            disk_percent=45.2,
        )

        assert resources.cpu_percent == 68.5
        assert resources.memory_used_gb == 14.7
        assert resources.memory_total_gb == 16.0
        assert resources.memory_percent == 91.9
        assert resources.disk_used_gb == 45.2
        assert resources.disk_total_gb == 100.0
        assert resources.disk_percent == 45.2

    def test_cpu_percent_boundaries(self):
        """Test CPU percent validation (0-100)."""
        # Valid
        ResourceUtilization(
            cpu_percent=0,
            memory_used_gb=10,
            memory_total_gb=16,
            memory_percent=62.5,
            disk_used_gb=50,
            disk_total_gb=100,
            disk_percent=50,
        )

        # Invalid: negative
        with pytest.raises(ValidationError):
            ResourceUtilization(
                cpu_percent=-1,
                memory_used_gb=10,
                memory_total_gb=16,
                memory_percent=62.5,
                disk_used_gb=50,
                disk_total_gb=100,
                disk_percent=50,
            )

        # Invalid: over 100
        with pytest.raises(ValidationError):
            ResourceUtilization(
                cpu_percent=101,
                memory_used_gb=10,
                memory_total_gb=16,
                memory_percent=62.5,
                disk_used_gb=50,
                disk_total_gb=100,
                disk_percent=50,
            )

    def test_memory_total_must_be_positive(self):
        """Test that memory_total_gb must be > 0."""
        with pytest.raises(ValidationError):
            ResourceUtilization(
                cpu_percent=50,
                memory_used_gb=0,
                memory_total_gb=0,  # Invalid
                memory_percent=0,
                disk_used_gb=50,
                disk_total_gb=100,
                disk_percent=50,
            )

    def test_disk_total_must_be_positive(self):
        """Test that disk_total_gb must be > 0."""
        with pytest.raises(ValidationError):
            ResourceUtilization(
                cpu_percent=50,
                memory_used_gb=10,
                memory_total_gb=16,
                memory_percent=62.5,
                disk_used_gb=0,
                disk_total_gb=0,  # Invalid
                disk_percent=0,
            )


class TestWorkerNode:
    """Test WorkerNode model validation and behavior."""

    def test_valid_worker_node(self):
        """Test creating a valid worker node."""
        worker = WorkerNode(
            id="wrkr-abc123",
            name="worker-01",
            group_id="default",
            host="10.0.1.45",
            version="4.5.2",
            health_status="degraded",
            resource_utilization=ResourceUtilization(
                cpu_percent=68.5,
                memory_used_gb=14.7,
                memory_total_gb=16.0,
                memory_percent=91.9,
                disk_used_gb=45.2,
                disk_total_gb=100.0,
                disk_percent=45.2,
            ),
            connectivity_status="connected",
        )

        assert worker.id == "wrkr-abc123"
        assert worker.name == "worker-01"
        assert worker.group_id == "default"
        assert worker.host == "10.0.1.45"
        assert worker.version == "4.5.2"
        assert worker.health_status == "degraded"
        assert worker.connectivity_status == "connected"
        assert worker.uptime_seconds is None
        assert worker.metadata == {}

    def test_all_health_statuses(self):
        """Test all valid health status values."""
        statuses = ["healthy", "degraded", "unhealthy", "unreachable"]

        for status in statuses:
            worker = WorkerNode(
                id=f"worker-{status}",
                name=f"Worker {status}",
                group_id="default",
                host="10.0.0.1",
                version="4.5.0",
                health_status=status,  # type: ignore
                resource_utilization=ResourceUtilization(
                    cpu_percent=50,
                    memory_used_gb=8,
                    memory_total_gb=16,
                    memory_percent=50,
                    disk_used_gb=50,
                    disk_total_gb=100,
                    disk_percent=50,
                ),
                connectivity_status="connected",
            )
            assert worker.health_status == status

    def test_all_connectivity_statuses(self):
        """Test all valid connectivity status values."""
        statuses = ["connected", "disconnected", "unknown"]

        for status in statuses:
            worker = WorkerNode(
                id=f"worker-{status}",
                name="Worker",
                group_id="default",
                host="10.0.0.1",
                version="4.5.0",
                health_status="healthy",
                resource_utilization=ResourceUtilization(
                    cpu_percent=50,
                    memory_used_gb=8,
                    memory_total_gb=16,
                    memory_percent=50,
                    disk_used_gb=50,
                    disk_total_gb=100,
                    disk_percent=50,
                ),
                connectivity_status=status,  # type: ignore
            )
            assert worker.connectivity_status == status

    def test_worker_with_uptime(self):
        """Test worker with uptime specified."""
        worker = WorkerNode(
            id="worker-001",
            name="Worker",
            group_id="default",
            host="10.0.0.1",
            version="4.5.0",
            health_status="healthy",
            resource_utilization=ResourceUtilization(
                cpu_percent=50,
                memory_used_gb=8,
                memory_total_gb=16,
                memory_percent=50,
                disk_used_gb=50,
                disk_total_gb=100,
                disk_percent=50,
            ),
            connectivity_status="connected",
            uptime_seconds=2592000,  # 30 days
        )

        assert worker.uptime_seconds == 2592000

    def test_negative_uptime_rejected(self):
        """Test that negative uptime is rejected."""
        with pytest.raises(ValidationError):
            WorkerNode(
                id="worker-001",
                name="Worker",
                group_id="default",
                host="10.0.0.1",
                version="4.5.0",
                health_status="healthy",
                resource_utilization=ResourceUtilization(
                    cpu_percent=50,
                    memory_used_gb=8,
                    memory_total_gb=16,
                    memory_percent=50,
                    disk_used_gb=50,
                    disk_total_gb=100,
                    disk_percent=50,
                ),
                connectivity_status="connected",
                uptime_seconds=-100,
            )

    def test_worker_with_metadata(self):
        """Test worker with custom metadata."""
        metadata = {"instance_type": "m5.xlarge", "az": "us-east-1a"}

        worker = WorkerNode(
            id="worker-001",
            name="Worker",
            group_id="default",
            host="10.0.0.1",
            version="4.5.0",
            health_status="healthy",
            resource_utilization=ResourceUtilization(
                cpu_percent=50,
                memory_used_gb=8,
                memory_total_gb=16,
                memory_percent=50,
                disk_used_gb=50,
                disk_total_gb=100,
                disk_percent=50,
            ),
            connectivity_status="connected",
            metadata=metadata,
        )

        assert worker.metadata == metadata
        assert worker.metadata["instance_type"] == "m5.xlarge"

    def test_determine_health_status_unreachable(self):
        """Test health status determination: unreachable."""
        status = WorkerNode.determine_health_status(
            connectivity_status="disconnected",
            cpu_percent=50,
            memory_percent=50,
            disk_percent=50,
        )
        assert status == "unreachable"

    def test_determine_health_status_unhealthy_cpu(self):
        """Test health status determination: unhealthy due to CPU."""
        status = WorkerNode.determine_health_status(
            connectivity_status="connected",
            cpu_percent=95,  # > 90
            memory_percent=50,
            disk_percent=50,
        )
        assert status == "unhealthy"

    def test_determine_health_status_unhealthy_memory(self):
        """Test health status determination: unhealthy due to memory."""
        status = WorkerNode.determine_health_status(
            connectivity_status="connected",
            cpu_percent=50,
            memory_percent=95,  # > 90
            disk_percent=50,
        )
        assert status == "unhealthy"

    def test_determine_health_status_unhealthy_disk(self):
        """Test health status determination: unhealthy due to disk."""
        status = WorkerNode.determine_health_status(
            connectivity_status="connected",
            cpu_percent=50,
            memory_percent=50,
            disk_percent=95,  # > 90
        )
        assert status == "unhealthy"

    def test_determine_health_status_degraded_cpu(self):
        """Test health status determination: degraded due to CPU."""
        status = WorkerNode.determine_health_status(
            connectivity_status="connected",
            cpu_percent=80,  # > 75 but <= 90
            memory_percent=50,
            disk_percent=50,
        )
        assert status == "degraded"

    def test_determine_health_status_degraded_memory(self):
        """Test health status determination: degraded due to memory."""
        status = WorkerNode.determine_health_status(
            connectivity_status="connected",
            cpu_percent=50,
            memory_percent=80,  # > 75 but <= 90
            disk_percent=50,
        )
        assert status == "degraded"

    def test_determine_health_status_degraded_disk(self):
        """Test health status determination: degraded due to disk."""
        status = WorkerNode.determine_health_status(
            connectivity_status="connected",
            cpu_percent=50,
            memory_percent=50,
            disk_percent=85,  # > 80 but <= 90
        )
        assert status == "degraded"

    def test_determine_health_status_healthy(self):
        """Test health status determination: healthy."""
        status = WorkerNode.determine_health_status(
            connectivity_status="connected",
            cpu_percent=50,
            memory_percent=50,
            disk_percent=50,
        )
        assert status == "healthy"
