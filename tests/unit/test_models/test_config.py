"""
Unit tests for ConfigurationElement model.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from cribl_hc.models.config import ConfigurationElement


class TestConfigurationElement:
    """Test ConfigurationElement model validation and behavior."""

    def test_valid_configuration_element(self):
        """Test creating a valid configuration element."""
        config = ConfigurationElement(
            id="pipeline-logs-processing",
            type="pipeline",
            name="logs-processing",
            group_id="default",
            definition={"id": "logs-processing", "functions": []},
            usage_status="active",
            validation_status="valid",
            best_practice_compliance=0.85,
        )

        assert config.id == "pipeline-logs-processing"
        assert config.type == "pipeline"
        assert config.name == "logs-processing"
        assert config.group_id == "default"
        assert config.definition == {"id": "logs-processing", "functions": []}
        assert config.usage_status == "active"
        assert config.validation_status == "valid"
        assert config.best_practice_compliance == 0.85
        assert config.validation_errors == []
        assert config.validation_warnings == []
        assert config.last_modified is None
        assert config.metadata == {}

    def test_all_configuration_types(self):
        """Test all valid configuration types."""
        types = ["pipeline", "route", "function", "destination", "input", "lookup"]

        for config_type in types:
            config = ConfigurationElement(
                id=f"config-{config_type}",
                type=config_type,  # type: ignore
                name=config_type,
                group_id="default",
                definition={},
                usage_status="active",
                validation_status="valid",
                best_practice_compliance=1.0,
            )
            assert config.type == config_type

    def test_invalid_configuration_type(self):
        """Test that invalid type is rejected."""
        with pytest.raises(ValidationError):
            ConfigurationElement(
                id="test",
                type="invalid-type",  # type: ignore
                name="test",
                group_id="default",
                definition={},
                usage_status="active",
                validation_status="valid",
                best_practice_compliance=1.0,
            )

    def test_all_usage_statuses(self):
        """Test all valid usage status values."""
        statuses = ["active", "unused", "orphaned"]

        for status in statuses:
            config = ConfigurationElement(
                id=f"config-{status}",
                type="pipeline",
                name="test",
                group_id="default",
                definition={},
                usage_status=status,  # type: ignore
                validation_status="valid",
                best_practice_compliance=1.0,
            )
            assert config.usage_status == status

    def test_all_validation_statuses(self):
        """Test all valid validation status values."""
        statuses = ["valid", "syntax_error", "logic_error", "warning"]

        for status in statuses:
            config = ConfigurationElement(
                id=f"config-{status}",
                type="pipeline",
                name="test",
                group_id="default",
                definition={},
                usage_status="active",
                validation_status=status,  # type: ignore
                best_practice_compliance=1.0,
            )
            assert config.validation_status == status

    def test_best_practice_compliance_boundaries(self):
        """Test best practice compliance score validation (0-1)."""
        # Valid boundaries
        ConfigurationElement(
            id="test-min",
            type="pipeline",
            name="test",
            group_id="default",
            definition={},
            usage_status="active",
            validation_status="valid",
            best_practice_compliance=0.0,
        )

        ConfigurationElement(
            id="test-max",
            type="pipeline",
            name="test",
            group_id="default",
            definition={},
            usage_status="active",
            validation_status="valid",
            best_practice_compliance=1.0,
        )

        # Invalid: below 0
        with pytest.raises(ValidationError):
            ConfigurationElement(
                id="test",
                type="pipeline",
                name="test",
                group_id="default",
                definition={},
                usage_status="active",
                validation_status="valid",
                best_practice_compliance=-0.1,
            )

        # Invalid: above 1
        with pytest.raises(ValidationError):
            ConfigurationElement(
                id="test",
                type="pipeline",
                name="test",
                group_id="default",
                definition={},
                usage_status="active",
                validation_status="valid",
                best_practice_compliance=1.1,
            )

    def test_configuration_with_errors_and_warnings(self):
        """Test configuration with validation errors and warnings."""
        config = ConfigurationElement(
            id="pipeline-with-issues",
            type="pipeline",
            name="problematic",
            group_id="default",
            definition={},
            usage_status="active",
            validation_status="warning",
            best_practice_compliance=0.75,
            validation_errors=["Error 1", "Error 2"],
            validation_warnings=["Warning 1", "Warning 2", "Warning 3"],
        )

        assert len(config.validation_errors) == 2
        assert len(config.validation_warnings) == 3
        assert "Error 1" in config.validation_errors
        assert "Warning 1" in config.validation_warnings

    def test_configuration_with_last_modified(self):
        """Test configuration with last_modified timestamp."""
        timestamp = datetime(2025, 11, 15, 8, 30, 0)
        config = ConfigurationElement(
            id="test",
            type="pipeline",
            name="test",
            group_id="default",
            definition={},
            usage_status="active",
            validation_status="valid",
            best_practice_compliance=1.0,
            last_modified=timestamp,
        )

        assert config.last_modified == timestamp

    def test_configuration_with_metadata(self):
        """Test configuration with custom metadata."""
        metadata = {"routes_using": ["route-splunk", "route-s3"], "author": "admin"}

        config = ConfigurationElement(
            id="test",
            type="pipeline",
            name="test",
            group_id="default",
            definition={"id": "test", "functions": []},
            usage_status="active",
            validation_status="valid",
            best_practice_compliance=1.0,
            metadata=metadata,
        )

        assert config.metadata == metadata
        assert "routes_using" in config.metadata
        assert len(config.metadata["routes_using"]) == 2

    def test_complex_definition(self):
        """Test configuration with complex nested definition."""
        definition = {
            "id": "logs-processing",
            "functions": [
                {
                    "id": "eval",
                    "filter": "true",
                    "add": [{"name": "_processed", "value": "true"}],
                },
                {"id": "drop", "filter": "_raw == null"},
            ],
            "description": "Process log data",
        }

        config = ConfigurationElement(
            id="pipeline-complex",
            type="pipeline",
            name="complex-pipeline",
            group_id="default",
            definition=definition,
            usage_status="active",
            validation_status="valid",
            best_practice_compliance=0.9,
        )

        assert config.definition == definition
        assert len(config.definition["functions"]) == 2
