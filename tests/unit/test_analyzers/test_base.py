"""
Unit tests for base analyzer and registry.
"""

import pytest

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.analyzers import (
    AnalyzerRegistry,
    get_global_registry,
    register_analyzer,
    get_analyzer,
    list_objectives,
)
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate


class TestAnalyzerResult:
    """Test AnalyzerResult class."""

    def test_result_initialization(self):
        """Test creating analyzer result."""
        result = AnalyzerResult(objective="health")

        assert result.objective == "health"
        assert result.findings == []
        assert result.recommendations == []
        assert result.metadata == {}
        assert result.success is True
        assert result.error is None

    def test_result_with_data(self):
        """Test result with findings and recommendations."""
        finding = Finding(
            id="test-finding-1",
            title="Test finding",
            description="Test description",
            severity="high",
            category="health",
            confidence_level="high",
            remediation_steps=["Step 1: Fix the issue"],
            estimated_impact="High impact on system",
        )

        recommendation = Recommendation(
            id="test-rec-1",
            type="optimization",
            title="Test recommendation",
            description="Fix the issue",
            priority="p1",
            rationale="Because it needs fixing",
            implementation_steps=["Step 1: Implement fix"],
            impact_estimate=ImpactEstimate(cost_savings_annual=1000.0),
            implementation_effort="low",
        )

        result = AnalyzerResult(
            objective="health",
            findings=[finding],
            recommendations=[recommendation],
            metadata={"worker_count": 5},
        )

        assert len(result.findings) == 1
        assert len(result.recommendations) == 1
        assert result.metadata["worker_count"] == 5

    def test_add_finding(self):
        """Test adding findings to result."""
        result = AnalyzerResult(objective="health")

        finding = Finding(
            id="test-finding-2",
            title="Test finding",
            description="Test description",
            severity="high",
            category="health",
            confidence_level="high",
            remediation_steps=["Step 1: Fix the issue"],
            estimated_impact="High impact on system",
        )

        result.add_finding(finding)

        assert len(result.findings) == 1
        assert result.findings[0] == finding

    def test_add_recommendation(self):
        """Test adding recommendations to result."""
        result = AnalyzerResult(objective="health")

        recommendation = Recommendation(
            id="test-rec-2",
            type="optimization",
            title="Test recommendation",
            description="Fix the issue",
            priority="p1",
            rationale="Because it needs fixing",
            implementation_steps=["Step 1: Implement fix"],
            impact_estimate=ImpactEstimate(cost_savings_annual=1000.0),
            implementation_effort="low",
        )

        result.add_recommendation(recommendation)

        assert len(result.recommendations) == 1
        assert result.recommendations[0] == recommendation

    def test_get_critical_findings(self):
        """Test filtering critical findings."""
        result = AnalyzerResult(objective="health")

        result.add_finding(
            Finding(
                id="test-critical-1",
                title="Critical issue",
                description="Bad",
                severity="critical",
                category="health",
                confidence_level="high",
                remediation_steps=["Fix critical issue immediately"],
                estimated_impact="System may fail",
            )
        )
        result.add_finding(
            Finding(
                id="test-high-1",
                title="High issue",
                description="Not good",
                severity="high",
                category="health",
                confidence_level="high",
                remediation_steps=["Fix high issue soon"],
                estimated_impact="Performance degradation",
            )
        )
        result.add_finding(
            Finding(
                id="test-medium-1",
                title="Medium issue",
                description="OK",
                severity="medium",
                category="health",
                confidence_level="medium",
                remediation_steps=["Fix medium issue when convenient"],
            )
        )

        critical = result.get_critical_findings()

        assert len(critical) == 1
        assert critical[0].severity == "critical"

    def test_get_high_findings(self):
        """Test filtering high severity findings."""
        result = AnalyzerResult(objective="health")

        result.add_finding(
            Finding(
                id="test-critical-2",
                title="Critical issue",
                description="Bad",
                severity="critical",
                category="health",
                confidence_level="high",
                remediation_steps=["Fix critical issue immediately"],
                estimated_impact="System may fail",
            )
        )
        result.add_finding(
            Finding(
                id="test-high-2",
                title="High issue",
                description="Not good",
                severity="high",
                category="health",
                confidence_level="high",
                remediation_steps=["Fix high issue soon"],
                estimated_impact="Performance degradation",
            )
        )

        high = result.get_high_findings()

        assert len(high) == 1
        assert high[0].severity == "high"

    def test_result_repr(self):
        """Test string representation."""
        result = AnalyzerResult(objective="health")
        result.add_finding(
            Finding(
                id="test-low-1",
                title="Test",
                description="Test",
                severity="low",
                category="health",
                confidence_level="medium",
            )
        )

        repr_str = repr(result)

        assert "health" in repr_str
        assert "findings=1" in repr_str
        assert "success=True" in repr_str


