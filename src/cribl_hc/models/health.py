"""
Health score models for tracking deployment health metrics.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ComponentScore(BaseModel):
    """
    Score for a single health component.

    Attributes:
        name: Human-readable component name
        score: Score from 0-100
        weight: Weight in overall score calculation (0.0-1.0)
        details: Explanation of the score
    """

    name: str = Field(..., description="Component name", min_length=1)
    score: int = Field(..., description="Score 0-100", ge=0, le=100)
    weight: float = Field(..., description="Weight in overall score", ge=0.0, le=1.0)
    details: str = Field(..., description="Score explanation", min_length=1)

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "name": "Worker Health",
                "score": 85,
                "weight": 0.25,
                "details": "3 of 5 workers healthy, 2 with high memory usage",
            }
        }


class HealthScore(BaseModel):
    """
    Overall health score for a Cribl Stream deployment.

    Calculated as weighted average of component scores. Components include:
    - workers: Worker node health (CPU, memory, disk, connectivity)
    - configuration: Configuration validity and best practices
    - security: Security posture and compliance
    - performance: Performance efficiency and optimization
    - reliability: HA, backups, disaster recovery
    - cost_efficiency: License utilization and cost optimization

    Default weights:
    - workers: 0.25
    - configuration: 0.20
    - security: 0.20
    - performance: 0.15
    - reliability: 0.15
    - cost_efficiency: 0.05

    Attributes:
        overall_score: Weighted average score 0-100
        components: Component breakdown with individual scores
        timestamp: When this score was calculated
        trend_direction: Direction of health trend (if historical data available)
        previous_score: Previous overall score for trend calculation

    Example:
        >>> health_score = HealthScore(
        ...     overall_score=78,
        ...     components={
        ...         "workers": ComponentScore(
        ...             name="Worker Health",
        ...             score=85,
        ...             weight=0.25,
        ...             details="3 of 5 workers healthy"
        ...         )
        ...     },
        ...     timestamp=datetime.utcnow()
        ... )
    """

    overall_score: int = Field(..., description="Overall score 0-100", ge=0, le=100)
    components: dict[str, ComponentScore] = Field(..., description="Component scores")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trend_direction: Optional[Literal["improving", "stable", "declining"]] = Field(
        None, description="Health trend direction"
    )
    previous_score: Optional[int] = Field(
        None, description="Previous score for trend", ge=0, le=100
    )

    @field_validator("components")
    @classmethod
    def validate_component_weights(cls, v: dict[str, ComponentScore]) -> dict[str, ComponentScore]:
        """Validate that component weights sum to approximately 1.0."""
        if not v:
            return v

        total_weight = sum(comp.weight for comp in v.values())

        # Allow small floating point tolerance
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(
                f"Component weights must sum to 1.0 (got {total_weight:.3f}). "
                f"Individual weights: {[(k, c.weight) for k, c in v.items()]}"
            )

        return v

    @model_validator(mode="after")
    def validate_trend_requires_previous(self) -> "HealthScore":
        """Validate that trend_direction requires previous_score."""
        if self.trend_direction is not None and self.previous_score is None:
            raise ValueError("trend_direction requires previous_score to be set")
        return self

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "overall_score": 78,
                "components": {
                    "workers": {
                        "name": "Worker Health",
                        "score": 85,
                        "weight": 0.25,
                        "details": "3 of 5 workers healthy, 2 with high memory usage",
                    },
                    "configuration": {
                        "name": "Configuration Quality",
                        "score": 72,
                        "weight": 0.20,
                        "details": "4 syntax errors, 2 deprecated functions found",
                    },
                },
                "timestamp": "2025-12-10T14:03:45Z",
                "trend_direction": "improving",
                "previous_score": 74,
            }
        }
