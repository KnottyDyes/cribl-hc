"""
Unit tests for LicenseOptimizationAnalyzer.
"""

from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.license_optimization import (
    DropRuleAnalysis,
    LicenseMetrics,
    LicenseOptimizationAnalyzer,
    PipelineMetrics,
)
from cribl_hc.core.api_client import CriblAPIClient


class TestLicenseOptimizationAnalyzer:
    """Test LicenseOptimizationAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return LicenseOptimizationAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = AsyncMock(spec=CriblAPIClient)
        return client

    def test_objective_name(self, analyzer):
        """Test analyzer objective name."""
        assert analyzer.objective_name == "license-optimization"

    def test_supported_products(self, analyzer):
        """Test supported products."""
        assert analyzer.supported_products == ["stream", "edge"]

    def test_required_permissions(self, analyzer):
        """Test required permissions."""
        expected = ["read:license", "read:metrics", "read:pipelines", "read:routes", "read:system"]
        assert analyzer.get_required_permissions() == expected

    @pytest.mark.asyncio
    async def test_analyze_no_license_data(self, analyzer, mock_client):
        """Test analysis with no license data."""
        # Mock failure to get license data
        mock_client.get.side_effect = Exception("License endpoint not available")

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        assert "No License Data Available" in result.findings[0].title

    @pytest.mark.asyncio
    async def test_analyze_license_exhaustion_risk(self, analyzer, mock_client):
        """Test license exhaustion risk analysis."""
        license_data = {
            "license": {
                "totalEvents": 1000000,
                "processedEvents": 950000,
                "droppedEvents": 50000,
                "usedPercent": 95.0,
                "limit": 1000000,
            }
        }

        mock_client.get.side_effect = [
            license_data,  # license status
            {"items": []},  # license history
        ]
        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        assert len(critical_findings) >= 1
        # Should find license exhaustion risk

    @pytest.mark.asyncio
    async def test_analyze_drop_rule_effectiveness(self, analyzer, mock_client):
        """Test drop rule effectiveness analysis."""
        pipelines_data = [
            {
                "id": "pipeline1",
                "name": "Data Pipeline",
                "config": {
                    "steps": [{"type": "filter", "filter": "field == 'old'", "action": "drop"}]
                },
            }
        ]

        mock_client.get.side_effect = [
            {"license": {"usedPercent": 50.0}},  # license
            {"items": []},  # history
        ]
        mock_client.get_pipelines.return_value = pipelines_data
        mock_client.get_routes.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should analyze drop rule effectiveness

    @pytest.mark.asyncio
    async def test_analyze_processing_efficiency(self, analyzer, mock_client):
        """Test processing efficiency analysis."""
        pipelines_data = [
            {
                "id": "inefficient_pipeline",
                "name": "Inefficient Pipeline",
                "metrics": {
                    "inputEvents": 10000,
                    "outputEvents": 8000,
                    "processingTimeMs": 50000,  # 50 seconds for 10k events
                    "cpuUsagePercent": 90.0,
                    "memoryUsageMb": 1500.0,
                },
            }
        ]

        mock_client.get.side_effect = [
            {"license": {"usedPercent": 50.0}},  # license
            {"items": []},  # history
        ]
        mock_client.get_pipelines.return_value = pipelines_data
        mock_client.get_routes.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        [f for f in result.findings if f.severity == "high"]
        # Should find inefficient processing

    @pytest.mark.asyncio
    async def test_analyze_cost_optimization_opportunities(self, analyzer, mock_client):
        """Test cost optimization opportunities analysis."""
        license_data = {
            "license": {
                "usedPercent": 15.0,  # Underutilized
                "totalEvents": 100000,
                "processedEvents": 85000,
                "droppedEvents": 15000,
            }
        }

        pipelines_data = [
            {"id": "p1", "name": "Pipeline 1"},
            {"id": "p2", "name": "Pipeline 2"},
            {"id": "p3", "name": "Pipeline 3"},
            {"id": "p4", "name": "Pipeline 4"},
            {"id": "p5", "name": "Pipeline 5"},
            {"id": "p6", "name": "Pipeline 6"},
            {"id": "p7", "name": "Pipeline 7"},
            {"id": "p8", "name": "Pipeline 8"},
        ]  # 8 pipelines - high complexity

        mock_client.get.side_effect = [
            license_data,  # license
            {"items": []},  # history
        ]
        mock_client.get_pipelines.return_value = pipelines_data
        mock_client.get_routes.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # Should find underutilized license and high pipeline complexity

    @pytest.mark.asyncio
    async def test_analyze_license_usage_spike(self, analyzer, mock_client):
        """Test license usage spike detection."""
        # Create history with increasing usage
        history_data = {
            "items": [
                {"date": "2024-01-01", "usedPercent": 40.0},
                {"date": "2024-01-02", "usedPercent": 42.0},
                {"date": "2024-01-03", "usedPercent": 45.0},
                {"date": "2024-01-04", "usedPercent": 50.0},
                {"date": "2024-01-05", "usedPercent": 48.0},
                {"date": "2024-01-06", "usedPercent": 52.0},
                {"date": "2024-01-07", "usedPercent": 75.0},  # Spike
            ]
        }

        current_license = {
            "license": {
                "usedPercent": 75.0,
                "totalEvents": 100000,
                "processedEvents": 75000,
                "droppedEvents": 25000,
            }
        }

        mock_client.get.side_effect = [
            current_license,  # license
            history_data,  # history
        ]
        mock_client.get_pipelines.return_value = []
        mock_client.get_routes.return_value = []

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        [f for f in result.findings if f.severity == "medium"]
        # Should detect usage spike

    def test_license_metrics_properties(self):
        """Test LicenseMetrics property methods."""
        metrics = LicenseMetrics(
            total_events=1000,
            processed_events=800,
            dropped_events=200,
            license_used_percent=80.0,
            license_limit=1000,
        )

        assert metrics.events_dropped_percent == 20.0
        assert metrics.license_remaining_percent == 20.0
        assert metrics.is_near_exhaustion is False

        high_usage = LicenseMetrics(
            total_events=1000,
            processed_events=950,
            dropped_events=50,
            license_used_percent=95.0,
            license_limit=1000,
        )

        assert high_usage.is_near_exhaustion is True

    def test_drop_rule_analysis(self):
        """Test DropRuleAnalysis functionality."""
        analysis = DropRuleAnalysis(
            pipeline_id="test_pipeline",
            pipeline_name="Test Pipeline",
            drop_conditions=["field == 'old'", "status == 'deprecated'"],
            estimated_dropped_events=500,
            effectiveness_score=25.0,
        )

        assert analysis.is_ineffective is True

        effective_analysis = DropRuleAnalysis(
            pipeline_id="good_pipeline",
            pipeline_name="Good Pipeline",
            drop_conditions=["field == 'old'"],
            estimated_dropped_events=800,
            effectiveness_score=80.0,
        )

        assert effective_analysis.is_ineffective is False

    def test_pipeline_metrics_properties(self):
        """Test PipelineMetrics property methods."""
        metrics = PipelineMetrics(
            id="test_pipeline",
            name="Test Pipeline",
            input_events=1000,
            output_events=800,
            processing_time_ms=5000.0,  # 5 seconds
            cpu_usage_percent=60.0,
            memory_usage_mb=500.0,
        )

        assert metrics.events_processed == 1000
        assert 190 <= metrics.throughput_eps <= 210  # ~200 events/second
        assert metrics.efficiency_score < 100  # Some efficiency cost

    def test_drop_rule_estimation(self, analyzer):
        """Test drop rule effectiveness estimation."""
        # Simple filter should be effective
        score1 = analyzer._estimate_drop_effectiveness("field == 'value'")
        assert score1 > 20

        # Complex filter should be more effective
        score2 = analyzer._estimate_drop_effectiveness("field == 'value' AND status == 'old'")
        assert score2 > score1

        # Broad filter should be less effective
        score3 = analyzer._estimate_drop_effectiveness("*")
        assert score3 < 10

    def test_license_health_score_calculation(self, analyzer):
        """Test license health score calculation."""
        # Good health scenario
        current = LicenseMetrics(
            total_events=1000, processed_events=700, dropped_events=300, license_used_percent=70.0
        )
        history = []

        score = analyzer._calculate_license_health_score(current, history)
        assert score > 80  # Good score

        # Poor health scenario
        poor_current = LicenseMetrics(
            total_events=1000, processed_events=950, dropped_events=50, license_used_percent=95.0
        )

        poor_score = analyzer._calculate_license_health_score(poor_current, history)
        assert poor_score < score  # Worse score

    def test_exhaustion_prediction(self, analyzer):
        """Test license exhaustion prediction."""
        current = LicenseMetrics(
            total_events=1000,
            processed_events=900,
            dropped_events=100,
            license_used_percent=90.0,
            license_limit=1000,
        )

        history = [
            LicenseMetrics(license_used_percent=80.0),
            LicenseMetrics(license_used_percent=85.0),
            LicenseMetrics(license_used_percent=87.0),
        ]

        days = analyzer._predict_exhaustion_days(current, history)
        assert days > 0
        assert days < 30  # Should predict exhaustion soon
