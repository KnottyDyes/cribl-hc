"""
Unit tests for BestPracticeRule model.
"""

import pytest
from pydantic import ValidationError

from cribl_hc.models.rule import BestPracticeRule


class TestBestPracticeRule:
    """Test BestPracticeRule model validation and behavior."""

    def test_valid_best_practice_rule(self):
        """Test creating a valid best practice rule."""
        rule = BestPracticeRule(
            id="rule-bp-001",
            name="Pipeline functions ordered for efficiency",
            category="performance",
            description="Filtering functions should appear early in pipelines",
            rationale="Reduces data volume processed by downstream functions",
            check_type="config_pattern",
            validation_logic="functions[0].id in ['drop', 'sampling']",
            severity_if_violated="medium",
            documentation_link="https://docs.cribl.io/stream/pipeline-best-practices",
        )

        assert rule.id == "rule-bp-001"
        assert rule.name == "Pipeline functions ordered for efficiency"
        assert rule.category == "performance"
        assert rule.check_type == "config_pattern"
        assert rule.severity_if_violated == "medium"
        assert rule.documentation_link == "https://docs.cribl.io/stream/pipeline-best-practices"
        assert rule.cribl_version_min is None
        assert rule.cribl_version_max is None
        assert rule.enabled is True

    def test_all_check_types(self):
        """Test all valid check types."""
        check_types = ["config_pattern", "metric_threshold", "relationship"]

        for check_type in check_types:
            rule = BestPracticeRule(
                id=f"rule-{check_type}",
                name="Test Rule",
                category="test",
                description="Test",
                rationale="Test",
                check_type=check_type,  # type: ignore
                validation_logic="test",
                severity_if_violated="low",
                documentation_link="https://docs.cribl.io/test",
            )
            assert rule.check_type == check_type

    def test_invalid_check_type(self):
        """Test that invalid check type is rejected."""
        with pytest.raises(ValidationError):
            BestPracticeRule(
                id="test",
                name="Test",
                category="test",
                description="Test",
                rationale="Test",
                check_type="invalid_type",  # type: ignore
                validation_logic="test",
                severity_if_violated="low",
                documentation_link="https://docs.cribl.io/test",
            )

    def test_all_severity_levels(self):
        """Test all valid severity levels."""
        severities = ["critical", "high", "medium", "low"]

        for severity in severities:
            rule = BestPracticeRule(
                id=f"rule-{severity}",
                name="Test Rule",
                category="test",
                description="Test",
                rationale="Test",
                check_type="config_pattern",
                validation_logic="test",
                severity_if_violated=severity,  # type: ignore
                documentation_link="https://docs.cribl.io/test",
            )
            assert rule.severity_if_violated == severity

    def test_invalid_severity(self):
        """Test that invalid severity is rejected."""
        with pytest.raises(ValidationError):
            BestPracticeRule(
                id="test",
                name="Test",
                category="test",
                description="Test",
                rationale="Test",
                check_type="config_pattern",
                validation_logic="test",
                severity_if_violated="info",  # type: ignore
                documentation_link="https://docs.cribl.io/test",
            )

    def test_rule_with_version_range(self):
        """Test rule with Cribl version range specified."""
        rule = BestPracticeRule(
            id="rule-versioned",
            name="Version-specific rule",
            category="compatibility",
            description="Applies to 4.x only",
            rationale="Deprecated in 5.x",
            check_type="config_pattern",
            validation_logic="test",
            severity_if_violated="low",
            documentation_link="https://docs.cribl.io/test",
            cribl_version_min="4.0.0",
            cribl_version_max="4.9.9",
        )

        assert rule.cribl_version_min == "4.0.0"
        assert rule.cribl_version_max == "4.9.9"

    def test_invalid_cribl_version_format(self):
        """Test that invalid Cribl version format is rejected."""
        # Invalid min version
        with pytest.raises(ValidationError):
            BestPracticeRule(
                id="test",
                name="Test",
                category="test",
                description="Test",
                rationale="Test",
                check_type="config_pattern",
                validation_logic="test",
                severity_if_violated="low",
                documentation_link="https://docs.cribl.io/test",
                cribl_version_min="4.5",  # Missing patch version
            )

        # Invalid max version
        with pytest.raises(ValidationError):
            BestPracticeRule(
                id="test",
                name="Test",
                category="test",
                description="Test",
                rationale="Test",
                check_type="config_pattern",
                validation_logic="test",
                severity_if_violated="low",
                documentation_link="https://docs.cribl.io/test",
                cribl_version_max="5.x.x",  # Non-numeric
            )

    def test_rule_can_be_disabled(self):
        """Test that rules can be disabled."""
        rule = BestPracticeRule(
            id="rule-disabled",
            name="Disabled Rule",
            category="test",
            description="Test",
            rationale="Test",
            check_type="config_pattern",
            validation_logic="test",
            severity_if_violated="low",
            documentation_link="https://docs.cribl.io/test",
            enabled=False,
        )

        assert rule.enabled is False

    def test_rule_enabled_by_default(self):
        """Test that rules are enabled by default."""
        rule = BestPracticeRule(
            id="rule-default",
            name="Default Rule",
            category="test",
            description="Test",
            rationale="Test",
            check_type="config_pattern",
            validation_logic="test",
            severity_if_violated="low",
            documentation_link="https://docs.cribl.io/test",
        )

        assert rule.enabled is True

    def test_config_pattern_validation_logic(self):
        """Test rule with config_pattern validation logic."""
        rule = BestPracticeRule(
            id="rule-pattern",
            name="Pattern Rule",
            category="performance",
            description="Check pipeline function order",
            rationale="Efficiency",
            check_type="config_pattern",
            validation_logic="functions[0].id in ['drop', 'sampling', 'eval'] and 'filter' in functions[0]",
            severity_if_violated="medium",
            documentation_link="https://docs.cribl.io/stream/pipeline-best-practices#ordering",
        )

        assert "functions[0]" in rule.validation_logic
        assert rule.check_type == "config_pattern"

    def test_metric_threshold_validation_logic(self):
        """Test rule with metric_threshold validation logic."""
        rule = BestPracticeRule(
            id="rule-threshold",
            name="CPU Threshold",
            category="performance",
            description="CPU should not exceed 80%",
            rationale="Performance degradation",
            check_type="metric_threshold",
            validation_logic="cpu_percent > 80",
            severity_if_violated="high",
            documentation_link="https://docs.cribl.io/stream/monitoring",
        )

        assert "cpu_percent" in rule.validation_logic
        assert rule.check_type == "metric_threshold"

    def test_relationship_validation_logic(self):
        """Test rule with relationship validation logic."""
        rule = BestPracticeRule(
            id="rule-relationship",
            name="Route References Valid Pipeline",
            category="configuration",
            description="Routes must reference existing pipelines",
            rationale="Prevent broken references",
            check_type="relationship",
            validation_logic="route.pipeline in available_pipelines",
            severity_if_violated="critical",
            documentation_link="https://docs.cribl.io/stream/routes",
        )

        assert "route.pipeline" in rule.validation_logic
        assert rule.check_type == "relationship"
        assert rule.severity_if_violated == "critical"

    def test_rule_categories(self):
        """Test rules with different categories."""
        categories = ["performance", "security", "reliability", "cost", "compliance"]

        for category in categories:
            rule = BestPracticeRule(
                id=f"rule-{category}",
                name=f"{category.title()} Rule",
                category=category,
                description=f"Test {category} rule",
                rationale=f"Ensures {category}",
                check_type="config_pattern",
                validation_logic="test",
                severity_if_violated="medium",
                documentation_link="https://docs.cribl.io/test",
            )
            assert rule.category == category
