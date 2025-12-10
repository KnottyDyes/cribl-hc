"""
Best practice rule model for configuration validation.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class BestPracticeRule(BaseModel):
    """
    Validation rule derived from Cribl documentation (configuration-driven).

    Rules are loaded from YAML configuration files and used to validate
    Cribl Stream configurations against best practices.

    Check Types:
    - config_pattern: Pattern matching against configuration structure
    - metric_threshold: Numeric threshold checks on metrics
    - relationship: Cross-component relationship validation

    Attributes:
        id: Unique rule identifier
        name: Human-readable rule name
        category: Category (e.g., "performance", "security", "reliability")
        description: Detailed description
        rationale: Why this rule is important
        check_type: Type of validation check
        validation_logic: Python expression or JSONPath query to evaluate
        severity_if_violated: Severity when rule is violated
        documentation_link: Cribl documentation URL
        cribl_version_min: Minimum Cribl version for this rule
        cribl_version_max: Maximum Cribl version (for deprecated rules)
        enabled: Whether this rule is currently enabled

    Example:
        >>> rule = BestPracticeRule(
        ...     id="rule-bp-001",
        ...     name="Pipeline functions ordered for efficiency",
        ...     category="performance",
        ...     description="Filtering functions should appear early in pipelines",
        ...     rationale="Improves throughput and reduces CPU usage",
        ...     check_type="config_pattern",
        ...     validation_logic="functions[0].id in ['drop', 'sampling']",
        ...     severity_if_violated="medium",
        ...     documentation_link="https://docs.cribl.io/stream/pipeline-best-practices"
        ... )
    """

    id: str = Field(..., description="Unique rule identifier", min_length=1)
    name: str = Field(..., description="Human-readable name", min_length=1)
    category: str = Field(..., description="Category", min_length=1)
    description: str = Field(..., description="Detailed description", min_length=1)
    rationale: str = Field(..., description="Why this rule is important", min_length=1)
    check_type: Literal["config_pattern", "metric_threshold", "relationship"] = Field(
        ..., description="Validation check type"
    )
    validation_logic: str = Field(
        ..., description="Python expression or JSONPath query", min_length=1
    )
    severity_if_violated: Literal["critical", "high", "medium", "low"] = Field(
        ..., description="Severity when violated"
    )
    documentation_link: str = Field(..., description="Cribl docs URL", min_length=1)
    cribl_version_min: Optional[str] = Field(
        None,
        description="Minimum Cribl version",
        pattern=r"^\d+\.\d+\.\d+$"
    )
    cribl_version_max: Optional[str] = Field(
        None,
        description="Maximum Cribl version (for deprecated rules)",
        pattern=r"^\d+\.\d+\.\d+$"
    )
    enabled: bool = Field(True, description="Whether rule is enabled")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "rule-bp-001",
                "name": "Pipeline functions ordered for efficiency",
                "category": "performance",
                "description": "Filtering functions should appear early in pipelines to reduce "
                "data volume processed by downstream functions",
                "rationale": "Processing fewer events through expensive operations (regex, lookups) "
                "improves throughput and reduces CPU usage",
                "check_type": "config_pattern",
                "validation_logic": "functions[0].id in ['drop', 'sampling', 'eval'] and 'filter' in functions[0]",
                "severity_if_violated": "medium",
                "documentation_link": "https://docs.cribl.io/stream/pipeline-best-practices#ordering",
                "cribl_version_min": "4.0.0",
                "cribl_version_max": None,
                "enabled": True,
            }
        }
