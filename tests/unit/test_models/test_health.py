"""
Unit tests for HealthScore and ComponentScore models.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from cribl_hc.models.health import ComponentScore, HealthScore


class TestComponentScore:
    """Test ComponentScore model validation."""

    def test_valid_component_score(self):
        """Test creating a valid component score."""
        comp = ComponentScore(
            name="Worker Health",
            score=85,
            weight=0.25,
            details="3 of 5 workers healthy",
        )

        assert comp.name == "Worker Health"
        assert comp.score == 85
        assert comp.weight == 0.25
        assert comp.details == "3 of 5 workers healthy"

    def test_score_boundaries(self):
        """Test score boundary validation (0-100)."""
        # Valid boundaries
        ComponentScore(name="Test", score=0, weight=0.5, details="Min")
        ComponentScore(name="Test", score=100, weight=0.5, details="Max")

        # Invalid: below 0
        with pytest.raises(ValidationError):
            ComponentScore(name="Test", score=-1, weight=0.5, details="Below min")

        # Invalid: above 100
        with pytest.raises(ValidationError):
            ComponentScore(name="Test", score=101, weight=0.5, details="Above max")

    def test_weight_boundaries(self):
        """Test weight boundary validation (0-1)."""
        # Valid boundaries
        ComponentScore(name="Test", score=50, weight=0.0, details="Min weight")
        ComponentScore(name="Test", score=50, weight=1.0, details="Max weight")

        # Invalid: below 0
        with pytest.raises(ValidationError):
            ComponentScore(name="Test", score=50, weight=-0.1, details="Negative")

        # Invalid: above 1
        with pytest.raises(ValidationError):
            ComponentScore(name="Test", score=50, weight=1.1, details="Too high")


class TestHealthScore:
    """Test HealthScore model validation and behavior."""

    def test_valid_health_score(self):
        """Test creating a valid health score."""
        components = {
            "workers": ComponentScore(
                name="Worker Health", score=85, weight=0.6, details="3/5 healthy"
            ),
            "config": ComponentScore(
                name="Configuration", score=70, weight=0.4, details="Some warnings"
            ),
        }

        health = HealthScore(overall_score=79, components=components)

        assert health.overall_score == 79
        assert len(health.components) == 2
        assert "workers" in health.components
        assert "config" in health.components
        assert isinstance(health.timestamp, datetime)
        assert health.trend_direction is None
        assert health.previous_score is None

    def test_health_score_with_trend(self):
        """Test health score with trend direction."""
        components = {
            "workers": ComponentScore(
                name="Workers", score=80, weight=1.0, details="Good"
            )
        }

        health = HealthScore(
            overall_score=80,
            components=components,
            trend_direction="improving",
            previous_score=75,
        )

        assert health.trend_direction == "improving"
        assert health.previous_score == 75

    def test_component_weights_must_sum_to_one(self):
        """Test that component weights must sum to approximately 1.0."""
        # Valid: weights sum to 1.0
        components_valid = {
            "a": ComponentScore(name="A", score=80, weight=0.5, details="A"),
            "b": ComponentScore(name="B", score=70, weight=0.5, details="B"),
        }
        HealthScore(overall_score=75, components=components_valid)

        # Invalid: weights sum to 0.8
        components_invalid = {
            "a": ComponentScore(name="A", score=80, weight=0.3, details="A"),
            "b": ComponentScore(name="B", score=70, weight=0.5, details="B"),
        }
        with pytest.raises(ValidationError) as exc_info:
            HealthScore(overall_score=75, components=components_invalid)

        errors = exc_info.value.errors()
        assert any("sum to 1.0" in str(e.get("msg", "")) for e in errors)

    def test_component_weights_tolerance(self):
        """Test that small floating point errors are tolerated."""
        # Weights sum to 0.9999999 (within tolerance)
        components = {
            "a": ComponentScore(name="A", score=80, weight=0.333333, details="A"),
            "b": ComponentScore(name="B", score=70, weight=0.333333, details="B"),
            "c": ComponentScore(name="C", score=90, weight=0.333334, details="C"),
        }

        # Should not raise error due to tolerance
        health = HealthScore(overall_score=80, components=components)
        assert health.overall_score == 80

    def test_trend_requires_previous_score(self):
        """Test that trend_direction requires previous_score."""
        components = {
            "workers": ComponentScore(
                name="Workers", score=80, weight=1.0, details="Good"
            )
        }

        # Invalid: trend without previous_score
        with pytest.raises(ValidationError) as exc_info:
            HealthScore(
                overall_score=80, components=components, trend_direction="improving"
            )

        errors = exc_info.value.errors()
        assert any("requires previous_score" in str(e.get("msg", "")) for e in errors)

    def test_overall_score_boundaries(self):
        """Test overall score boundary validation (0-100)."""
        components = {
            "test": ComponentScore(name="Test", score=50, weight=1.0, details="Test")
        }

        # Valid boundaries
        HealthScore(overall_score=0, components=components)
        HealthScore(overall_score=100, components=components)

        # Invalid: below 0
        with pytest.raises(ValidationError):
            HealthScore(overall_score=-1, components=components)

        # Invalid: above 100
        with pytest.raises(ValidationError):
            HealthScore(overall_score=101, components=components)

    def test_previous_score_boundaries(self):
        """Test previous score boundary validation."""
        components = {
            "test": ComponentScore(name="Test", score=50, weight=1.0, details="Test")
        }

        # Valid boundaries
        HealthScore(
            overall_score=50,
            components=components,
            trend_direction="stable",
            previous_score=0,
        )
        HealthScore(
            overall_score=50,
            components=components,
            trend_direction="stable",
            previous_score=100,
        )

        # Invalid: below 0
        with pytest.raises(ValidationError):
            HealthScore(
                overall_score=50,
                components=components,
                trend_direction="stable",
                previous_score=-1,
            )

        # Invalid: above 100
        with pytest.raises(ValidationError):
            HealthScore(
                overall_score=50,
                components=components,
                trend_direction="stable",
                previous_score=101,
            )

    def test_empty_components(self):
        """Test that empty components dict is allowed."""
        # Empty components should be allowed (will fail weight validation but that's ok)
        health = HealthScore(overall_score=50, components={})
        assert len(health.components) == 0
