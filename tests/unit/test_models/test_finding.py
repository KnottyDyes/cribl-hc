"""
Unit tests for Finding model.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from cribl_hc.models.finding import Finding


class TestFinding:
    """Test Finding model validation and behavior."""

    def test_valid_finding_creation(self):
        """Test creating a valid finding."""
        finding = Finding(
            id="finding-001",
            category="health",
            severity="high",
            title="Worker memory exhaustion",
            description="Worker using 92% memory",
            affected_components=["worker-01"],
            remediation_steps=["Increase memory allocation"],
            documentation_links=["https://docs.cribl.io/stream/sizing-workers"],
            estimated_impact="High risk of crash",
            confidence_level="high",
        )

        assert finding.id == "finding-001"
        assert finding.category == "health"
        assert finding.severity == "high"
        assert finding.title == "Worker memory exhaustion"
        assert len(finding.affected_components) == 1
        assert len(finding.remediation_steps) == 1
        assert len(finding.documentation_links) == 1
        assert finding.estimated_impact == "High risk of crash"
        assert finding.confidence_level == "high"
        assert isinstance(finding.detected_at, datetime)
        assert finding.metadata == {}

    def test_all_severity_levels(self):
        """Test all valid severity levels."""
        severities = ["critical", "high", "medium", "low", "info"]

        for severity in severities:
            # critical/high/medium require remediation steps
            remediation = ["Fix it"] if severity in ["critical", "high", "medium"] else []
            # critical/high require estimated impact
            impact = "Impact description" if severity in ["critical", "high"] else ""

            finding = Finding(
                id=f"finding-{severity}",
                category="test",
                severity=severity,  # type: ignore
                title="Test",
                description="Test finding",
                confidence_level="medium",
                remediation_steps=remediation,
                estimated_impact=impact,
            )
            assert finding.severity == severity

    def test_invalid_severity(self):
        """Test that invalid severity is rejected."""
        with pytest.raises(ValidationError):
            Finding(
                id="test",
                category="test",
                severity="extreme",  # type: ignore
                title="Test",
                description="Test",
                confidence_level="high",
            )

    def test_remediation_steps_required_for_critical(self):
        """Test that remediation steps are required for critical severity."""
        with pytest.raises(ValidationError) as exc_info:
            Finding(
                id="test",
                category="test",
                severity="critical",
                title="Critical issue",
                description="Very bad",
                remediation_steps=[],  # Empty - should fail
                estimated_impact="System failure",
                confidence_level="high",
            )

        errors = exc_info.value.errors()
        assert any("Remediation steps required" in str(e.get("msg", "")) for e in errors)

    def test_remediation_steps_required_for_high(self):
        """Test that remediation steps are required for high severity."""
        with pytest.raises(ValidationError) as exc_info:
            Finding(
                id="test",
                category="test",
                severity="high",
                title="High issue",
                description="Bad",
                estimated_impact="Potential data loss",
                confidence_level="high",
            )

        errors = exc_info.value.errors()
        assert any("Remediation steps required" in str(e.get("msg", "")) for e in errors)

    def test_remediation_steps_required_for_medium(self):
        """Test that remediation steps are required for medium severity."""
        with pytest.raises(ValidationError) as exc_info:
            Finding(
                id="test",
                category="test",
                severity="medium",
                title="Medium issue",
                description="Needs attention",
                confidence_level="medium",
            )

        errors = exc_info.value.errors()
        assert any("Remediation steps required" in str(e.get("msg", "")) for e in errors)

    def test_remediation_steps_not_required_for_low(self):
        """Test that remediation steps are optional for low severity."""
        finding = Finding(
            id="test",
            category="test",
            severity="low",
            title="Low issue",
            description="Minor problem",
            confidence_level="low",
        )
        assert finding.remediation_steps == []

    def test_remediation_steps_not_required_for_info(self):
        """Test that remediation steps are optional for info severity."""
        finding = Finding(
            id="test",
            category="test",
            severity="info",
            title="Informational",
            description="FYI",
            confidence_level="medium",
        )
        assert finding.remediation_steps == []

    def test_estimated_impact_required_for_critical(self):
        """Test that estimated impact is required for critical severity."""
        with pytest.raises(ValidationError) as exc_info:
            Finding(
                id="test",
                category="test",
                severity="critical",
                title="Critical",
                description="Bad",
                remediation_steps=["Fix it"],
                estimated_impact="",  # Empty - should fail
                confidence_level="high",
            )

        errors = exc_info.value.errors()
        assert any("Estimated impact required" in str(e.get("msg", "")) for e in errors)

    def test_estimated_impact_required_for_high(self):
        """Test that estimated impact is required for high severity."""
        with pytest.raises(ValidationError) as exc_info:
            Finding(
                id="test",
                category="test",
                severity="high",
                title="High",
                description="Bad",
                remediation_steps=["Fix it"],
                confidence_level="high",
            )

        errors = exc_info.value.errors()
        assert any("Estimated impact required" in str(e.get("msg", "")) for e in errors)

    def test_estimated_impact_not_required_for_medium(self):
        """Test that estimated impact is optional for medium severity."""
        finding = Finding(
            id="test",
            category="test",
            severity="medium",
            title="Medium",
            description="Issue",
            remediation_steps=["Fix"],
            confidence_level="medium",
        )
        assert finding.estimated_impact == ""

    def test_documentation_links_validation(self):
        """Test documentation links URL validation."""
        # Valid HTTP/HTTPS URLs
        finding = Finding(
            id="test",
            category="test",
            severity="low",
            title="Test",
            description="Test",
            documentation_links=[
                "https://docs.cribl.io/stream/test",
                "http://docs.cribl.io/other",
            ],
            confidence_level="medium",
        )
        assert len(finding.documentation_links) == 2

        # Invalid: not a URL
        with pytest.raises(ValidationError) as exc_info:
            Finding(
                id="test",
                category="test",
                severity="low",
                title="Test",
                description="Test",
                documentation_links=["not-a-url"],
                confidence_level="medium",
            )

        errors = exc_info.value.errors()
        assert any("valid URL" in str(e.get("msg", "")) for e in errors)

    def test_confidence_levels(self):
        """Test all valid confidence levels."""
        levels = ["high", "medium", "low"]

        for level in levels:
            finding = Finding(
                id=f"test-{level}",
                category="test",
                severity="info",
                title="Test",
                description="Test",
                confidence_level=level,  # type: ignore
            )
            assert finding.confidence_level == level

    def test_finding_with_metadata(self):
        """Test finding with custom metadata."""
        metadata = {
            "current_memory_gb": 14.7,
            "allocated_memory_gb": 16,
            "utilization_percent": 92,
        }

        finding = Finding(
            id="test",
            category="health",
            severity="info",
            title="Test",
            description="Test",
            confidence_level="high",
            metadata=metadata,
        )

        assert finding.metadata == metadata
        assert finding.metadata["current_memory_gb"] == 14.7
