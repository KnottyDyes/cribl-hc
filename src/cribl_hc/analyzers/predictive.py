"""
Predictive Analytics Analyzer for Cribl Health Check.

Provides proactive recommendations based on historical trends, capacity predictions,
and anomaly detection.

Priority: P7 (Predictive analytics - advanced feature)
"""

import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import structlog

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class PredictiveAnalyzer(BaseAnalyzer):
    """
    Analyzer for predictive analytics and proactive recommendations.

    Identifies:
    - Worker capacity exhaustion predictions
    - License consumption forecasting
    - Destination backpressure predictions
    - Anomaly detection in metrics
    - Proactive scaling recommendations

    Priority: P7 (Predictive analytics - valuable for proactive operations)

    Example:
        >>> analyzer = PredictiveAnalyzer()
        >>> historical_data = {
        ...     "worker_metrics": [
        ...         {"timestamp": "2025-12-21", "cpu_avg": 60},
        ...         {"timestamp": "2025-12-22", "cpu_avg": 65},
        ...         {"timestamp": "2025-12-23", "cpu_avg": 70}
        ...     ]
        ... }
        >>> result = await analyzer.analyze(client, historical_data=historical_data)
        >>> print(f"Predictions: {len(result.findings)}")
    """

    def __init__(self):
        """Initialize PredictiveAnalyzer."""
        super().__init__()

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "predictive"

    @property
    def supported_products(self) -> List[str]:
        """Predictive analyzer supports all products."""
        return ["stream", "edge", "lake", "search"]

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls for predictive analysis.

        Calls: workers(1) + license_info(1) + outputs(1) = 3 calls.
        """
        return 3

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:workers",
            "read:license",
            "read:outputs"
        ]

    async def analyze(
        self,
        client: CriblAPIClient,
        historical_data: Optional[Dict[str, Any]] = None
    ) -> AnalyzerResult:
        """
        Analyze current state and historical data for predictions.

        Args:
            client: Cribl API client
            historical_data: Optional dictionary with historical metrics
                Expected keys:
                - worker_metrics: List of {"timestamp": str, "cpu_avg": float, "memory_avg": float}
                - license_consumption: List of {"date": str, "gb": float}
                - destination_throughput: Dict of destination_id -> List of throughput data
                - health_scores: List of {"timestamp": str, "score": float}

        Returns:
            AnalyzerResult with predictions and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        # Track data availability
        has_historical = historical_data is not None and len(historical_data) > 0
        result.metadata["historical_data_available"] = has_historical

        if not has_historical:
            self.log.info("predictive_analysis_limited_no_historical_data")
            result.metadata["data_points"] = 0
            result.success = True
            return result

        # Count data points
        data_points = sum(
            len(v) if isinstance(v, list) else 1
            for v in historical_data.values()
        )
        result.metadata["data_points"] = data_points

        # Analyze worker capacity trends
        await self._predict_worker_capacity(client, historical_data, result)

        # Analyze license consumption trends
        await self._predict_license_exhaustion(client, historical_data, result)

        # Analyze destination throughput
        await self._predict_destination_backpressure(client, historical_data, result)

        # Detect anomalies
        self._detect_anomalies(historical_data, result)

        # Generate proactive recommendations
        self._generate_proactive_recommendations(historical_data, result)

        # Calculate prediction confidence
        confidence = self._calculate_prediction_confidence(data_points)
        result.metadata["prediction_confidence"] = confidence

        result.success = True
        self.log.info(
            "predictive_analysis_completed",
            findings=len(result.findings),
            recommendations=len(result.recommendations),
            confidence=confidence
        )

        return result

    async def _predict_worker_capacity(
        self,
        client: CriblAPIClient,
        historical_data: Dict[str, Any],
        result: AnalyzerResult
    ) -> None:
        """
        Predict worker capacity exhaustion based on trends.

        Args:
            client: API client
            historical_data: Historical metrics
            result: Result to add findings to
        """
        worker_metrics = historical_data.get("worker_metrics", [])
        if len(worker_metrics) < 3:
            return  # Need at least 3 data points for trend

        # Extract CPU trend
        cpu_values = [m.get("cpu_avg", 0) for m in worker_metrics if "cpu_avg" in m]
        if not cpu_values:
            return

        # Calculate linear trend
        trend_slope = self._calculate_trend_slope(cpu_values)

        # Predict exhaustion (>90% threshold)
        if trend_slope > 0:
            current_cpu = cpu_values[-1]
            days_to_exhaustion = (90 - current_cpu) / trend_slope if trend_slope > 0 else None

            if days_to_exhaustion and 0 < days_to_exhaustion <= 30:
                result.add_finding(Finding(
                    id="predictive-worker-capacity-exhaustion",
                    category="predictive",
                    severity="high",
                    title="Worker Capacity Exhaustion Predicted",
                    description=(
                        f"Current CPU utilization trend predicts exhaustion in approximately "
                        f"{int(days_to_exhaustion)} days. Current average: {current_cpu:.1f}%, "
                        f"trend: +{trend_slope:.2f}% per day."
                    ),
                    confidence_level="medium",
                    estimated_impact="Worker overload and potential service degradation",
                    remediation_steps=[
                        "Add additional worker nodes before capacity is exhausted",
                        "Review and optimize high-CPU pipelines",
                        "Consider implementing auto-scaling policies",
                        "Monitor worker metrics closely"
                    ],
                    metadata={
                        "current_cpu_avg": current_cpu,
                        "trend_slope": trend_slope,
                        "days_to_exhaustion": int(days_to_exhaustion),
                        "data_points": len(cpu_values)
                    }
                ))

    async def _predict_license_exhaustion(
        self,
        client: CriblAPIClient,
        historical_data: Dict[str, Any],
        result: AnalyzerResult
    ) -> None:
        """
        Predict license exhaustion based on consumption trends.

        Args:
            client: API client
            historical_data: Historical metrics
            result: Result to add findings to
        """
        license_consumption = historical_data.get("license_consumption", [])
        if len(license_consumption) < 3:
            return

        # Extract consumption values
        gb_values = [c.get("gb", 0) for c in license_consumption if "gb" in c]
        if not gb_values:
            return

        # Calculate trend
        trend_slope = self._calculate_trend_slope(gb_values)

        # Get current license limit if available
        try:
            license_info = await client.get_license_info()
            daily_limit = license_info.get("daily_gb_limit", 0)

            if daily_limit > 0 and trend_slope > 0:
                current_gb = gb_values[-1]
                days_to_exhaustion = (daily_limit - current_gb) / trend_slope if trend_slope > 0 else None

                if days_to_exhaustion and 0 < days_to_exhaustion <= 60:
                    severity = "critical" if days_to_exhaustion <= 14 else "high"
                    result.add_finding(Finding(
                        id="predictive-license-exhaustion",
                        category="predictive",
                        severity=severity,
                        title="License Exhaustion Predicted",
                        description=(
                            f"Current license consumption trend predicts exhaustion in approximately "
                            f"{int(days_to_exhaustion)} days. Current usage: {current_gb:.1f} GB/day, "
                            f"limit: {daily_limit} GB/day, trend: +{trend_slope:.2f} GB/day."
                        ),
                        confidence_level="high",
                        estimated_impact="License limit exceeded, potential data loss or service interruption",
                        remediation_steps=[
                            "Review data sources and reduce unnecessary ingestion",
                            "Implement additional data reduction strategies",
                            "Contact Cribl for license expansion options",
                            "Optimize pipelines to reduce data volume"
                        ],
                        metadata={
                            "current_gb_per_day": current_gb,
                            "daily_limit": daily_limit,
                            "trend_slope": trend_slope,
                            "days_to_exhaustion": int(days_to_exhaustion),
                            "utilization_pct": (current_gb / daily_limit) * 100
                        }
                    ))
        except Exception as e:
            self.log.warning("failed_to_get_license_info", error=str(e))

    async def _predict_destination_backpressure(
        self,
        client: CriblAPIClient,
        historical_data: Dict[str, Any],
        result: AnalyzerResult
    ) -> None:
        """
        Predict destination backpressure from throughput trends.

        Args:
            client: API client
            historical_data: Historical metrics
            result: Result to add findings to
        """
        destination_throughput = historical_data.get("destination_throughput", {})
        if not destination_throughput:
            return

        for dest_id, throughput_data in destination_throughput.items():
            if len(throughput_data) < 3:
                continue

            # Extract throughput values
            gb_per_hour = [t.get("gb_per_hour", 0) for t in throughput_data if "gb_per_hour" in t]
            if not gb_per_hour:
                continue

            # Calculate trend
            trend_slope = self._calculate_trend_slope(gb_per_hour)

            # Predict backpressure if trend is upward and current is high
            current_throughput = gb_per_hour[-1]
            if trend_slope > 0.5 and current_throughput > 50:  # Arbitrary thresholds
                result.add_finding(Finding(
                    id=f"predictive-backpressure-{dest_id}",
                    category="predictive",
                    severity="medium",
                    title=f"Destination Backpressure Risk: {dest_id}",
                    description=(
                        f"Destination {dest_id} shows increasing throughput trend. "
                        f"Current: {current_throughput:.1f} GB/hour, trend: +{trend_slope:.2f} GB/hour per day. "
                        f"This may lead to backpressure."
                    ),
                    confidence_level="medium",
                    estimated_impact="Potential backpressure and data buffering",
                    remediation_steps=[
                        f"Monitor {dest_id} for backpressure indicators",
                        "Review destination capacity and scaling options",
                        "Implement persistent queuing if not already enabled",
                        "Consider load balancing across multiple destinations"
                    ],
                    affected_components=[dest_id],
                    metadata={
                        "destination_id": dest_id,
                        "current_throughput_gb_per_hour": current_throughput,
                        "trend_slope": trend_slope
                    }
                ))

    def _detect_anomalies(
        self,
        historical_data: Dict[str, Any],
        result: AnalyzerResult
    ) -> None:
        """
        Detect anomalies in historical metrics using z-score.

        Args:
            historical_data: Historical metrics
            result: Result to add findings to
        """
        # Check health scores for anomalies
        health_scores = historical_data.get("health_scores", [])
        if len(health_scores) >= 5:
            scores = [h.get("score", 0) for h in health_scores if "score" in h]
            anomalies = self._detect_zscore_anomalies(scores, threshold=2.5)

            if anomalies:
                result.add_finding(Finding(
                    id="predictive-anomaly-health-score",
                    category="predictive",
                    severity="medium",
                    title="Health Score Anomaly Detected",
                    description=(
                        f"Detected {len(anomalies)} anomalous health score(s) in recent history. "
                        f"This may indicate underlying issues requiring investigation."
                    ),
                    confidence_level="high",
                    estimated_impact="Potential service instability",
                    remediation_steps=[
                        "Investigate cause of health score drops",
                        "Review logs and metrics during anomaly periods",
                        "Check for infrastructure or configuration changes",
                        "Implement monitoring alerts for similar patterns"
                    ],
                    metadata={
                        "anomaly_count": len(anomalies),
                        "anomaly_indices": anomalies
                    }
                ))

        # Check worker metrics for anomalies
        worker_metrics = historical_data.get("worker_metrics", [])
        if len(worker_metrics) >= 5:
            cpu_values = [w.get("cpu_avg", 0) for w in worker_metrics if "cpu_avg" in w]
            anomalies = self._detect_zscore_anomalies(cpu_values, threshold=3.0)

            if anomalies:
                result.metadata["anomalies_detected"] = True
                result.metadata["cpu_anomaly_count"] = len(anomalies)

    def _generate_proactive_recommendations(
        self,
        historical_data: Dict[str, Any],
        result: AnalyzerResult
    ) -> None:
        """
        Generate proactive scaling and optimization recommendations.

        Args:
            historical_data: Historical metrics
            result: Result to add recommendations to
        """
        worker_metrics = historical_data.get("worker_metrics", [])
        if len(worker_metrics) < 4:
            return

        # Check for sustained growth
        cpu_values = [w.get("cpu_avg", 0) for w in worker_metrics if "cpu_avg" in w]
        if not cpu_values:
            return

        trend_slope = self._calculate_trend_slope(cpu_values)

        # Recommend scaling if sustained growth
        if trend_slope > 1.0:  # >1% increase per day
            current_cpu = cpu_values[-1]

            result.add_recommendation(Recommendation(
                id="predictive-rec-scale-workers",
                type="scaling",
                priority="p1",
                title="Proactive Worker Scaling Recommended",
                description=(
                    f"Worker CPU utilization shows sustained growth trend (+{trend_slope:.2f}% per day). "
                    f"Proactive scaling recommended before capacity issues occur."
                ),
                rationale="Preventing capacity exhaustion is more cost-effective than reactive scaling",
                implementation_steps=[
                    "Plan worker node additions based on projected growth",
                    "Test scaling procedures in non-production environment",
                    "Schedule scaling during low-traffic period",
                    "Monitor post-scaling metrics to validate improvement"
                ],
                before_state=f"Current CPU average: {current_cpu:.1f}%, upward trend detected",
                after_state="Adequate capacity buffer for projected growth",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Prevents capacity-related performance degradation",
                    cost_impact="Incremental infrastructure cost, prevents emergency scaling costs"
                ),
                implementation_effort="medium",
                metadata={
                    "current_cpu_avg": current_cpu,
                    "trend_slope": trend_slope,
                    "recommendation_type": "proactive_scaling"
                }
            ))

    def _calculate_trend_slope(self, values: List[float]) -> float:
        """
        Calculate linear trend slope using simple linear regression.

        Args:
            values: List of numeric values

        Returns:
            Slope of trend line (change per time period)
        """
        if len(values) < 2:
            return 0.0

        n = len(values)
        x = list(range(n))
        y = values

        # Simple linear regression
        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator
        return slope

    def _detect_zscore_anomalies(
        self,
        values: List[float],
        threshold: float = 3.0
    ) -> List[int]:
        """
        Detect anomalies using z-score method.

        Args:
            values: List of numeric values
            threshold: Z-score threshold (default 3.0 = 3 standard deviations)

        Returns:
            List of indices where anomalies detected
        """
        if len(values) < 3:
            return []

        try:
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)

            if stdev == 0:
                return []

            anomalies = []
            for i, value in enumerate(values):
                z_score = abs((value - mean) / stdev)
                if z_score > threshold:
                    anomalies.append(i)

            return anomalies
        except Exception as e:
            self.log.warning("zscore_calculation_failed", error=str(e))
            return []

    def _calculate_prediction_confidence(self, data_points: int) -> str:
        """
        Calculate confidence level based on available data points.

        Args:
            data_points: Number of historical data points

        Returns:
            Confidence level (low/medium/high)
        """
        if data_points >= 20:
            return "high"
        elif data_points >= 10:
            return "medium"
        else:
            return "low"
