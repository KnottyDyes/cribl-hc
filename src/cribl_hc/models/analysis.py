"""
Analysis run model for tracking health check execution and results.
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

# Import related models
from .finding import Finding
from .health import HealthScore
from .recommendation import Recommendation
from .worker import WorkerNode


class AnalysisRun(BaseModel):
    """
    Single execution of health check analysis with metadata and results.

    State Transitions:
    - running → completed (all objectives succeeded)
    - running → partial (some objectives failed but results available)
    - running → failed (critical failure, no results)

    Attributes:
        id: UUID for this analysis run
        deployment_id: Reference to Deployment being analyzed
        started_at: When analysis started
        completed_at: When analysis completed (None if still running)
        duration_seconds: Total duration in seconds
        status: Current status (running/completed/partial/failed)
        objectives_analyzed: List of objectives analyzed
        api_calls_used: Count of Cribl API calls made
        health_score: Overall health score (None if not yet calculated)
        findings: List of identified issues
        recommendations: List of improvement suggestions
        worker_nodes: List of analyzed worker nodes
        errors: List of errors encountered
        partial_completion: True if some objectives failed

    Validation:
        - api_calls_used must be ≤ 100 (enforced limit)
        - duration_seconds must be ≤ 300 (5 minutes target)

    Example:
        >>> run = AnalysisRun(
        ...     id=str(uuid4()),
        ...     deployment_id="prod-cribl",
        ...     started_at=datetime.utcnow(),
        ...     status="running",
        ...     objectives_analyzed=["health"],
        ...     api_calls_used=0
        ... )
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="Analysis run UUID")
    deployment_id: str = Field(..., description="Deployment ID", min_length=1)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    duration_seconds: Optional[float] = Field(
        None, description="Duration in seconds", ge=0, le=300
    )
    status: Literal["running", "completed", "partial", "failed"] = Field(
        ..., description="Analysis status"
    )
    objectives_analyzed: list[str] = Field(..., description="Analyzed objectives", min_items=1)
    api_calls_used: int = Field(..., description="API calls made", ge=0, le=100)
    health_score: Optional[HealthScore] = Field(None, description="Overall health score")
    findings: list[Finding] = Field(default_factory=list, description="Identified issues")
    recommendations: list[Recommendation] = Field(
        default_factory=list, description="Improvement suggestions"
    )
    worker_nodes: list[WorkerNode] = Field(default_factory=list, description="Worker nodes")
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
    partial_completion: bool = Field(False, description="Partial completion flag")

    @field_validator("api_calls_used")
    @classmethod
    def validate_api_calls_limit(cls, v: int) -> int:
        """Validate API calls are within budget (≤ 100)."""
        if v > 100:
            raise ValueError(
                f"API calls used ({v}) exceeds budget limit of 100 calls per analysis"
            )
        return v

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration_limit(cls, v: Optional[float]) -> Optional[float]:
        """Validate duration is within target (≤ 300 seconds / 5 minutes)."""
        if v is not None and v > 300:
            # This is a warning, not a hard error - log but don't reject
            # The field constraint le=300 will handle hard validation
            pass
        return v

    @field_validator("completed_at")
    @classmethod
    def validate_completed_after_started(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate completion timestamp is after start timestamp."""
        if v is not None:
            started_at = info.data.get("started_at")
            if started_at and v < started_at:
                raise ValueError("completed_at must be after started_at")
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "deployment_id": "prod-cribl",
                "started_at": "2025-12-10T14:00:00Z",
                "completed_at": "2025-12-10T14:03:45Z",
                "duration_seconds": 225.3,
                "status": "completed",
                "objectives_analyzed": ["health", "config", "security"],
                "api_calls_used": 87,
                "health_score": {
                    "overall_score": 78,
                    "components": {},
                    "timestamp": "2025-12-10T14:03:45Z",
                },
                "findings": [],
                "recommendations": [],
                "worker_nodes": [],
                "errors": [],
                "partial_completion": False,
            }
        }
