from datetime import datetime
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from .finding import Finding
from .health import HealthScore
from .recommendation import Recommendation
from .worker import WorkerNode


class ComponentVersion(BaseModel):
    name: str = Field(..., description="Component name.")
    version: str = Field(..., description="Version string.")
    status: str = Field(default="unknown", description="Operational status.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context.")

    model_config = {"populate_by_name": True}


class VersionInfo(BaseModel):
    leader_version: Optional[str] = None
    product_type: Optional[str] = None
    product_versions: dict[str, str] = Field(default_factory=dict)
    component_versions: list[ComponentVersion] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class AnalysisRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), description="Analysis run UUID")
    deployment_id: str = Field(..., description="Deployment ID", min_length=1)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = Field(default=None, ge=0)
    status: Literal["running", "completed", "partial", "failed"] = Field(
        ..., description="Analysis status"
    )
    objectives_analyzed: list[str] = Field(..., description="Analyzed objectives")
    api_calls_used: int = Field(default=0, description="API calls made", ge=0)
    health_score: Optional[HealthScore] = None
    findings: list[Finding] = Field(default_factory=list, description="Identified issues")
    recommendations: list[Recommendation] = Field(
        default_factory=list, description="Improvement suggestions"
    )
    worker_nodes: list[WorkerNode] = Field(default_factory=list, description="Worker nodes")
    version_info: VersionInfo = Field(default_factory=lambda: VersionInfo())
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
    partial_completion: bool = False

    @field_validator("completed_at")
    @classmethod
    def validate_completed_after_started(
        cls, v: Optional[datetime], info: Any
    ) -> Optional[datetime]:
        if v is not None:
            started_at = info.data.get("started_at")
            if started_at and v < started_at:
                raise ValueError("completed_at must be after started_at")
        return v

    model_config = {"populate_by_name": True}
