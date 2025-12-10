"""
Deployment model representing a Cribl Stream environment.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, SecretStr, field_validator, HttpUrl


class Deployment(BaseModel):
    """
    Represents a Cribl Stream deployment (Cloud or self-hosted) with API credentials.

    Attributes:
        id: Unique identifier (lowercase, alphanumeric, hyphens)
        name: Human-readable name
        url: Base URL for Cribl API
        environment_type: cloud or self-hosted
        auth_token: API authentication token (encrypted in storage)
        cribl_version: Detected Cribl version (e.g., "4.5.2")
        created_at: Timestamp when deployment was added
        updated_at: Timestamp of last update
        metadata: Custom key-value pairs for user data

    Example:
        >>> deployment = Deployment(
        ...     id="prod-cribl",
        ...     name="Production Cribl Cluster",
        ...     url="https://cribl.example.com",
        ...     environment_type="self-hosted",
        ...     auth_token="secret-token-123"
        ... )
    """

    id: str = Field(
        ...,
        description="Unique identifier (lowercase, alphanumeric, hyphens)",
        pattern=r"^[a-z0-9-]+$",
        min_length=1,
        max_length=64,
    )
    name: str = Field(..., description="Human-readable name", min_length=1, max_length=255)
    url: HttpUrl = Field(..., description="Base URL for Cribl API")
    environment_type: Literal["cloud", "self-hosted"] = Field(
        ..., description="Environment type"
    )
    auth_token: SecretStr = Field(..., description="API authentication token (encrypted)")
    cribl_version: Optional[str] = Field(
        None, description="Detected Cribl version", pattern=r"^\d+\.\d+\.\d+$"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate deployment ID is lowercase alphanumeric with hyphens."""
        if not v.islower():
            raise ValueError("Deployment ID must be lowercase")
        return v

    @field_validator("cribl_version")
    @classmethod
    def validate_cribl_version(cls, v: Optional[str]) -> Optional[str]:
        """Validate Cribl version format if provided."""
        if v is None:
            return v

        # Version should be in format X.Y.Z
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Cribl version must be in format X.Y.Z")

        # All parts should be numeric
        try:
            [int(p) for p in parts]
        except ValueError:
            raise ValueError("Cribl version parts must be numeric")

        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "prod-cribl",
                "name": "Production Cribl Cluster",
                "url": "https://cribl.example.com",
                "environment_type": "self-hosted",
                "auth_token": "**SECRET**",
                "cribl_version": "4.5.2",
                "created_at": "2025-12-10T10:00:00Z",
                "updated_at": "2025-12-10T10:00:00Z",
                "metadata": {"region": "us-east-1", "team": "platform"},
            }
        }
