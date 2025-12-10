"""
Historical trend model for tracking metric changes over time.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DataPoint(BaseModel):
    """
    Single data point in a time series.

    Attributes:
        timestamp: When this measurement was taken
        value: Numeric value of the measurement
        metadata: Additional context for this data point
    """

    timestamp: datetime = Field(..., description="Measurement timestamp")
    value: float = Field(..., description="Measurement value")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class HistoricalTrend(BaseModel):
    """
    Time-series data for tracking metric changes over multiple analysis runs.

    Trend Direction Calculation:
    - If < 3 data points: stable
    - Calculate slope and variance from last 5 points
    - If variance > 0.2: volatile
    - If slope > 0.1: improving
    - If slope < -0.1: declining
    - Otherwise: stable

    Attributes:
        deployment_id: Deployment being tracked
        metric_name: Metric name (e.g., "health_score", "api_calls_used", "finding_count")
        data_points: Time-series data points
        trend_direction: Overall trend direction
        anomalies_detected: Data points flagged as anomalous
        forecast_next: Predicted next value (optional)
        created_at: When trend tracking started
        updated_at: Last update timestamp

    Example:
        >>> trend = HistoricalTrend(
        ...     deployment_id="prod-cribl",
        ...     metric_name="health_score",
        ...     data_points=[
        ...         DataPoint(timestamp=datetime(2025, 12, 1), value=72.0),
        ...         DataPoint(timestamp=datetime(2025, 12, 10), value=78.0)
        ...     ],
        ...     trend_direction="improving"
        ... )
    """

    deployment_id: str = Field(..., description="Deployment ID", min_length=1)
    metric_name: str = Field(..., description="Metric name", min_length=1)
    data_points: list[DataPoint] = Field(..., description="Time-series data", min_items=1)
    trend_direction: Literal["improving", "stable", "declining", "volatile"] = Field(
        ..., description="Trend direction"
    )
    anomalies_detected: list[DataPoint] = Field(
        default_factory=list, description="Anomalous data points"
    )
    forecast_next: Optional[float] = Field(None, description="Predicted next value")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @staticmethod
    def calculate_trend_direction(values: list[float]) -> Literal["improving", "stable", "declining", "volatile"]:
        """
        Calculate trend direction from a list of values.

        Args:
            values: List of numeric values (most recent last)

        Returns:
            Trend direction: improving, stable, declining, or volatile

        Note:
            This is a simplified implementation. Production code should use
            proper statistical methods (linear regression, standard deviation).
        """
        if len(values) < 3:
            return "stable"

        # Use last 5 values or all if fewer
        recent = values[-5:] if len(values) >= 5 else values

        # Simple slope calculation (first to last)
        slope = (recent[-1] - recent[0]) / len(recent)

        # Simple variance estimation
        mean_val = sum(recent) / len(recent)
        variance = sum((x - mean_val) ** 2 for x in recent) / len(recent)
        relative_variance = variance / (mean_val + 0.001)  # Avoid division by zero

        # Classification
        if relative_variance > 0.2:
            return "volatile"
        elif slope > 0.1:
            return "improving"
        elif slope < -0.1:
            return "declining"
        return "stable"

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "deployment_id": "prod-cribl",
                "metric_name": "health_score",
                "data_points": [
                    {"timestamp": "2025-12-01T00:00:00Z", "value": 72.0, "metadata": {}},
                    {"timestamp": "2025-12-02T00:00:00Z", "value": 74.0, "metadata": {}},
                    {"timestamp": "2025-12-03T00:00:00Z", "value": 76.0, "metadata": {}},
                    {"timestamp": "2025-12-10T14:03:45Z", "value": 78.0, "metadata": {}},
                ],
                "trend_direction": "improving",
                "anomalies_detected": [],
                "forecast_next": 80.0,
                "created_at": "2025-12-01T00:00:00Z",
                "updated_at": "2025-12-10T14:03:45Z",
            }
        }
