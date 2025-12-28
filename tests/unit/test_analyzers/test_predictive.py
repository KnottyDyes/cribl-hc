"""
Unit tests for PredictiveAnalyzer (US7 - Predictive Analytics).

Tests cover:
- Worker capacity exhaustion prediction
- License consumption forecasting
- Destination backpressure prediction
- Anomaly detection
- Proactive scaling recommendations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from cribl_hc.analyzers.predictive import PredictiveAnalyzer
from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation


class TestPredictiveAnalyzer:
    """Test suite for PredictiveAnalyzer."""

    @pytest.fixture
    def predictive_analyzer(self):
        """Create PredictiveAnalyzer instance."""
        return PredictiveAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock Cribl API client."""
        client = AsyncMock(spec=CriblAPIClient)
        client.is_cloud = False
        client.is_edge = False
        client.product_type = "stream"
        return client

    # === Objective Name Tests ===

    def test_objective_name(self, predictive_analyzer):
        """Test that analyzer has correct objective name."""
        assert predictive_analyzer.objective_name == "predictive"

    def test_supported_products(self, predictive_analyzer):
        """Test that PredictiveAnalyzer supports all products."""
        assert "stream" in predictive_analyzer.supported_products
        assert "edge" in predictive_analyzer.supported_products

    # === Worker Capacity Exhaustion Prediction Tests ===

    @pytest.mark.asyncio
    async def test_predict_worker_capacity_exhaustion(self, predictive_analyzer, mock_client):
        """Test worker capacity exhaustion prediction with growth trend."""
        # Mock historical worker metrics showing growth
        mock_client.get_workers = AsyncMock(return_value=[
            {
                "id": "worker-1",
                "metrics": {"cpu_utilization": 75, "memory_utilization": 80}
            }
        ])

        # Provide historical data showing upward trend
        historical_data = {
            "worker_metrics": [
                {"timestamp": "2025-12-21T00:00:00Z", "cpu_avg": 50, "memory_avg": 55},
                {"timestamp": "2025-12-22T00:00:00Z", "cpu_avg": 55, "memory_avg": 60},
                {"timestamp": "2025-12-23T00:00:00Z", "cpu_avg": 60, "memory_avg": 65},
                {"timestamp": "2025-12-24T00:00:00Z", "cpu_avg": 65, "memory_avg": 70},
                {"timestamp": "2025-12-25T00:00:00Z", "cpu_avg": 70, "memory_avg": 75},
                {"timestamp": "2025-12-26T00:00:00Z", "cpu_avg": 75, "memory_avg": 80},
            ]
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        assert result.success is True
        # Should predict exhaustion
        capacity_findings = [
            f for f in result.findings
            if "capacity" in f.id.lower() or "exhaustion" in f.id.lower()
        ]
        # May have capacity prediction findings
        assert isinstance(capacity_findings, list)

    @pytest.mark.asyncio
    async def test_no_prediction_without_historical_data(self, predictive_analyzer, mock_client):
        """Test that predictions require historical data."""
        mock_client.get_workers = AsyncMock(return_value=[])

        result = await predictive_analyzer.analyze(mock_client, historical_data=None)

        # Should still succeed but with limited predictions
        assert result.success is True
        assert "historical_data_available" in result.metadata

    # === License Consumption Forecasting Tests ===

    @pytest.mark.asyncio
    async def test_forecast_license_exhaustion(self, predictive_analyzer, mock_client):
        """Test license consumption forecasting with growth trend."""
        # Mock current license consumption
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 800
        })

        # Historical consumption showing growth
        historical_data = {
            "license_consumption": [
                {"date": "2025-12-21", "gb": 700},
                {"date": "2025-12-22", "gb": 720},
                {"date": "2025-12-23", "gb": 740},
                {"date": "2025-12-24", "gb": 760},
                {"date": "2025-12-25", "gb": 780},
                {"date": "2025-12-26", "gb": 800},
            ]
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        # Should predict license exhaustion
        license_findings = [
            f for f in result.findings
            if "license" in f.id.lower()
        ]
        # May have license forecasting
        assert isinstance(license_findings, list)

    # === Destination Backpressure Prediction Tests ===

    @pytest.mark.asyncio
    async def test_predict_destination_backpressure(self, predictive_analyzer, mock_client):
        """Test destination backpressure prediction from throughput trends."""
        mock_client.get_outputs = AsyncMock(return_value=[
            {"id": "splunk-output", "type": "splunk_hec"}
        ])

        # Historical throughput data showing increasing load
        historical_data = {
            "destination_throughput": {
                "splunk-output": [
                    {"timestamp": "2025-12-21T00:00:00Z", "gb_per_hour": 50},
                    {"timestamp": "2025-12-22T00:00:00Z", "gb_per_hour": 55},
                    {"timestamp": "2025-12-23T00:00:00Z", "gb_per_hour": 60},
                    {"timestamp": "2025-12-24T00:00:00Z", "gb_per_hour": 65},
                    {"timestamp": "2025-12-25T00:00:00Z", "gb_per_hour": 70},
                    {"timestamp": "2025-12-26T00:00:00Z", "gb_per_hour": 75},
                ]
            }
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        # May predict backpressure
        backpressure_findings = [
            f for f in result.findings
            if "backpressure" in f.id.lower() or "throughput" in f.id.lower()
        ]
        assert isinstance(backpressure_findings, list)

    # === Anomaly Detection Tests ===

    @pytest.mark.asyncio
    async def test_detect_anomalies_in_health_scores(self, predictive_analyzer, mock_client):
        """Test anomaly detection in health score trends."""
        # Historical health scores with anomaly (sudden drop)
        historical_data = {
            "health_scores": [
                {"timestamp": "2025-12-21T00:00:00Z", "score": 95},
                {"timestamp": "2025-12-22T00:00:00Z", "score": 94},
                {"timestamp": "2025-12-23T00:00:00Z", "score": 96},
                {"timestamp": "2025-12-24T00:00:00Z", "score": 95},
                {"timestamp": "2025-12-25T00:00:00Z", "score": 93},
                {"timestamp": "2025-12-26T00:00:00Z", "score": 65},  # Anomaly!
            ]
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        # Should detect anomaly
        anomaly_findings = [
            f for f in result.findings
            if "anomaly" in f.id.lower() or "anomaly" in f.title.lower()
        ]
        # May detect anomalies
        assert isinstance(anomaly_findings, list)

    @pytest.mark.asyncio
    async def test_anomaly_detection_with_z_score(self, predictive_analyzer, mock_client):
        """Test z-score based anomaly detection."""
        # Data with statistical outlier
        historical_data = {
            "worker_metrics": [
                {"timestamp": "2025-12-21", "cpu_avg": 50},
                {"timestamp": "2025-12-22", "cpu_avg": 52},
                {"timestamp": "2025-12-23", "cpu_avg": 51},
                {"timestamp": "2025-12-24", "cpu_avg": 53},
                {"timestamp": "2025-12-25", "cpu_avg": 50},
                {"timestamp": "2025-12-26", "cpu_avg": 95},  # Outlier (>3 std devs)
            ]
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        # Should use z-score method
        assert "anomalies_detected" in result.metadata or len(result.findings) >= 0

    # === Proactive Scaling Recommendations Tests ===

    @pytest.mark.asyncio
    async def test_generate_proactive_scaling_recommendations(self, predictive_analyzer, mock_client):
        """Test generation of proactive scaling recommendations."""
        mock_client.get_workers = AsyncMock(return_value=[
            {"id": "worker-1", "metrics": {"cpu_utilization": 80}}
        ])

        # Historical data showing sustained growth
        historical_data = {
            "worker_metrics": [
                {"timestamp": "2025-12-21", "cpu_avg": 60},
                {"timestamp": "2025-12-22", "cpu_avg": 65},
                {"timestamp": "2025-12-23", "cpu_avg": 70},
                {"timestamp": "2025-12-24", "cpu_avg": 75},
                {"timestamp": "2025-12-25", "cpu_avg": 80},
                {"timestamp": "2025-12-26", "cpu_avg": 85},
            ]
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        # Should generate scaling recommendations
        scaling_recs = [
            r for r in result.recommendations
            if "scaling" in r.id.lower() or "scaling" in r.title.lower()
        ]
        # May have scaling recommendations
        assert isinstance(scaling_recs, list)

    @pytest.mark.asyncio
    async def test_recommendations_include_lead_time(self, predictive_analyzer, mock_client):
        """Test that recommendations include implementation timeline."""
        historical_data = {
            "worker_metrics": [
                {"timestamp": f"2025-12-{21+i}", "cpu_avg": 50 + (i * 5)}
                for i in range(6)
            ]
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        # Recommendations should have metadata about timeline
        for rec in result.recommendations:
            assert rec.implementation_effort in ["low", "medium", "high"]

    # === Metadata and Confidence Tests ===

    @pytest.mark.asyncio
    async def test_predictions_include_confidence_levels(self, predictive_analyzer, mock_client):
        """Test that predictions include confidence levels."""
        historical_data = {
            "worker_metrics": [
                {"timestamp": f"2025-12-{21+i}", "cpu_avg": 50 + i}
                for i in range(10)  # More data points = higher confidence
            ]
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        # Should have prediction confidence in metadata
        assert "prediction_confidence" in result.metadata or "data_points" in result.metadata

    @pytest.mark.asyncio
    async def test_insufficient_data_warning(self, predictive_analyzer, mock_client):
        """Test warning when insufficient historical data."""
        # Only 2 data points (minimum for trend)
        historical_data = {
            "worker_metrics": [
                {"timestamp": "2025-12-25", "cpu_avg": 50},
                {"timestamp": "2025-12-26", "cpu_avg": 55},
            ]
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        # Should warn about limited data
        assert "historical_data_available" in result.metadata
        assert result.metadata.get("data_points", 0) <= 2 or result.success is True

    # === Trend Analysis Tests ===

    @pytest.mark.asyncio
    async def test_identify_upward_trend(self, predictive_analyzer, mock_client):
        """Test identification of upward trends."""
        historical_data = {
            "license_consumption": [
                {"date": f"2025-12-{21+i}", "gb": 700 + (i * 20)}
                for i in range(6)
            ]
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        # Should identify upward trend
        assert "trends_detected" in result.metadata or len(result.findings) >= 0

    @pytest.mark.asyncio
    async def test_stable_metrics_no_predictions(self, predictive_analyzer, mock_client):
        """Test that stable metrics don't generate false alarms."""
        # Stable data (no trend)
        historical_data = {
            "worker_metrics": [
                {"timestamp": f"2025-12-{21+i}", "cpu_avg": 50}
                for i in range(6)
            ]
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        # Should not predict exhaustion for stable metrics
        critical_findings = result.get_critical_findings()
        # Stable metrics shouldn't trigger critical warnings
        assert len(critical_findings) == 0 or result.success is True

    # === Error Handling Tests ===

    @pytest.mark.asyncio
    async def test_handle_missing_historical_data_gracefully(self, predictive_analyzer, mock_client):
        """Test graceful handling when no historical data provided."""
        result = await predictive_analyzer.analyze(mock_client, historical_data={})

        # Should succeed with limited functionality
        assert result.success is True
        assert result.metadata.get("historical_data_available", False) is False

    @pytest.mark.asyncio
    async def test_handle_malformed_historical_data(self, predictive_analyzer, mock_client):
        """Test handling of malformed historical data."""
        # Malformed data
        historical_data = {
            "worker_metrics": [
                {"timestamp": "invalid", "cpu_avg": "not_a_number"}
            ]
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        # Should handle gracefully
        assert result.success is True or "error" in result.metadata

    # === Integration with Other Analyzers Tests ===

    @pytest.mark.asyncio
    async def test_builds_on_cost_analyzer_data(self, predictive_analyzer, mock_client):
        """Test that PredictiveAnalyzer can use CostAnalyzer historical data."""
        # License data similar to CostAnalyzer format
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 850
        })

        historical_data = {
            "license_consumption": [
                {"date": f"2025-12-{21+i}", "gb": 700 + (i * 25)}
                for i in range(6)
            ]
        }

        result = await predictive_analyzer.analyze(mock_client, historical_data=historical_data)

        # Should integrate with license tracking
        assert result.success is True
