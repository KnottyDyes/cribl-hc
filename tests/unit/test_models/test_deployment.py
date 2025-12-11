"""
Unit tests for Deployment model.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from cribl_hc.models.deployment import Deployment


class TestDeployment:
    """Test Deployment model validation and behavior."""

    def test_valid_deployment_creation(self):
        """Test creating a valid deployment."""
        deployment = Deployment(
            id="prod-cribl",
            name="Production Cribl Cluster",
            url="https://cribl.example.com",
            environment_type="self-hosted",
            auth_token="secret-token-123",
        )

        assert deployment.id == "prod-cribl"
        assert deployment.name == "Production Cribl Cluster"
        assert str(deployment.url) == "https://cribl.example.com/"
        assert deployment.environment_type == "self-hosted"
        assert deployment.auth_token.get_secret_value() == "secret-token-123"
        assert deployment.cribl_version is None
        assert isinstance(deployment.created_at, datetime)
        assert isinstance(deployment.updated_at, datetime)
        assert deployment.metadata == {}

    def test_deployment_with_cloud_environment(self):
        """Test deployment with cloud environment type."""
        deployment = Deployment(
            id="cloud-prod",
            name="Cloud Production",
            url="https://myorg.cribl.cloud",
            environment_type="cloud",
            auth_token="cloud-token",
        )

        assert deployment.environment_type == "cloud"

    def test_deployment_with_cribl_version(self):
        """Test deployment with Cribl version specified."""
        deployment = Deployment(
            id="test-deployment",
            name="Test",
            url="https://test.example.com",
            environment_type="self-hosted",
            auth_token="token",
            cribl_version="4.5.2",
        )

        assert deployment.cribl_version == "4.5.2"

    def test_deployment_with_metadata(self):
        """Test deployment with custom metadata."""
        metadata = {"region": "us-east-1", "team": "platform"}
        deployment = Deployment(
            id="test",
            name="Test",
            url="https://test.example.com",
            environment_type="self-hosted",
            auth_token="token",
            metadata=metadata,
        )

        assert deployment.metadata == metadata

    def test_invalid_deployment_id_uppercase(self):
        """Test that uppercase deployment ID is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Deployment(
                id="PROD-CRIBL",
                name="Production",
                url="https://cribl.example.com",
                environment_type="self-hosted",
                auth_token="token",
            )

        errors = exc_info.value.errors()
        # Check for either pattern error or custom validator error
        assert any(
            "must be lowercase" in str(e.get("msg", "")).lower()
            or "string_pattern_mismatch" in str(e.get("type", ""))
            for e in errors
        )

    def test_invalid_deployment_id_pattern(self):
        """Test that invalid ID pattern is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Deployment(
                id="invalid_id_with_underscore",
                name="Test",
                url="https://test.example.com",
                environment_type="self-hosted",
                auth_token="token",
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0

    def test_invalid_url(self):
        """Test that invalid URL is rejected."""
        with pytest.raises(ValidationError):
            Deployment(
                id="test",
                name="Test",
                url="not-a-valid-url",
                environment_type="self-hosted",
                auth_token="token",
            )

    def test_invalid_environment_type(self):
        """Test that invalid environment type is rejected."""
        with pytest.raises(ValidationError):
            Deployment(
                id="test",
                name="Test",
                url="https://test.example.com",
                environment_type="on-premises",  # type: ignore
                auth_token="token",
            )

    def test_invalid_cribl_version_format(self):
        """Test that invalid Cribl version format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Deployment(
                id="test",
                name="Test",
                url="https://test.example.com",
                environment_type="self-hosted",
                auth_token="token",
                cribl_version="4.5",  # Missing patch version
            )

        errors = exc_info.value.errors()
        # Check for either pattern error or custom validator error
        assert any(
            "format X.Y.Z" in str(e.get("msg", ""))
            or "string_pattern_mismatch" in str(e.get("type", ""))
            for e in errors
        )

    def test_invalid_cribl_version_non_numeric(self):
        """Test that non-numeric Cribl version is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Deployment(
                id="test",
                name="Test",
                url="https://test.example.com",
                environment_type="self-hosted",
                auth_token="token",
                cribl_version="4.5.x",
            )

        errors = exc_info.value.errors()
        # Check for either pattern error or custom validator error
        assert any(
            "must be numeric" in str(e.get("msg", ""))
            or "string_pattern_mismatch" in str(e.get("type", ""))
            for e in errors
        )

    def test_missing_required_fields(self):
        """Test that missing required fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Deployment()  # type: ignore

        errors = exc_info.value.errors()
        required_fields = {"id", "name", "url", "environment_type", "auth_token"}
        missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}
        assert required_fields.issubset(missing_fields)

    def test_auth_token_is_secret(self):
        """Test that auth_token is stored as SecretStr."""
        deployment = Deployment(
            id="test",
            name="Test",
            url="https://test.example.com",
            environment_type="self-hosted",
            auth_token="super-secret-token",
        )

        # SecretStr representation should not expose the value
        assert "super-secret-token" not in str(deployment.auth_token)
        # But we can get the value explicitly
        assert deployment.auth_token.get_secret_value() == "super-secret-token"

    def test_deployment_json_serialization(self):
        """Test that deployment can be serialized to JSON."""
        deployment = Deployment(
            id="test",
            name="Test",
            url="https://test.example.com",
            environment_type="self-hosted",
            auth_token="token",
            cribl_version="4.5.2",
        )

        json_data = deployment.model_dump()
        assert json_data["id"] == "test"
        assert json_data["name"] == "Test"
        assert json_data["cribl_version"] == "4.5.2"
        # auth_token should be in the dump but as SecretStr
        assert "auth_token" in json_data
