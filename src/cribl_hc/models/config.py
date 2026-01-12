"""
Configuration element model for Cribl Stream configuration components.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ConfigurationElement(BaseModel):
    """
    Pipeline, route, function, destination, or other configurable component.

    Usage Status Definitions:
    - active: Referenced by routes and actively processing data
    - unused: Defined but not referenced by any routes
    - orphaned: References non-existent components (broken dependencies)

    Validation Status Definitions:
    - valid: No errors or warnings
    - syntax_error: Configuration has syntax errors
    - logic_error: Configuration has logical errors
    - warning: Configuration valid but has warnings

    Attributes:
        id: Unique configuration element ID
        type: Configuration element type
        name: Human-readable name
        group_id: Worker group this config belongs to
        definition: Raw configuration JSON/dict
        usage_status: Usage status (active/unused/orphaned)
        validation_status: Validation status (valid/syntax_error/logic_error/warning)
        best_practice_compliance: Best practice compliance score (0-1)
        validation_errors: List of validation errors
        validation_warnings: List of validation warnings
        last_modified: Last modification timestamp
        metadata: Additional metadata

    Example:
        >>> config = ConfigurationElement(
        ...     id="pipeline-logs-processing",
        ...     type="pipeline",
        ...     name="logs-processing",
        ...     group_id="default",
        ...     definition={"id": "logs-processing", "functions": [...]},
        ...     usage_status="active",
        ...     validation_status="warning",
        ...     best_practice_compliance=0.85
        ... )
    """

    id: str = Field(..., description="Configuration element ID", min_length=1)
    type: Literal["pipeline", "route", "function", "destination", "input", "lookup"] = Field(
        ..., description="Element type"
    )
    name: str = Field(..., description="Human-readable name", min_length=1)
    group_id: str = Field(..., description="Worker group ID", min_length=1)
    definition: dict[str, Any] = Field(..., description="Raw configuration JSON")
    usage_status: Literal["active", "unused", "orphaned"] = Field(
        ..., description="Usage status"
    )
    validation_status: Literal["valid", "syntax_error", "logic_error", "warning"] = Field(
        ..., description="Validation status"
    )
    best_practice_compliance: float = Field(
        ..., description="Best practice compliance score", ge=0.0, le=1.0
    )
    validation_errors: list[str] = Field(
        default_factory=list, description="Validation errors"
    )
    validation_warnings: list[str] = Field(
        default_factory=list, description="Validation warnings"
    )
    last_modified: Optional[datetime] = Field(None, description="Last modification time")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "pipeline-logs-processing",
                "type": "pipeline",
                "name": "logs-processing",
                "group_id": "default",
                "definition": {
                    "id": "logs-processing",
                    "functions": [
                        {
                            "id": "eval",
                            "filter": "true",
                            "add": [{"name": "_processed", "value": "true"}],
                        }
                    ],
                },
                "usage_status": "active",
                "validation_status": "warning",
                "best_practice_compliance": 0.85,
                "validation_errors": [],
                "validation_warnings": [
                    "Pipeline uses deprecated 'eval' function syntax, migrate to 'c.Set' method"
                ],
                "last_modified": "2025-11-15T08:30:00Z",
                "metadata": {"routes_using": ["route-splunk", "route-s3"]},
            }
        }
