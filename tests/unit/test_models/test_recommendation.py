"""
Unit tests for Recommendation and ImpactEstimate models.
"""

import pytest
from pydantic import ValidationError

from cribl_hc.models.recommendation import ImpactEstimate, Recommendation


class TestImpactEstimate:
    """Test ImpactEstimate model validation."""

    def test_valid_impact_estimate(self):
        """Test creating a valid impact estimate."""
        impact = ImpactEstimate(
            cost_savings_annual=18720.0,
            performance_improvement="15% throughput increase",
            storage_reduction_gb=788.4,
            time_to_implement="45 minutes",
        )

        assert impact.cost_savings_annual == 18720.0
        assert impact.performance_improvement == "15% throughput increase"
        assert impact.storage_reduction_gb == 788.4
        assert impact.time_to_implement == "45 minutes"

    def test_impact_estimate_all_optional(self):
        """Test that all impact metrics are optional."""
        impact = ImpactEstimate()
        assert impact.cost_savings_annual is None
        assert impact.performance_improvement is None
        assert impact.storage_reduction_gb is None
        assert impact.time_to_implement is None

    def test_has_impact_metrics_method(self):
        """Test the has_impact_metrics helper method."""
        # No metrics
        impact_none = ImpactEstimate()
        assert not impact_none.has_impact_metrics()

        # Has cost savings
        impact_cost = ImpactEstimate(cost_savings_annual=1000.0)
        assert impact_cost.has_impact_metrics()

        # Has performance
        impact_perf = ImpactEstimate(performance_improvement="Better")
        assert impact_perf.has_impact_metrics()

        # Has storage
        impact_storage = ImpactEstimate(storage_reduction_gb=100.0)
        assert impact_storage.has_impact_metrics()

        # Only time_to_implement doesn't count
        impact_time = ImpactEstimate(time_to_implement="1 hour")
        assert not impact_time.has_impact_metrics()

    def test_negative_cost_savings_rejected(self):
        """Test that negative cost savings is rejected."""
        with pytest.raises(ValidationError):
            ImpactEstimate(cost_savings_annual=-1000.0)

    def test_negative_storage_rejected(self):
        """Test that negative storage reduction is rejected."""
        with pytest.raises(ValidationError):
            ImpactEstimate(storage_reduction_gb=-100.0)