class MockAnalyzer(BaseAnalyzer):
    """Mock analyzer for testing."""

    @property
    def objective_name(self) -> str:
        return "mock"

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = AnalyzerResult(objective=self.objective_name)
        result.add_finding(
            Finding(
                id="mock-finding-1",
                title="Mock finding",
                description="From mock analyzer",
                severity="low",
                category="mock",
                confidence_level="high",
            )
        )
        return result


class AnotherMockAnalyzer(BaseAnalyzer):
    """Another mock analyzer for testing."""

    @property
    def objective_name(self) -> str:
        return "another"

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        return AnalyzerResult(objective=self.objective_name)


class TestBaseAnalyzer:
    """Test BaseAnalyzer abstract class."""

    def test_analyzer_initialization(self):
        """Test initializing an analyzer."""
        analyzer = MockAnalyzer()

        assert analyzer.objective_name == "mock"
        assert analyzer.log is not None

    @pytest.mark.asyncio
    async def test_analyzer_analyze(self):
        """Test running analyzer."""
        analyzer = MockAnalyzer()
        client = None  # Mock analyzer doesn't use client

        result = await analyzer.analyze(client)

        assert result.objective == "mock"
        assert len(result.findings) == 1
        assert result.findings[0].title == "Mock finding"

    def test_get_description(self):
        """Test analyzer description."""
        analyzer = MockAnalyzer()

        description = analyzer.get_description()

        assert "mock" in description.lower()

    def test_supports_partial_results(self):
        """Test partial results support (default True)."""
        analyzer = MockAnalyzer()

        assert analyzer.supports_partial_results() is True

    def test_get_required_permissions(self):
        """Test required permissions (default empty)."""
        analyzer = MockAnalyzer()

        permissions = analyzer.get_required_permissions()

        assert permissions == []

    def test_get_estimated_api_calls(self):
        """Test API call estimation (default 5)."""
        analyzer = MockAnalyzer()

        estimate = analyzer.get_estimated_api_calls()

        assert estimate == 5

    @pytest.mark.asyncio
    async def test_pre_analyze_check(self):
        """Test pre-analyze check (default True)."""
        analyzer = MockAnalyzer()
        client = None

        result = await analyzer.pre_analyze_check(client)

        assert result is True

    @pytest.mark.asyncio
    async def test_post_analyze_cleanup(self):
        """Test post-analyze cleanup (should not raise)."""
        analyzer = MockAnalyzer()

        # Should complete without error
        await analyzer.post_analyze_cleanup()


