"""
Recommendation model for actionable improvement suggestions.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ImpactEstimate(BaseModel):
    """
    Estimated impact of implementing a recommendation.

    Attributes:
        cost_savings_annual: Dollars saved per year
        performance_improvement: Performance improvement description
        storage_reduction_gb: Storage space saved in GB
        time_to_implement: Estimated time to implement
    """

    cost_savings_annual: Optional[float] = Field(
        None, description="Annual cost savings in dollars", ge=0
    )
    performance_improvement: Optional[str] = Field(
        None, description="Performance improvement estimate"
    )
    storage_reduction_gb: Optional[float] = Field(
        None, description="Storage reduction in GB", ge=0
    )
    time_to_implement: Optional[str] = Field(None, description="Time to implement estimate")

    def has_impact_metrics(self) -> bool:
        """Check if at least one impact metric is provided."""
        return any(
            [
                self.cost_savings_annual is not None,
                self.performance_improvement is not None,
                self.storage_reduction_gb is not None,
            ]
        )


class Recommendation(BaseModel):
    """
    Actionable suggestion for improvement with impact estimates.

    Priority Levels:
    - p0: Critical, implement immediately (< 24 hours)
    - p1: High priority, implement soon (< 1 week)
    - p2: Medium priority, plan for next sprint
    - p3: Low priority, nice-to-have improvement

    Attributes:
        id: Unique recommendation identifier
        type: Type (e.g., "scaling", "optimization", "security", "cost")
        priority: Priority level
        title: Brief title
        description: Detailed description
        rationale: Why this recommendation is made
        implementation_steps: Step-by-step implementation guide
        before_state: Current state description
        after_state: Expected state after implementation
        impact_estimate: Estimated impact metrics
        implementation_effort: Effort required (low/medium/high)
        related_findings: Finding IDs this addresses
        product_tags: Products this recommendation applies to (e.g., ["stream"], ["edge"], ["lake"], ["search"], or any combination)
        documentation_links: Cribl docs URLs
        created_at: When recommendation was created

    Example:
        >>> rec = Recommendation(
        ...     id="rec-storage-001",
        ...     type="optimization",
        ...     priority="p1",
        ...     title="Implement sampling for debug logs",
        ...     description="Reduce storage costs by 35%",
        ...     rationale="Debug logs rarely queried",
        ...     implementation_steps=["Add eval function to pipeline"],
        ...     before_state="Sending 2.4TB/day",
        ...     after_state="Send 240GB/day",
        ...     impact_estimate=ImpactEstimate(cost_savings_annual=18720.0),
        ...     implementation_effort="low"
        ... )
    """

    id: str = Field(..., description="Unique recommendation ID", min_length=1)
    type: str = Field(..., description="Recommendation type", min_length=1)
    priority: Literal["p0", "p1", "p2", "p3"] = Field(..., description="Priority level")
    title: str = Field(..., description="Brief title", min_length=1, max_length=255)
    description: str = Field(..., description="Detailed description", min_length=1)
    rationale: str = Field(..., description="Rationale for recommendation", min_length=1)
    implementation_steps: list[str] = Field(..., description="Implementation steps", min_items=1)
    before_state: str = Field(default="", description="Current state")
    after_state: str = Field(default="", description="Expected state after")
    impact_estimate: ImpactEstimate = Field(..., description="Impact estimates")
    implementation_effort: Literal["low", "medium", "high"] = Field(
        ..., description="Implementation effort"
    )
    related_findings: list[str] = Field(
        default_factory=list, description="Related finding IDs"
    )
    product_tags: List[Literal["stream", "edge", "lake", "search"]] = Field(
        default_factory=lambda: ["stream", "edge", "lake", "search"],
        description="Products this recommendation applies to"
    )
    documentation_links: list[str] = Field(
        default_factory=list, description="Documentation URLs"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("impact_estimate")
    @classmethod
    def validate_impact_estimate(cls, v: ImpactEstimate, info) -> ImpactEstimate:
        """Validate impact estimate has metrics for p0/p1 priorities."""
        priority = info.data.get("priority")
        if priority in ["p0", "p1"] and not v.has_impact_metrics():
            raise ValueError(
                f"Impact estimate must have at least one metric for {priority} priority"
            )
        return v

    @field_validator("before_state")
    @classmethod
    def validate_before_state(cls, v: str, info) -> str:
        """Validate before_state is present for optimization recommendations."""
        rec_type = info.data.get("type", "")
        if rec_type == "optimization" and not v:
            raise ValueError("before_state required for optimization recommendations")
        return v

    @field_validator("after_state")
    @classmethod
    def validate_after_state(cls, v: str, info) -> str:
        """Validate after_state is present for optimization recommendations."""
        rec_type = info.data.get("type", "")
        if rec_type == "optimization" and not v:
            raise ValueError("after_state required for optimization recommendations")
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "rec-storage-001",
                "type": "optimization",
                "priority": "p1",
                "title": "Implement sampling for high-volume debug logs",
                "description": "Reduce storage costs by 35% by sampling debug-level logs at 10:1 ratio",
                "rationale": "Debug logs represent 60% of total volume but are rarely queried",
                "implementation_steps": [
                    "Add eval function to 'debug-logs' pipeline: sample rate=0.1",
                    "Test sampling logic with known debug volume",
                    "Monitor Splunk for adequate debug log coverage",
                    "Adjust sample rate if needed (recommend 0.05-0.2 range)",
                ],
                "before_state": "Sending 2.4TB/day of debug logs to Splunk at full volume",
                "after_state": "Send 240GB/day of sampled debug logs (10% sample)",
                "impact_estimate": {
                    "cost_savings_annual": 18720.0,
                    "storage_reduction_gb": 788.4,
                    "performance_improvement": "15% reduction in Splunk indexer load",
                    "time_to_implement": "45 minutes",
                },
                "implementation_effort": "low",
                "related_findings": ["finding-storage-003"],
                "documentation_links": ["https://docs.cribl.io/stream/sampling-function"],
                "created_at": "2025-12-10T14:02:15Z",
            }
        }
