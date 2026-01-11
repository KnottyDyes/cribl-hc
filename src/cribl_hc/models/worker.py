"""
Worker node model for Cribl Stream workers with resource utilization.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ResourceUtilization(BaseModel):
    """
    Resource utilization metrics for a worker node.

    Attributes:
        cpu_percent: CPU utilization percentage (0-100)
        memory_used_gb: Memory used in GB
        memory_total_gb: Total memory in GB
        memory_percent: Memory utilization percentage (0-100)
        disk_used_gb: Disk space used in GB
        disk_total_gb: Total disk space in GB
        disk_percent: Disk utilization percentage (0-100)
    """

    cpu_percent: float = Field(..., description="CPU utilization %", ge=0, le=100)
    memory_used_gb: float = Field(..., description="Memory used GB", ge=0)
    memory_total_gb: float = Field(..., description="Total memory GB", gt=0)
    memory_percent: float = Field(..., description="Memory utilization %", ge=0, le=100)
    disk_used_gb: float = Field(..., description="Disk used GB", ge=0)
    disk_total_gb: float = Field(..., description="Total disk GB", gt=0)
    disk_percent: float = Field(..., description="Disk utilization %", ge=0, le=100)


class WorkerNode(BaseModel):
    """
    Individual Cribl worker instance with health status and resource metrics.

    Health Status Determination:
    - unreachable: connectivity_status != "connected"
    - unhealthy: CPU > 90% OR memory > 90% OR disk > 90%
    - degraded: CPU > 75% OR memory > 75% OR disk > 80%
    - healthy: All resources within normal range

    Attributes:
        id: Worker ID from Cribl API
        name: Human-readable name
        group_id: Worker group membership
        host: Hostname or IP address
        version: Cribl version running on this worker
        health_status: Current health status
        resource_utilization: Resource usage metrics
        connectivity_status: Connection status to master
        last_seen: Last communication timestamp
        uptime_seconds: Worker uptime in seconds
        metadata: Additional worker metadata

    Example:
        >>> worker = WorkerNode(
        ...     id="wrkr-abc123",
        ...     name="worker-01",
        ...     group_id="default",
        ...     host="10.0.1.45",
        ...     version="4.5.2",
        ...     health_status="degraded",
        ...     resource_utilization=ResourceUtilization(
        ...         cpu_percent=68.5,
        ...         memory_used_gb=14.7,
        ...         memory_total_gb=16.0,
        ...         memory_percent=91.9,
        ...         disk_used_gb=45.2,
        ...         disk_total_gb=100.0,
        ...         disk_percent=45.2
        ...     ),
        ...     connectivity_status="connected"
        ... )
    """

    id: str = Field(..., description="Worker ID from Cribl API", min_length=1)
    name: str = Field(..., description="Human-readable name", min_length=1)
    group_id: str = Field(..., description="Worker group ID", min_length=1)
    host: str = Field(..., description="Hostname or IP address", min_length=1)
    version: str = Field(..., description="Cribl version", min_length=1)
    health_status: Literal["healthy", "degraded", "unhealthy", "unreachable"] = Field(
        ..., description="Health status"
    )
    resource_utilization: ResourceUtilization = Field(..., description="Resource metrics")
    connectivity_status: Literal["connected", "disconnected", "unknown"] = Field(
        ..., description="Connection status"
    )
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    uptime_seconds: Optional[int] = Field(None, description="Uptime in seconds", ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @staticmethod
    def determine_health_status(
        connectivity_status: str,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float,
    ) -> Literal["healthy", "degraded", "unhealthy", "unreachable"]:
        """
        Determine health status from resource utilization.

        Args:
            connectivity_status: Worker connectivity status
            cpu_percent: CPU utilization percentage
            memory_percent: Memory utilization percentage
            disk_percent: Disk utilization percentage

        Returns:
            Health status: healthy, degraded, unhealthy, or unreachable
        """
        if connectivity_status != "connected":
            return "unreachable"

        if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
            return "unhealthy"

        if cpu_percent > 75 or memory_percent > 75 or disk_percent > 80:
            return "degraded"

        return "healthy"

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "wrkr-abc123",
                "name": "worker-01",
                "group_id": "default",
                "host": "10.0.1.45",
                "version": "4.5.2",
                "health_status": "degraded",
                "resource_utilization": {
                    "cpu_percent": 68.5,
                    "memory_used_gb": 14.7,
                    "memory_total_gb": 16.0,
                    "memory_percent": 91.9,
                    "disk_used_gb": 45.2,
                    "disk_total_gb": 100.0,
                    "disk_percent": 45.2,
                },
                "connectivity_status": "connected",
                "last_seen": "2025-12-10T14:03:30Z",
                "uptime_seconds": 2592000,
                "metadata": {"instance_type": "m5.xlarge", "az": "us-east-1a"},
            }
        }
