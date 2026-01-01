"""
Quick test to verify product tagging and sorting enhancements work.
"""

from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.analyzers.cost import CostAnalyzer


def test_finding_product_tags():
    """Test Finding model with product tags."""
    # Default: all products
    finding1 = Finding(
        id="test-001",
        category="health",
        severity="high",
        title="Test Finding",
        description="Test description",
        confidence_level="high",
        estimated_impact="Test impact",
        remediation_steps=["Fix the issue"]
    )
    assert finding1.product_tags == ["stream", "edge", "lake", "search"]
    print("✓ Finding defaults to all products")

    # Stream-only finding
    finding2 = Finding(
        id="test-002",
        category="cost",
        severity="critical",
        title="License exhaustion",
        description="License running out",
        confidence_level="high",
        estimated_impact="Service disruption",
        remediation_steps=["Upgrade license", "Reduce consumption"],
        product_tags=["stream"]
    )
    assert finding2.product_tags == ["stream"]
    print("✓ Finding can be tagged for specific product")


def test_recommendation_product_tags():
    """Test Recommendation model with product tags."""
    # Default: all products
    rec1 = Recommendation(
        id="rec-001",
        type="optimization",
        priority="p1",
        title="Optimize pipeline",
        description="Test optimization",
        rationale="Improve performance",
        implementation_steps=["Step 1"],
        before_state="Current state",
        after_state="Improved state",
        impact_estimate=ImpactEstimate(cost_savings_annual=1000),
        implementation_effort="low"
    )
    assert rec1.product_tags == ["stream", "edge", "lake", "search"]
    print("✓ Recommendation defaults to all products")

    # Edge-only recommendation
    rec2 = Recommendation(
        id="rec-002",
        type="resource",
        priority="p2",
        title="Reduce memory",
        description="Lower memory footprint",
        rationale="Edge devices constrained",
        implementation_steps=["Reduce buffer size"],
        impact_estimate=ImpactEstimate(performance_improvement="30% memory reduction"),
        implementation_effort="medium",
        product_tags=["edge"]
    )
    assert rec2.product_tags == ["edge"]
    print("✓ Recommendation can be tagged for specific product")


def test_analyzer_sorting():
    """Test AnalyzerResult sorting methods."""
    result = AnalyzerResult(objective="test")

    # Add findings in random order
    result.add_finding(Finding(
        id="f1", category="test", severity="low", title="Low",
        description="Low severity", confidence_level="high"
    ))
    result.add_finding(Finding(
        id="f2", category="test", severity="critical", title="Critical",
        description="Critical issue", confidence_level="high", estimated_impact="High",
        remediation_steps=["Fix critical issue"]
    ))
    result.add_finding(Finding(
        id="f3", category="test", severity="medium", title="Medium",
        description="Medium issue", confidence_level="high",
        remediation_steps=["Fix medium issue"]
    ))
    result.add_finding(Finding(
        id="f4", category="test", severity="high", title="High",
        description="High severity", confidence_level="high", estimated_impact="Medium",
        remediation_steps=["Fix high issue"]
    ))

    # Sort by severity
    result.sort_findings_by_severity()
    assert result.findings[0].severity == "critical"
    assert result.findings[1].severity == "high"
    assert result.findings[2].severity == "medium"
    assert result.findings[3].severity == "low"
    print("✓ Findings sorted by severity (critical > high > medium > low)")

    # Add recommendations in random order
    result.add_recommendation(Recommendation(
        id="r1", type="test", priority="p3", title="P3", description="Low priority",
        rationale="Nice to have", implementation_steps=["Do it"],
        impact_estimate=ImpactEstimate(), implementation_effort="low"
    ))
    result.add_recommendation(Recommendation(
        id="r2", type="test", priority="p0", title="P0", description="Critical",
        rationale="Must do", implementation_steps=["Do it now"],
        impact_estimate=ImpactEstimate(cost_savings_annual=10000), implementation_effort="high"
    ))
    result.add_recommendation(Recommendation(
        id="r3", type="test", priority="p1", title="P1", description="High priority",
        rationale="Should do", implementation_steps=["Do it soon"],
        impact_estimate=ImpactEstimate(cost_savings_annual=5000), implementation_effort="medium"
    ))

    # Sort by priority
    result.sort_recommendations_by_priority()
    assert result.recommendations[0].priority == "p0"
    assert result.recommendations[1].priority == "p1"
    assert result.recommendations[2].priority == "p3"
    print("✓ Recommendations sorted by priority (p0 > p1 > p3)")


def test_product_filtering():
    """Test filtering by product."""
    result = AnalyzerResult(objective="test")

    # Add findings for different products
    result.add_finding(Finding(
        id="f-stream", category="test", severity="high", title="Stream only",
        description="Stream issue", confidence_level="high", estimated_impact="Impact",
        remediation_steps=["Fix stream issue"],
        product_tags=["stream"]
    ))
    result.add_finding(Finding(
        id="f-edge", category="test", severity="medium", title="Edge only",
        description="Edge issue", confidence_level="high",
        remediation_steps=["Fix edge issue"],
        product_tags=["edge"]
    ))
    result.add_finding(Finding(
        id="f-both", category="test", severity="low", title="Both",
        description="Both products", confidence_level="high",
        product_tags=["stream", "edge"]
    ))

    # Filter for stream
    stream_result = result.filter_by_product("stream")
    assert len(stream_result.findings) == 2  # f-stream and f-both
    assert stream_result.findings[0].id in ["f-stream", "f-both"]
    assert stream_result.findings[1].id in ["f-stream", "f-both"]
    print("✓ Filtered findings by product tag (stream)")

    # Filter for edge
    edge_result = result.filter_by_product("edge")
    assert len(edge_result.findings) == 2  # f-edge and f-both
    print("✓ Filtered findings by product tag (edge)")

    # Filter for lake (none should match)
    lake_result = result.filter_by_product("lake")
    assert len(lake_result.findings) == 0
    print("✓ Filtered findings for product with no matches")


def test_cost_analyzer_supported_products():
    """Test CostAnalyzer reports correct supported products."""
    analyzer = CostAnalyzer()
    assert analyzer.supported_products == ["stream"]
    print("✓ CostAnalyzer supports only Stream (as expected)")


if __name__ == "__main__":
    print("Testing Product Tagging and Sorting Enhancements\n")
    print("=" * 60)

    test_finding_product_tags()
    test_recommendation_product_tags()
    test_analyzer_sorting()
    test_product_filtering()
    test_cost_analyzer_supported_products()

    print("=" * 60)
    print("\n✅ All tests passed!")