class TestRecommendation:
    """Test Recommendation model validation and behavior."""

    def test_valid_recommendation_creation(self):
        """Test creating a valid recommendation."""
        rec = Recommendation(
            id="rec-001",
            type="optimization",
            priority="p1",
            title="Implement sampling",
            description="Reduce storage by sampling",
            rationale="Debug logs rarely queried",
            implementation_steps=["Add sampling function"],
            before_state="2.4TB/day",
            after_state="240GB/day",
            impact_estimate=ImpactEstimate(cost_savings_annual=18720.0),
            implementation_effort="low",
        )

        assert rec.id == "rec-001"
        assert rec.type == "optimization"
        assert rec.priority == "p1"
        assert rec.title == "Implement sampling"
        assert len(rec.implementation_steps) == 1
        assert rec.implementation_effort == "low"
        assert rec.related_findings == []
        assert rec.documentation_links == []

    def test_all_priority_levels(self):
        """Test all valid priority levels."""
        priorities = ["p0", "p1", "p2", "p3"]

        for priority in priorities:
            # p0 and p1 need impact metrics
            impact = (
                ImpactEstimate(cost_savings_annual=1000.0)
                if priority in ["p0", "p1"]
                else ImpactEstimate()
            )

            rec = Recommendation(
                id=f"rec-{priority}",
                type="test",
                priority=priority,  # type: ignore
                title="Test",
                description="Test",
                rationale="Test",
                implementation_steps=["Step 1"],
                impact_estimate=impact,
                implementation_effort="low",
            )
            assert rec.priority == priority

    def test_invalid_priority(self):
        """Test that invalid priority is rejected."""
        with pytest.raises(ValidationError):
            Recommendation(
                id="test",
                type="test",
                priority="p4",  # type: ignore
                title="Test",
                description="Test",
                rationale="Test",
                implementation_steps=["Step"],
                impact_estimate=ImpactEstimate(),
                implementation_effort="low",
            )

    def test_p0_requires_impact_metrics(self):
        """Test that p0 priority requires impact metrics."""
        with pytest.raises(ValidationError) as exc_info:
            Recommendation(
                id="test",
                type="test",
                priority="p0",
                title="Critical",
                description="Fix now",
                rationale="Important",
                implementation_steps=["Fix"],
                impact_estimate=ImpactEstimate(),  # No metrics
                implementation_effort="high",
            )

        errors = exc_info.value.errors()
        assert any("at least one metric" in str(e.get("msg", "")) for e in errors)

    def test_p1_requires_impact_metrics(self):
        """Test that p1 priority requires impact metrics."""
        with pytest.raises(ValidationError) as exc_info:
            Recommendation(
                id="test",
                type="test",
                priority="p1",
                title="High priority",
                description="Important",
                rationale="Needed",
                implementation_steps=["Do it"],
                impact_estimate=ImpactEstimate(time_to_implement="1 hour"),  # Only time
                implementation_effort="medium",
            )

        errors = exc_info.value.errors()
        assert any("at least one metric" in str(e.get("msg", "")) for e in errors)

    def test_p2_does_not_require_impact_metrics(self):
        """Test that p2 priority does not require impact metrics."""
        rec = Recommendation(
            id="test",
            type="test",
            priority="p2",
            title="Medium",
            description="Can wait",
            rationale="Nice to have",
            implementation_steps=["Eventually"],
            impact_estimate=ImpactEstimate(),
            implementation_effort="low",
        )
        assert rec.priority == "p2"

    def test_optimization_requires_before_state(self):
        """Test that optimization type requires before_state."""
        with pytest.raises(ValidationError) as exc_info:
            Recommendation(
                id="test",
                type="optimization",
                priority="p3",
                title="Optimize",
                description="Make better",
                rationale="Efficiency",
                implementation_steps=["Optimize"],
                before_state="",  # Empty
                after_state="Better state",
                impact_estimate=ImpactEstimate(),
                implementation_effort="medium",
            )

        errors = exc_info.value.errors()
        assert any("before_state required" in str(e.get("msg", "")) for e in errors)

    def test_optimization_requires_after_state(self):
        """Test that optimization type requires after_state."""
        with pytest.raises(ValidationError) as exc_info:
            Recommendation(
                id="test",
                type="optimization",
                priority="p3",
                title="Optimize",
                description="Make better",
                rationale="Efficiency",
                implementation_steps=["Optimize"],
                before_state="Current state",
                after_state="",  # Empty
                impact_estimate=ImpactEstimate(),
                implementation_effort="medium",
            )

        errors = exc_info.value.errors()
        assert any("after_state required" in str(e.get("msg", "")) for e in errors)

    def test_non_optimization_type_no_state_required(self):
        """Test that non-optimization types don't require before/after state."""
        rec = Recommendation(
            id="test",
            type="security",
            priority="p3",
            title="Add encryption",
            description="Encrypt data",
            rationale="Security",
            implementation_steps=["Enable TLS"],
            impact_estimate=ImpactEstimate(),
            implementation_effort="low",
        )
        assert rec.before_state == ""
        assert rec.after_state == ""

    def test_implementation_steps_required(self):
        """Test that at least one implementation step is required."""
        with pytest.raises(ValidationError):
            Recommendation(
                id="test",
                type="test",
                priority="p3",
                title="Test",
                description="Test",
                rationale="Test",
                implementation_steps=[],  # Empty
                impact_estimate=ImpactEstimate(),
                implementation_effort="low",
            )

    def test_recommendation_with_related_findings(self):
        """Test recommendation with related findings."""
        rec = Recommendation(
            id="rec-001",
            type="optimization",
            priority="p2",
            title="Fix",
            description="Fix issues",
            rationale="Related to findings",
            implementation_steps=["Step 1"],
            before_state="Broken",
            after_state="Fixed",
            impact_estimate=ImpactEstimate(),
            implementation_effort="medium",
            related_findings=["finding-001", "finding-002"],
        )

        assert len(rec.related_findings) == 2
        assert "finding-001" in rec.related_findings

    def test_recommendation_with_documentation_links(self):
        """Test recommendation with documentation links."""
        rec = Recommendation(
            id="rec-001",
            type="test",
            priority="p3",
            title="Test",
            description="Test",
            rationale="Test",
            implementation_steps=["Step"],
            impact_estimate=ImpactEstimate(),
            implementation_effort="low",
            documentation_links=[
                "https://docs.cribl.io/stream/test",
                "https://community.cribl.io/topic/123",
            ],
        )

        assert len(rec.documentation_links) == 2