class TestAnalyzerRegistry:
    """Test AnalyzerRegistry class."""

    def test_registry_initialization(self):
        """Test creating empty registry."""
        registry = AnalyzerRegistry()

        assert len(registry) == 0
        assert registry.list_objectives() == []

    def test_register_analyzer(self):
        """Test registering an analyzer."""
        registry = AnalyzerRegistry()

        registry.register(MockAnalyzer)

        assert len(registry) == 1
        assert "mock" in registry.list_objectives()
        assert registry.has_analyzer("mock")

    def test_register_multiple_analyzers(self):
        """Test registering multiple analyzers."""
        registry = AnalyzerRegistry()

        registry.register(MockAnalyzer)
        registry.register(AnotherMockAnalyzer)

        assert len(registry) == 2
        assert "mock" in registry.list_objectives()
        assert "another" in registry.list_objectives()

    def test_register_duplicate_objective_fails(self):
        """Test that registering duplicate objective raises error."""
        registry = AnalyzerRegistry()

        registry.register(MockAnalyzer)

        with pytest.raises(ValueError) as exc_info:
            registry.register(MockAnalyzer)

        assert "already registered" in str(exc_info.value).lower()

    def test_register_non_analyzer_fails(self):
        """Test that registering non-analyzer class fails."""
        registry = AnalyzerRegistry()

        class NotAnAnalyzer:
            pass

        with pytest.raises(ValueError) as exc_info:
            registry.register(NotAnAnalyzer)

        assert "baseanalyzer" in str(exc_info.value).lower()

    def test_get_analyzer(self):
        """Test getting analyzer instance."""
        registry = AnalyzerRegistry()
        registry.register(MockAnalyzer)

        analyzer = registry.get_analyzer("mock")

        assert analyzer is not None
        assert isinstance(analyzer, MockAnalyzer)
        assert analyzer.objective_name == "mock"

    def test_get_nonexistent_analyzer(self):
        """Test getting analyzer that doesn't exist."""
        registry = AnalyzerRegistry()

        analyzer = registry.get_analyzer("nonexistent")

        assert analyzer is None

    def test_get_analyzer_class(self):
        """Test getting analyzer class."""
        registry = AnalyzerRegistry()
        registry.register(MockAnalyzer)

        analyzer_class = registry.get_analyzer_class("mock")

        assert analyzer_class is MockAnalyzer

    def test_unregister_analyzer(self):
        """Test unregistering analyzer."""
        registry = AnalyzerRegistry()
        registry.register(MockAnalyzer)

        result = registry.unregister("mock")

        assert result is True
        assert len(registry) == 0
        assert not registry.has_analyzer("mock")

    def test_unregister_nonexistent(self):
        """Test unregistering nonexistent analyzer."""
        registry = AnalyzerRegistry()

        result = registry.unregister("nonexistent")

        assert result is False

    def test_list_objectives_sorted(self):
        """Test that objectives are sorted."""
        registry = AnalyzerRegistry()
        registry.register(AnotherMockAnalyzer)  # "another"
        registry.register(MockAnalyzer)  # "mock"

        objectives = registry.list_objectives()

        assert objectives == ["another", "mock"]

    def test_list_analyzers(self):
        """Test listing analyzer classes."""
        registry = AnalyzerRegistry()
        registry.register(MockAnalyzer)
        registry.register(AnotherMockAnalyzer)

        analyzers = registry.list_analyzers()

        assert len(analyzers) == 2
        assert MockAnalyzer in analyzers
        assert AnotherMockAnalyzer in analyzers

    def test_clear_registry(self):
        """Test clearing all analyzers."""
        registry = AnalyzerRegistry()
        registry.register(MockAnalyzer)
        registry.register(AnotherMockAnalyzer)

        registry.clear()

        assert len(registry) == 0
        assert registry.list_objectives() == []

    def test_registry_repr(self):
        """Test string representation."""
        registry = AnalyzerRegistry()
        registry.register(MockAnalyzer)

        repr_str = repr(registry)

        assert "1 analyzer" in repr_str
        assert "mock" in repr_str


class TestGlobalRegistry:
    """Test global registry functions."""

    def test_get_global_registry(self):
        """Test getting global registry instance."""
        registry = get_global_registry()

        assert isinstance(registry, AnalyzerRegistry)

    def test_global_registry_singleton(self):
        """Test that global registry is singleton."""
        registry1 = get_global_registry()
        registry2 = get_global_registry()

        assert registry1 is registry2

    def test_register_to_global_registry(self):
        """Test registering to global registry."""
        # Clear first to ensure clean state
        get_global_registry().clear()

        register_analyzer(MockAnalyzer)

        assert "mock" in list_objectives()

        # Cleanup
        get_global_registry().unregister("mock")

    def test_get_from_global_registry(self):
        """Test getting analyzer from global registry."""
        # Clear first
        get_global_registry().clear()

        register_analyzer(MockAnalyzer)
        analyzer = get_analyzer("mock")

        assert analyzer is not None
        assert isinstance(analyzer, MockAnalyzer)

        # Cleanup
        get_global_registry().unregister("mock")

    def test_list_global_objectives(self):
        """Test listing objectives from global registry."""
        # Clear first
        get_global_registry().clear()

        register_analyzer(MockAnalyzer)
        register_analyzer(AnotherMockAnalyzer)

        objectives = list_objectives()

        assert "mock" in objectives
        assert "another" in objectives

        # Cleanup
        get_global_registry().clear()
