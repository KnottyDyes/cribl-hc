"""
Finding model for identified problems and improvement opportunities.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Finding(BaseModel):
    """
    Identified problem or improvement opportunity with remediation guidance.
    """

    id: str = Field(..., description="Unique finding identifier", min_length=1)
    category: str = Field(..., description="Objective category", min_length=1)
    severity: Literal["critical", "high", "medium", "low", "info"] = Field(
        ..., description="Finding severity"
    )
    title: str = Field(..., description="Brief title", min_length=1, max_length=255)
    description: str = Field(..., description="Detailed description", min_length=1)
    affected_components: list[str] = Field(default_factory=list, description="Affected components")
    remediation_steps: list[str] = Field(default_factory=list, description="Fix instructions")
    documentation_links: list[str] = Field(default_factory=list, description="Cribl docs URLs")
    estimated_impact: str = Field(default="", description="Impact description")
    confidence_level: Literal["high", "medium", "low"] = Field(..., description="Confidence level")
    product_tags: list[Literal["stream", "edge", "lake", "search"]] = Field(
        default_factory=list,
        description="Products this finding applies to (derived from source analyzer)",
    )
    worker_group: Optional[str] = Field(
        default=None,
        description="Worker group this finding applies to (e.g., 'default', 'prod-group').",
    )
    source_analyzer: str = Field(
        default="", description="Name of the analyzer that generated this finding"
    )
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    grouping_id: Optional[str] = Field(
        default=None, description="Identifier used to group similar findings together."
    )

    @model_validator(mode="after")
    def validate_severity_requirements(self) -> "Finding":
        """Validate remediation steps and impact based on severity."""
        if self.severity in ["critical", "high", "medium"] and len(self.remediation_steps) == 0:
            raise ValueError(f"Remediation steps required for {self.severity} severity findings")

        if self.severity in ["critical", "high"] and not self.estimated_impact:
            raise ValueError(f"Estimated impact required for {self.severity} severity findings")

        return self

    @field_validator("documentation_links")
    @classmethod
    def validate_documentation_links(cls, v: list[str]) -> list[str]:
        """Validate documentation links are valid URLs."""
        for link in v:
            if not link.startswith(("http://", "https://")):
                raise ValueError(f"Documentation link must be a valid URL: {link}")
        return v

    model_config = {"populate_by_name": True}
