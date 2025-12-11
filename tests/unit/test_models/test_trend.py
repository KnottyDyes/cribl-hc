"""
Unit tests for HistoricalTrend and DataPoint models.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from cribl_hc.models.trend import DataPoint, HistoricalTrend


class TestDataPoint:
    """Test DataPoint model validation."""

    def test_valid_data_point(self):
        """Test creating a valid data point."""
        timestamp = datetime(2025, 12, 10, 14, 0, 0)
        dp = DataPoint(timestamp=timestamp, value=72.0)

        assert dp.timestamp == timestamp
        assert dp.value == 72.0
        assert dp.metadata == {}

    def test_data_point_with_metadata(self):
        """Test data point with metadata."""
        metadata = {"source": "health_check", "version": "1.0"}
        dp = DataPoint(
            timestamp=datetime(2025, 12, 10, 14, 0, 0), value=78.5, metadata=metadata
        )

        assert dp.metadata == metadata
        assert dp.metadata["source"] == "health_check"

    def test_data_point_accepts_any_numeric_value(self):
        """Test that data point accepts any numeric value."""
        DataPoint(timestamp=datetime(2025, 12, 10, 14, 0, 0), value=-10.5)
        DataPoint(timestamp=datetime(2025, 12, 10, 14, 0, 0), value=0.0)
        DataPoint(timestamp=datetime(2025, 12, 10, 14, 0, 0), value=1000.0)


class TestHistoricalTrend:
    """Test HistoricalTrend model validation and behavior."""

    def test_valid_historical_trend(self):
        """Test creating a valid historical trend."""
        data_points = [
            DataPoint(timestamp=datetime(2025, 12, 1), value=72.0),
            DataPoint(timestamp=datetime(2025, 12, 2), value=74.0),
            DataPoint(timestamp=datetime(2025, 12, 3), value=76.0),
        ]

        trend = HistoricalTrend(
            deployment_id="prod-cribl",
            metric_name="health_score",
            data_points=data_points,
            trend_direction="improving",
        )

        assert trend.deployment_id == "prod-cribl"
        assert trend.metric_name == "health_score"
        assert len(trend.data_points) == 3
        assert trend.trend_direction == "improving"
        assert trend.anomalies_detected == []
        assert trend.forecast_next is None
        assert isinstance(trend.created_at, datetime)
        assert isinstance(trend.updated_at, datetime)

    def test_all_trend_directions(self):
        """Test all valid trend direction values."""
        directions = ["improving", "stable", "declining", "volatile"]

        for direction in directions:
            trend = HistoricalTrend(
                deployment_id="test",
                metric_name="test_metric",
                data_points=[DataPoint(timestamp=datetime(2025, 12, 1), value=50.0)],
                trend_direction=direction,  # type: ignore
            )
            assert trend.trend_direction == direction

    def test_invalid_trend_direction(self):
        """Test that invalid trend direction is rejected."""
        with pytest.raises(ValidationError):
            HistoricalTrend(
                deployment_id="test",
                metric_name="test",
                data_points=[DataPoint(timestamp=datetime(2025, 12, 1), value=50.0)],
                trend_direction="unknown",  # type: ignore
            )

    def test_data_points_required(self):
        """Test that at least one data point is required."""
        # Valid: one data point
        trend = HistoricalTrend(
            deployment_id="test",
            metric_name="test",
            data_points=[DataPoint(timestamp=datetime(2025, 12, 1), value=50.0)],
            trend_direction="stable",
        )
        assert len(trend.data_points) == 1

        # Invalid: empty list
        with pytest.raises(ValidationError):
            HistoricalTrend(
                deployment_id="test",
                metric_name="test",
                data_points=[],
                trend_direction="stable",
            )

    def test_trend_with_forecast(self):
        """Test trend with forecast value."""
        trend = HistoricalTrend(
            deployment_id="test",
            metric_name="health_score",
            data_points=[
                DataPoint(timestamp=datetime(2025, 12, 1), value=70.0),
                DataPoint(timestamp=datetime(2025, 12, 2), value=75.0),
            ],
            trend_direction="improving",
            forecast_next=80.0,
        )

        assert trend.forecast_next == 80.0

    def test_trend_with_anomalies(self):
        """Test trend with detected anomalies."""
        anomaly = DataPoint(timestamp=datetime(2025, 12, 5), value=45.0)
        data_points = [
            DataPoint(timestamp=datetime(2025, 12, 1), value=75.0),
            DataPoint(timestamp=datetime(2025, 12, 2), value=76.0),
            DataPoint(timestamp=datetime(2025, 12, 3), value=77.0),
            DataPoint(timestamp=datetime(2025, 12, 4), value=78.0),
            anomaly,  # Sudden drop
        ]

        trend = HistoricalTrend(
            deployment_id="test",
            metric_name="health_score",
            data_points=data_points,
            trend_direction="volatile",
            anomalies_detected=[anomaly],
        )

        assert len(trend.anomalies_detected) == 1
        assert trend.anomalies_detected[0].value == 45.0

    def test_calculate_trend_direction_stable_few_points(self):
        """Test trend calculation with < 3 data points returns stable."""
        direction = HistoricalTrend.calculate_trend_direction([50.0, 51.0])
        assert direction == "stable"

    def test_calculate_trend_direction_improving(self):
        """Test trend calculation for improving trend."""
        # Clear upward trend
        values = [50.0, 55.0, 60.0, 65.0, 70.0]
        direction = HistoricalTrend.calculate_trend_direction(values)
        assert direction == "improving"

    def test_calculate_trend_direction_declining(self):
        """Test trend calculation for declining trend."""
        # Clear downward trend
        values = [70.0, 65.0, 60.0, 55.0, 50.0]
        direction = HistoricalTrend.calculate_trend_direction(values)
        assert direction == "declining"

    def test_calculate_trend_direction_stable(self):
        """Test trend calculation for stable trend."""
        # Small variations around mean
        values = [50.0, 51.0, 49.0, 50.5, 50.2]
        direction = HistoricalTrend.calculate_trend_direction(values)
        assert direction == "stable"

    def test_calculate_trend_direction_volatile(self):
        """Test trend calculation for volatile trend."""
        # Large swings
        values = [50.0, 80.0, 30.0, 90.0, 40.0]
        direction = HistoricalTrend.calculate_trend_direction(values)
        assert direction == "volatile"

    def test_calculate_trend_uses_last_5_values(self):
        """Test that trend calculation uses last 5 values."""
        # Declining trend in last 5 values, but overall improving
        values = [10.0, 20.0, 30.0, 40.0, 100.0, 95.0, 90.0, 85.0, 80.0]
        direction = HistoricalTrend.calculate_trend_direction(values)
        # Should focus on last 5: [100, 95, 90, 85, 80] = declining
        assert direction == "declining"

    def test_multiple_metrics_for_same_deployment(self):
        """Test tracking multiple metrics for the same deployment."""
        health_trend = HistoricalTrend(
            deployment_id="prod",
            metric_name="health_score",
            data_points=[DataPoint(timestamp=datetime(2025, 12, 1), value=75.0)],
            trend_direction="stable",
        )

        api_calls_trend = HistoricalTrend(
            deployment_id="prod",
            metric_name="api_calls_used",
            data_points=[DataPoint(timestamp=datetime(2025, 12, 1), value=87.0)],
            trend_direction="stable",
        )

        assert health_trend.deployment_id == api_calls_trend.deployment_id
        assert health_trend.metric_name != api_calls_trend.metric_name
