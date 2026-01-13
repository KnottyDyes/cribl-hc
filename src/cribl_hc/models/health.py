from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ComponentScore(BaseModel):
    name: str = Field(..., description="Component name", min_length=1)
    score: int = Field(..., description="Score 0-100", ge=0, le=100)
    weight: float = Field(..., description="Weight in overall score", ge=0.0, le=1.0)
    details: str = Field(..., description="Score explanation", min_length=1)

    model_config = {"populate_by_name": True}


class HealthScore(BaseModel):
    overall_score: int = Field(..., description="Overall score 0-100", ge=0, le=100)
    components: Dict[str, ComponentScore] = Field(..., description="Component scores")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trend_direction: Optional[Literal["improving", "stable", "declining"]] = None
    previous_score: Optional[int] = Field(default=None, ge=0, le=100)

    @field_validator("components")
    @classmethod
    def validate_component_weights(cls, v: Dict[str, ComponentScore]) -> Dict[str, ComponentScore]:
        if not v:
            return v
        total_weight = sum(comp.weight for comp in v.values())
        if not (0.99 <= total_weight <= 1.01):
            raise ValueError(f"Weights must sum to 1.0 (got {total_weight})")
        return v

    @model_validator(mode="after")
    def validate_trend_requires_previous(self) -> "HealthScore":
        if self.trend_direction is not None and self.previous_score is None:
            raise ValueError("trend_direction requires previous_score")
        return self

    model_config = {"populate_by_name": True}
