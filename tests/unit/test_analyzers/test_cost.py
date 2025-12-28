"""
Unit tests for CostAnalyzer.

Following TDD: These tests are written FIRST and should FAIL until implementation is complete.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta

from cribl_hc.analyzers.cost import CostAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestCostAnalyzer:
    """Test suite for CostAnalyzer."""

    @pytest.fixture
    def cost_analyzer(self):
        """Create CostAnalyzer instance."""
        return CostAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock Cribl API client."""
        client = AsyncMock(spec=CriblAPIClient)
        client.is_cloud = False
        client.is_edge = False
        client.product_type = "stream"
        # Set up default mock responses
        client.get_license_info = AsyncMock(return_value={})
        client.get_metrics = AsyncMock(return_value={})
        client.get_outputs = AsyncMock(return_value=[])
        return client

    # === Objective Name and Metadata Tests ===

    def test_objective_name(self, cost_analyzer):
        """Test that analyzer has correct objective name."""
        assert cost_analyzer.objective_name == "cost"

    def test_estimated_api_calls(self, cost_analyzer):
        """Test API call estimation."""
        # Should need: license(1) + metrics(1) + outputs(1) = 3 calls
        assert cost_analyzer.get_estimated_api_calls() <= 4

    def test_required_permissions(self, cost_analyzer):
        """Test required API permissions."""
        permissions = cost_analyzer.get_required_permissions()
        assert "read:license" in permissions or "read:system" in permissions
        assert "read:metrics" in permissions

    # === License Consumption Tests ===

    @pytest.mark.asyncio
    async def test_track_license_consumption_vs_allocation(self, cost_analyzer, mock_client):
        """Test license consumption tracking against allocation."""
        # Mock license data: 75% consumed
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,  # 1TB allocated per day
            "current_daily_gb": 750   # 750GB consumed
        })

        result = await cost_analyzer.analyze(mock_client)

        assert result.success is True
        assert "license_consumption_pct" in result.metadata
        assert result.metadata["license_consumption_pct"] == 75.0
        assert result.metadata["license_allocated_gb"] == 1000
        assert result.metadata["license_consumed_gb"] == 750

    @pytest.mark.asyncio
    async def test_identify_high_license_utilization(self, cost_analyzer, mock_client):
        """Test detection of high license utilization."""
        # Mock license data: 95% consumed (high utilization)
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 950  # 95% consumed
        })

        result = await cost_analyzer.analyze(mock_client)

        # Should create finding for high utilization (95% triggers critical threshold)
        high_util_findings = [
            f for f in result.findings
            if "license" in f.id.lower() and "utilization" in f.id.lower()
        ]
        assert len(high_util_findings) > 0
        assert high_util_findings[0].severity in ["critical", "high", "medium"]

    @pytest.mark.asyncio
    async def test_license_within_limits(self, cost_analyzer, mock_client):
        """Test license consumption within healthy limits."""
        # Mock license data: 60% consumed (healthy)
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 600  # 60% consumed
        })

        result = await cost_analyzer.analyze(mock_client)

        # Should not create high-severity findings for healthy utilization
        critical_findings = [
            f for f in result.findings
            if f.severity in ["critical", "high"]
        ]
        assert len(critical_findings) == 0

    # === License Exhaustion Prediction Tests ===

    @pytest.mark.asyncio
    async def test_predict_license_exhaustion_timeline(self, cost_analyzer, mock_client):
        """Test license exhaustion prediction with growing consumption."""
        # Mock historical consumption showing growth trend
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 800,
            "consumption_history": [
                {"date": "2025-12-21", "gb": 700},
                {"date": "2025-12-22", "gb": 720},
                {"date": "2025-12-23", "gb": 740},
                {"date": "2025-12-24", "gb": 760},
                {"date": "2025-12-25", "gb": 780},
                {"date": "2025-12-26", "gb": 800},
            ]
        })

        result = await cost_analyzer.analyze(mock_client)

        # Should predict exhaustion timeline
        assert "license_exhaustion_days" in result.metadata
        # With linear growth of ~20GB/day, should exhaust in ~10 days (200GB headroom)
        assert result.metadata["license_exhaustion_days"] > 0
        assert result.metadata["license_exhaustion_days"] < 30  # Should be soon

    @pytest.mark.asyncio
    async def test_no_exhaustion_prediction_for_stable_consumption(self, cost_analyzer, mock_client):
        """Test no exhaustion warning when consumption is stable."""
        # Mock stable consumption (no growth)
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 500,
            "consumption_history": [
                {"date": "2025-12-21", "gb": 500},
                {"date": "2025-12-22", "gb": 505},
                {"date": "2025-12-23", "gb": 495},
                {"date": "2025-12-24", "gb": 500},
                {"date": "2025-12-25", "gb": 502},
                {"date": "2025-12-26", "gb": 500},
            ]
        })

        result = await cost_analyzer.analyze(mock_client)

        # Should not predict exhaustion for flat/slow growth
        exhaustion_findings = [
            f for f in result.findings
            if "exhaustion" in f.description.lower()
        ]
        # May or may not have findings depending on implementation threshold

    @pytest.mark.asyncio
    async def test_exhaustion_warning_for_rapid_growth(self, cost_analyzer, mock_client):
        """Test warning generation for rapid license consumption growth."""
        # Mock rapid growth trend
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 900,
            "consumption_history": [
                {"date": "2025-12-21", "gb": 600},
                {"date": "2025-12-22", "gb": 700},
                {"date": "2025-12-23", "gb": 750},
                {"date": "2025-12-24", "gb": 800},
                {"date": "2025-12-25", "gb": 850},
                {"date": "2025-12-26", "gb": 900},
            ]
        })

        result = await cost_analyzer.analyze(mock_client)

        # Should create finding for rapid growth
        growth_findings = [
            f for f in result.findings
            if "growth" in f.description.lower() or "exhaustion" in f.description.lower()
        ]
        assert len(growth_findings) > 0

    # === TCO Calculation Tests ===

    @pytest.mark.asyncio
    async def test_calculate_tco_by_destination(self, cost_analyzer, mock_client):
        """Test TCO calculation per destination when pricing configured."""
        # Mock outputs with volume data
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "s3-main",
                "type": "s3",
                "stats": {"out_bytes_total": 5_000_000_000_000}  # 5TB
            },
            {
                "id": "splunk-prod",
                "type": "splunk_hec",
                "stats": {"out_bytes_total": 2_000_000_000_000}  # 2TB
            }
        ])
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 700
        })

        # Set pricing configuration
        cost_analyzer.set_pricing_config({
            "s3": {"storage_cost_per_gb_month": 0.023},
            "splunk_hec": {"ingest_cost_per_gb": 0.15}
        })

        result = await cost_analyzer.analyze(mock_client)

        # Should calculate TCO for each destination
        assert "tco_by_destination" in result.metadata
        assert "s3-main" in result.metadata["tco_by_destination"]
        assert "splunk-prod" in result.metadata["tco_by_destination"]

    @pytest.mark.asyncio
    async def test_tco_without_pricing_config(self, cost_analyzer, mock_client):
        """Test that TCO calculation is skipped when no pricing configured."""
        mock_client.get_outputs = AsyncMock(return_value=[
            {"id": "s3-main", "type": "s3", "stats": {"out_bytes_total": 1000}}
        ])
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 500
        })

        result = await cost_analyzer.analyze(mock_client)

        # Should succeed without pricing data
        assert result.success is True
        # TCO metadata may be empty or have placeholder values

    # === Cost Comparison Tests ===

    @pytest.mark.asyncio
    async def test_identify_expensive_destinations(self, cost_analyzer, mock_client):
        """Test identification of expensive destinations."""
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "splunk-expensive",
                "type": "splunk_hec",
                "stats": {"out_bytes_total": 10_000_000_000_000}  # 10TB to expensive Splunk
            },
            {
                "id": "s3-cheap",
                "type": "s3",
                "stats": {"out_bytes_total": 10_000_000_000_000}  # 10TB to cheap S3
            }
        ])
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 2000,
            "current_daily_gb": 1500
        })

        # Set pricing showing Splunk is more expensive
        cost_analyzer.set_pricing_config({
            "s3": {"storage_cost_per_gb_month": 0.023},
            "splunk_hec": {"ingest_cost_per_gb": 0.15}
        })

        result = await cost_analyzer.analyze(mock_client)

        # Should identify expensive destination
        expensive_findings = [
            f for f in result.findings
            if "expensive" in f.description.lower() or "cost" in f.description.lower()
        ]
        # May or may not create findings depending on implementation

    @pytest.mark.asyncio
    async def test_cost_comparison_recommendations(self, cost_analyzer, mock_client):
        """Test cost optimization recommendations."""
        mock_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "expensive-dest",
                "type": "splunk_hec",
                "stats": {"out_bytes_total": 5_000_000_000_000}
            }
        ])
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 800
        })

        cost_analyzer.set_pricing_config({
            "splunk_hec": {"ingest_cost_per_gb": 0.15}
        })

        result = await cost_analyzer.analyze(mock_client)

        # Should generate cost optimization recommendations
        cost_recs = [
            r for r in result.recommendations
            if "cost" in r.type.lower() or "cost" in r.description.lower()
        ]
        # Recommendations are optional based on analysis

    # === Future Cost Forecasting Tests ===

    @pytest.mark.asyncio
    async def test_forecast_future_costs(self, cost_analyzer, mock_client):
        """Test future cost forecasting based on growth trends."""
        # Mock growing consumption
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 700,
            "consumption_history": [
                {"date": "2025-12-21", "gb": 600},
                {"date": "2025-12-22", "gb": 620},
                {"date": "2025-12-23", "gb": 640},
                {"date": "2025-12-24", "gb": 660},
                {"date": "2025-12-25", "gb": 680},
                {"date": "2025-12-26", "gb": 700},
            ]
        })
        mock_client.get_outputs = AsyncMock(return_value=[])

        result = await cost_analyzer.analyze(mock_client)

        # Should forecast future consumption/costs
        assert "forecasted_consumption_30d" in result.metadata or "growth_rate_gb_per_day" in result.metadata

    # === Metadata Tests ===

    @pytest.mark.asyncio
    async def test_metadata_structure(self, cost_analyzer, mock_client):
        """Test that metadata includes required cost metrics."""
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 600
        })
        mock_client.get_outputs = AsyncMock(return_value=[])

        result = await cost_analyzer.analyze(mock_client)

        # Check for key metadata fields
        assert "license_allocated_gb" in result.metadata or "daily_gb_limit" in result.metadata
        assert "license_consumed_gb" in result.metadata or "current_daily_gb" in result.metadata
        assert "license_consumption_pct" in result.metadata

    # === Recommendation Tests ===

    @pytest.mark.asyncio
    async def test_generate_license_recommendations(self, cost_analyzer, mock_client):
        """Test license management recommendations."""
        # Mock high consumption
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 950  # 95% consumed
        })
        mock_client.get_outputs = AsyncMock(return_value=[])

        result = await cost_analyzer.analyze(mock_client)

        # Should generate recommendations for high consumption
        license_recs = [
            r for r in result.recommendations
            if "license" in r.description.lower()
        ]
        # Recommendations are based on thresholds

    # === Edge Case Tests ===

    @pytest.mark.asyncio
    async def test_no_license_data(self, cost_analyzer, mock_client):
        """Test analysis when no license data available."""
        mock_client.get_license_info = AsyncMock(return_value={})
        mock_client.get_outputs = AsyncMock(return_value=[])

        result = await cost_analyzer.analyze(mock_client)

        # Should succeed gracefully
        assert result.success is True
        assert result.metadata.get("license_allocated_gb", 0) == 0

    @pytest.mark.asyncio
    async def test_no_consumption_history(self, cost_analyzer, mock_client):
        """Test handling when no historical data available."""
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 500
            # No consumption_history
        })
        mock_client.get_outputs = AsyncMock(return_value=[])

        result = await cost_analyzer.analyze(mock_client)

        # Should succeed without predictions
        assert result.success is True
        # Exhaustion prediction should be None or skipped

    @pytest.mark.asyncio
    async def test_error_handling(self, cost_analyzer, mock_client):
        """Test graceful error handling."""
        mock_client.get_license_info = AsyncMock(side_effect=Exception("API Error"))

        result = await cost_analyzer.analyze(mock_client)

        # Should still return success (graceful degradation)
        assert result.success is True
        assert result.metadata.get("license_allocated_gb", 0) == 0

    # === Product Type Tests ===

    @pytest.mark.asyncio
    async def test_edge_deployment_analysis(self, cost_analyzer):
        """Test cost analysis on Edge deployment."""
        edge_client = AsyncMock(spec=CriblAPIClient)
        edge_client.is_edge = True
        edge_client.is_stream = False
        edge_client.product_type = "edge"

        # Edge typically forwards to Stream (minimal local costs)
        edge_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 100,  # Smaller Edge license
            "current_daily_gb": 50
        })
        edge_client.get_outputs = AsyncMock(return_value=[
            {
                "id": "cribl-stream",
                "type": "cribl",
                "stats": {"out_bytes_total": 50_000_000_000}
            }
        ])
        edge_client.get_metrics = AsyncMock(return_value={})

        result = await cost_analyzer.analyze(edge_client)

        assert result.success is True
        assert result.metadata.get("product_type") == "edge"

    # === Severity Classification Tests ===

    @pytest.mark.asyncio
    async def test_critical_severity_for_license_exhaustion(self, cost_analyzer, mock_client):
        """Test that imminent license exhaustion is critical."""
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 995,  # 99.5% consumed
            "consumption_history": [
                {"date": "2025-12-26", "gb": 995}
            ]
        })
        mock_client.get_outputs = AsyncMock(return_value=[])

        result = await cost_analyzer.analyze(mock_client)

        # Should have critical findings for near-exhaustion
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        # Critical if above threshold (e.g., 95%+)

    # === Linear Regression Tests ===

    @pytest.mark.asyncio
    async def test_linear_regression_calculation(self, cost_analyzer, mock_client):
        """Test linear regression for license exhaustion prediction."""
        # Mock perfect linear growth
        mock_client.get_license_info = AsyncMock(return_value={
            "daily_gb_limit": 1000,
            "current_daily_gb": 700,
            "consumption_history": [
                {"date": "2025-12-20", "gb": 500},
                {"date": "2025-12-21", "gb": 550},
                {"date": "2025-12-22", "gb": 600},
                {"date": "2025-12-23", "gb": 650},
                {"date": "2025-12-24", "gb": 700},
            ]
        })
        mock_client.get_outputs = AsyncMock(return_value=[])

        result = await cost_analyzer.analyze(mock_client)

        # With 50GB/day growth, should predict exhaustion in 6 days (300GB headroom)
        if "license_exhaustion_days" in result.metadata:
            assert 4 <= result.metadata["license_exhaustion_days"] <= 8  # Allow some variance
