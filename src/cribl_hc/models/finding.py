"""
Finding model for identified problems and improvement opportunities.
"""

from datetime import datetime
from typing import Any, List, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class Finding(BaseModel):
    """
    Identified problem or improvement opportunity with remediation guidance.

    Severity Levels:
    - critical: Immediate action required, service at risk
    - high: Significant issue, should address within 24 hours
    - medium: Notable issue, address within 1 week
    - low: Minor issue, address when convenient
    - info: Informational, no action required

    Attributes:
        id: Unique identifier for this finding
        category: Objective category (e.g., "health", "config", "security")
        severity: Finding severity level
        title: Brief title
        description: Detailed description of the issue
        affected_components: Components affected (e.g., ["worker-01", "pipeline-logs"])
        remediation_steps: Step-by-step fix instructions
        documentation_links: URLs to Cribl documentation
        estimated_impact: Impact description
        confidence_level: Confidence in this finding
        product_tags: Products this finding applies to (e.g., ["stream"], ["edge"], ["lake"], ["search"], or any combination)
        detected_at: When finding was detected
        metadata: Additional context data

    Example:
        >>> finding = Finding(
        ...     id="finding-mem-001",
        ...     category="health",
        ...     severity="high",
        ...     title="Worker node approaching memory exhaustion",
        ...     description="Worker worker-01 is using 92% of allocated memory",
        ...     affected_components=["worker-01"],
        ...     remediation_steps=["Review worker memory allocation"],
        ...     documentation_links=["https://docs.cribl.io/stream/sizing-workers"],
        ...     estimated_impact="High risk of worker crash",
        ...     confidence_level="high"
        ... )
    """

    id: str = Field(..., description="Unique finding identifier", min_length=1)
    category: str = Field(..., description="Objective category", min_length=1)
    severity: Literal["critical", "high", "medium", "low", "info"] = Field(
        ..., description="Finding severity"
    )
    title: str = Field(..., description="Brief title", min_length=1, max_length=255)
    description: str = Field(..., description="Detailed description", min_length=1)
    affected_components: list[str] = Field(
        default_factory=list, description="Affected components"
    )
    remediation_steps: list[str] = Field(
        default_factory=list, description="Fix instructions"
    )
    documentation_links: list[str] = Field(default_factory=list, description="Cribl docs URLs")
    estimated_impact: str = Field(default="", description="Impact description")
    confidence_level: Literal["high", "medium", "low"] = Field(
        ..., description="Confidence level"
    )
    product_tags: List[Literal["stream", "edge", "lake", "search"]] = Field(
        default_factory=lambda: ["stream", "edge", "lake", "search"],
        description="Products this finding applies to"
    )
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")

    @model_validator(mode="after")
    def validate_severity_requirements(self) -> "Finding":
        """Validate remediation steps and impact based on severity."""
        # Validate remediation steps for critical/high/medium
        if self.severity in ["critical", "high", "medium"] and len(self.remediation_steps) == 0:
            raise ValueError(
                f"Remediation steps required for {self.severity} severity findings"
            )

        # Validate estimated impact for critical/high
        if self.severity in ["critical", "high"] and not self.estimated_impact:
            raise ValueError(
                f"Estimated impact required for {self.severity} severity findings"
            )

        return self

    @field_validator("documentation_links")
    @classmethod
    def validate_documentation_links(cls, v: list[str]) -> list[str]:
        """Validate documentation links are valid URLs to docs.cribl.io domain."""
        for link in v:
            # Basic URL validation
            if not link.startswith(("http://", "https://")):
                raise ValueError(f"Documentation link must be a valid URL: {link}")

            # Prefer docs.cribl.io domain but allow other domains for flexibility
            # (e.g., community forums, blog posts, etc.)

        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "finding-mem-001",
                "category": "health",
                "severity": "high",
                "title": "Worker node approaching memory exhaustion",
                "description": "Worker worker-01 is using 92% of allocated memory (14.7GB of 16GB). "
                "Persistent high memory usage may lead to OOM kills and data loss.",
                "affected_components": ["worker-01"],
                "remediation_steps": [
                    "Review worker memory allocation in worker group settings",
                    "Consider vertical scaling: increase worker memory to 24GB",
                    "Investigate memory-intensive pipelines on this worker",
                    "Check for memory leaks in custom functions",
                ],
                "documentation_links": [
                    "https://docs.cribl.io/stream/sizing-workers",
                    "https://docs.cribl.io/stream/monitoring#memory",
                ],
                "estimated_impact": "High risk of worker crash and data loss if memory exhaustion occurs",
                "confidence_level": "high",
                "detected_at": "2025-12-10T14:01:23Z",
                "metadata": {
                    "current_memory_gb": 14.7,
                    "allocated_memory_gb": 16,
                    "utilization_percent": 92,
                },
            }
        }
