"""
Unit tests for Pydantic models.
"""

import pytest
from pydantic import ValidationError

from cribl_hc.models.finding import Finding


class TestFindingModel:
    """Tests for the Finding model."""

    def test_finding_creation_success(self):
        """Test successful creation of a Finding."""
        finding = Finding(
            id="test-finding",
            category="test",
            severity="medium",
            title="Test Finding",
            description="This is a test finding.",
            confidence_level="medium",
            remediation_steps=["Do the thing"],
        )
        assert finding.id == "test-finding"
        assert finding.severity == "medium"

    def test_finding_invalid_severity(self):
        """Test that an invalid severity raises a validation error."""
        with pytest.raises(ValidationError):
            Finding(
                id="test-finding",
                category="test",
                severity="not-a-real-severity",
                title="Test Finding",
                description="This is a test finding.",
            )
