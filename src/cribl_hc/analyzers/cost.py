"""
Cost & License Management Analyzer for Cribl Health Check.

Tracks license consumption, predicts exhaustion timelines, calculates TCO,
and forecasts future costs based on growth trends.

Priority: P5 (Financial planning and license compliance)
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import structlog

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class CostAnalyzer(BaseAnalyzer):
    """
    Analyzer for cost and license management.

    Identifies:
    - License consumption vs allocation
    - License exhaustion timeline predictions (linear regression)
    - Total cost of ownership (TCO) per destination
    - Cost comparison across destinations
    - Future cost forecasting

    Priority: P5 (Cost management - important for budgeting)

    Example:
        >>> async with CriblAPIClient(url, token) as client:
        ...     analyzer = CostAnalyzer()
        ...     analyzer.set_pricing_config({
        ...         "s3": {"storage_cost_per_gb_month": 0.023},
        ...         "splunk_hec": {"ingest_cost_per_gb": 0.15}
        ...     })
        ...     result = await analyzer.analyze(client)
        ...     consumption_pct = result.metadata.get('license_consumption_pct', 0)
        ...     print(f"License Utilization: {consumption_pct:.1f}%")
    """

    # License utilization thresholds
    HIGH_UTILIZATION_THRESHOLD_PCT = 85.0
    CRITICAL_UTILIZATION_THRESHOLD_PCT = 95.0

    # Exhaustion warning thresholds (days)
    CRITICAL_EXHAUSTION_DAYS = 7
    HIGH_EXHAUSTION_DAYS = 30

    # Default pricing (when not configured)
    DEFAULT_PRICING = {
        "s3": {"storage_cost_per_gb_month": 0.023},  # AWS S3 Standard
        "splunk_hec": {"ingest_cost_per_gb": 0.15},  # Splunk Cloud estimate
        "cribl": {"ingest_cost_per_gb": 0.0},  # Free for Cribl-to-Cribl
    }

    def __init__(self):
        """Initialize CostAnalyzer with optional pricing configuration."""
        super().__init__()
        self._pricing_config: Dict[str, Dict[str, float]] = {}

    def set_pricing_config(self, pricing_config: Dict[str, Dict[str, float]]) -> None:
        """
        Set pricing configuration for TCO calculations.

        Args:
            pricing_config: Dictionary mapping output types to pricing info.
                Example: {
                    "s3": {"storage_cost_per_gb_month": 0.023},
                    "splunk_hec": {"ingest_cost_per_gb": 0.15}
                }
        """
        self._pricing_config = pricing_config

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "cost"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: license(1) + metrics(1) + outputs(1) = 3.
        """
        return 3

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:system",  # For license info
            "read:metrics",
            "read:outputs"
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze cost and license management.

        Automatically adapts based on detected product type.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with cost findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            # Detect product type
            product_name = "Cribl Edge" if client.is_edge else "Cribl Stream"
            log.info("cost_analysis_started", product=client.product_type, product_name=product_name)

            # Fetch data
            license_info = await self._fetch_license_info(client)
            outputs = await self._fetch_outputs(client)

            # Analyze license consumption
            license_metrics = self._analyze_license_consumption(license_info, result)

            # Predict license exhaustion
            if license_info.get("consumption_history"):
                self._predict_license_exhaustion(license_info, license_metrics, result)

            # Calculate TCO if pricing configured or use defaults
            pricing = self._pricing_config or self.DEFAULT_PRICING
            if outputs and pricing:
                self._calculate_tco_by_destination(outputs, pricing, result)

            # Generate recommendations
            self._generate_cost_recommendations(license_metrics, outputs, result)

            # Set metadata
            result.metadata.update({
                "product_type": client.product_type,
                "license_allocated_gb": license_metrics.get("allocated_gb", 0),
                "license_consumed_gb": license_metrics.get("consumed_gb", 0),
                "license_consumption_pct": license_metrics.get("consumption_pct", 0),
                "license_exhaustion_days": license_metrics.get("exhaustion_days"),
                "growth_rate_gb_per_day": license_metrics.get("growth_rate_gb_per_day"),
                "outputs_analyzed": len(outputs),
                "total_bytes": sum(o.get("stats", {}).get("out_bytes_total", 0) for o in outputs),
                "analyzed_at": datetime.utcnow().isoformat(),
            })

            result.success = True
            log.info(
                "cost_analysis_completed",
                product=client.product_type,
                consumption_pct=license_metrics.get("consumption_pct", 0),
                exhaustion_days=license_metrics.get("exhaustion_days"),
                findings=len(result.findings),
                recommendations=len(result.recommendations),
            )

        except Exception as e:
            log.error("cost_analysis_failed", error=str(e), exc_info=True)
            # Graceful degradation
            result.metadata.update({
                "product_type": getattr(client, "product_type", "unknown"),
                "license_allocated_gb": 0,
                "license_consumed_gb": 0,
                "license_consumption_pct": 0,
                "outputs_analyzed": 0,
                "total_bytes": 0,
                "error": str(e),
            })
            result.success = True  # Graceful degradation

        return result

    # === Data Fetching ===

    async def _fetch_license_info(self, client: CriblAPIClient) -> Dict[str, Any]:
        """Fetch license information."""
        try:
            return await client.get_license_info() or {}
        except Exception as e:
            log.warning("failed_to_fetch_license_info", error=str(e))
            return {}

    async def _fetch_outputs(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        """Fetch output configurations."""
        try:
            return await client.get_outputs() or []
        except Exception as e:
            log.warning("failed_to_fetch_outputs", error=str(e))
            return []

    # === License Consumption Analysis ===

    def _analyze_license_consumption(
        self,
        license_info: Dict[str, Any],
        result: AnalyzerResult
    ) -> Dict[str, Any]:
        """
        Analyze current license consumption.

        Returns dict with license metrics.
        """
        allocated_gb = license_info.get("daily_gb_limit", 0)
        consumed_gb = license_info.get("current_daily_gb", 0)

        if allocated_gb == 0:
            return {
                "allocated_gb": 0,
                "consumed_gb": 0,
                "consumption_pct": 0
            }

        consumption_pct = (consumed_gb / allocated_gb) * 100

        metrics = {
            "allocated_gb": allocated_gb,
            "consumed_gb": consumed_gb,
            "consumption_pct": consumption_pct,
            "headroom_gb": allocated_gb - consumed_gb
        }

        # Check for high utilization
        if consumption_pct >= self.CRITICAL_UTILIZATION_THRESHOLD_PCT:
            result.add_finding(
                Finding(
                    id="cost-license-critical-utilization",
                    category="cost",
                    severity="critical",
                    title="Critical License Utilization",
                    description=(
                        f"License consumption is at {consumption_pct:.1f}% ({consumed_gb:.1f}GB of {allocated_gb:.1f}GB daily limit). "
                        f"Immediate action required to avoid license violations."
                    ),
                    affected_components=["license"],
                    confidence_level="high",
                    estimated_impact="License exhaustion will cause data loss or service disruption",
                    remediation_steps=[
                        "Review high-volume data sources immediately",
                        "Implement filtering or sampling on verbose sources",
                        "Contact Cribl sales to increase license allocation",
                        "Monitor consumption hourly until resolved",
                    ],
                    documentation_links=[
                        "https://docs.cribl.io/stream/license-management",
                    ],
                    metadata={
                        "consumption_pct": consumption_pct,
                        "allocated_gb": allocated_gb,
                        "consumed_gb": consumed_gb,
                        "headroom_gb": allocated_gb - consumed_gb,
                    },
                )
            )
        elif consumption_pct >= self.HIGH_UTILIZATION_THRESHOLD_PCT:
            result.add_finding(
                Finding(
                    id="cost-license-high-utilization",
                    category="cost",
                    severity="high",
                    title="High License Utilization",
                    description=(
                        f"License consumption is at {consumption_pct:.1f}% ({consumed_gb:.1f}GB of {allocated_gb:.1f}GB daily limit). "
                        f"Consider optimization or license expansion."
                    ),
                    affected_components=["license"],
                    confidence_level="high",
                    estimated_impact="Risk of license exhaustion if consumption continues to grow",
                    remediation_steps=[
                        "Identify high-volume data sources",
                        "Review and optimize data routing rules",
                        "Consider implementing data reduction techniques",
                        "Plan for license expansion if growth is expected",
                    ],
                    documentation_links=[
                        "https://docs.cribl.io/stream/license-management",
                    ],
                    metadata={
                        "consumption_pct": consumption_pct,
                        "allocated_gb": allocated_gb,
                        "consumed_gb": consumed_gb,
                    },
                )
            )

        return metrics

    # === License Exhaustion Prediction ===

    def _predict_license_exhaustion(
        self,
        license_info: Dict[str, Any],
        license_metrics: Dict[str, Any],
        result: AnalyzerResult
    ) -> None:
        """
        Predict license exhaustion timeline using linear regression.

        Args:
            license_info: License data with consumption_history
            license_metrics: Current license metrics
            result: AnalyzerResult to add findings to
        """
        history = license_info.get("consumption_history", [])
        if len(history) < 2:
            # Need at least 2 data points for trend
            return

        allocated_gb = license_metrics["allocated_gb"]
        current_gb = license_metrics["consumed_gb"]

        # Calculate linear regression (simple least squares)
        growth_rate_gb_per_day = self._calculate_linear_regression(history)

        if growth_rate_gb_per_day <= 0:
            # No growth or declining - no exhaustion predicted
            license_metrics["growth_rate_gb_per_day"] = growth_rate_gb_per_day
            return

        # Calculate days until exhaustion
        headroom_gb = allocated_gb - current_gb
        if headroom_gb <= 0:
            days_to_exhaustion = 0
        else:
            days_to_exhaustion = int(headroom_gb / growth_rate_gb_per_day)

        license_metrics["growth_rate_gb_per_day"] = growth_rate_gb_per_day
        license_metrics["exhaustion_days"] = days_to_exhaustion

        # Create findings based on timeline
        if days_to_exhaustion <= self.CRITICAL_EXHAUSTION_DAYS:
            result.add_finding(
                Finding(
                    id="cost-license-exhaustion-imminent",
                    category="cost",
                    severity="critical",
                    title="License Exhaustion Imminent",
                    description=(
                        f"License will exhaust in approximately {days_to_exhaustion} day(s) "
                        f"based on current growth rate of {growth_rate_gb_per_day:.1f}GB/day. "
                        f"Immediate action required."
                    ),
                    affected_components=["license"],
                    confidence_level="high",
                    estimated_impact="License exhaustion will cause data loss within a week",
                    remediation_steps=[
                        f"Reduce consumption by {growth_rate_gb_per_day * self.CRITICAL_EXHAUSTION_DAYS:.1f}GB/day immediately",
                        "Implement emergency data filtering or sampling",
                        "Contact Cribl sales for license expansion",
                        "Identify and disable non-critical data sources",
                    ],
                    documentation_links=[
                        "https://docs.cribl.io/stream/license-management",
                    ],
                    metadata={
                        "days_to_exhaustion": days_to_exhaustion,
                        "growth_rate_gb_per_day": growth_rate_gb_per_day,
                        "current_gb": current_gb,
                        "allocated_gb": allocated_gb,
                    },
                )
            )
        elif days_to_exhaustion <= self.HIGH_EXHAUSTION_DAYS:
            result.add_finding(
                Finding(
                    id="cost-license-exhaustion-predicted",
                    category="cost",
                    severity="high",
                    title="License Exhaustion Predicted",
                    description=(
                        f"License will exhaust in approximately {days_to_exhaustion} day(s) "
                        f"based on current growth rate of {growth_rate_gb_per_day:.1f}GB/day. "
                        f"Plan optimization or expansion."
                    ),
                    affected_components=["license"],
                    confidence_level="medium",
                    estimated_impact="License exhaustion predicted within 30 days",
                    remediation_steps=[
                        "Review consumption trends and identify growth sources",
                        "Implement data reduction strategies",
                        "Plan for license expansion",
                        "Monitor consumption daily",
                    ],
                    documentation_links=[
                        "https://docs.cribl.io/stream/license-management",
                    ],
                    metadata={
                        "days_to_exhaustion": days_to_exhaustion,
                        "growth_rate_gb_per_day": growth_rate_gb_per_day,
                    },
                )
            )

    def _calculate_linear_regression(self, history: List[Dict[str, Any]]) -> float:
        """
        Calculate linear regression to determine growth rate.

        Simple least squares regression: y = mx + b (we only need m, the slope)

        Returns:
            Growth rate in GB per day
        """
        if len(history) < 2:
            return 0.0

        # Extract GB values (y) and create day indices (x)
        gb_values = [point.get("gb", 0) for point in history]
        n = len(gb_values)
        x_values = list(range(n))

        # Calculate means
        x_mean = sum(x_values) / n
        y_mean = sum(gb_values) / n

        # Calculate slope (m)
        numerator = sum((x_values[i] - x_mean) * (gb_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator
        return slope

    # === TCO Calculation ===

    def _calculate_tco_by_destination(
        self,
        outputs: List[Dict[str, Any]],
        pricing: Dict[str, Dict[str, float]],
        result: AnalyzerResult
    ) -> None:
        """
        Calculate total cost of ownership per destination.

        Args:
            outputs: Output configurations with volume data
            pricing: Pricing configuration
            result: AnalyzerResult to add metadata to
        """
        tco_by_dest = {}

        for output in outputs:
            output_id = output.get("id", "unknown")
            output_type = output.get("type", "unknown")
            bytes_total = output.get("stats", {}).get("out_bytes_total", 0)
            gb_total = bytes_total / (1024 ** 3)

            # Get pricing for this output type
            output_pricing = pricing.get(output_type, {})
            if not output_pricing:
                continue

            # Calculate cost based on pricing model
            cost = 0.0
            if "storage_cost_per_gb_month" in output_pricing:
                # Storage-based pricing (e.g., S3)
                cost = gb_total * output_pricing["storage_cost_per_gb_month"]
            elif "ingest_cost_per_gb" in output_pricing:
                # Ingest-based pricing (e.g., Splunk)
                cost = gb_total * output_pricing["ingest_cost_per_gb"]

            tco_by_dest[output_id] = {
                "type": output_type,
                "gb_total": gb_total,
                "estimated_cost": cost,
                "pricing_model": "storage" if "storage_cost_per_gb_month" in output_pricing else "ingest"
            }

        if tco_by_dest:
            result.metadata["tco_by_destination"] = tco_by_dest
            result.metadata["total_estimated_cost"] = sum(
                dest["estimated_cost"] for dest in tco_by_dest.values()
            )

    # === Recommendations ===

    def _generate_cost_recommendations(
        self,
        license_metrics: Dict[str, Any],
        outputs: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """Generate cost optimization recommendations."""

        consumption_pct = license_metrics.get("consumption_pct", 0)
        exhaustion_days = license_metrics.get("exhaustion_days")

        # Recommendation: Optimize license consumption
        if consumption_pct >= self.HIGH_UTILIZATION_THRESHOLD_PCT:
            result.add_recommendation(
                Recommendation(
                    id="cost-optimize-license-consumption",
                    type="cost",
                    priority="p1" if consumption_pct >= self.CRITICAL_UTILIZATION_THRESHOLD_PCT else "p2",
                    title="Optimize License Consumption",
                    description=(
                        f"License utilization is at {consumption_pct:.1f}%. "
                        f"Implement data reduction strategies to optimize consumption."
                    ),
                    rationale="High license utilization increases risk of exhaustion and indicates inefficient data routing",
                    implementation_steps=[
                        "Audit data sources by volume (identify top 10 consumers)",
                        "Implement filtering rules to drop low-value data",
                        "Apply sampling to verbose/debug logs",
                        "Review and optimize route configurations",
                        "Monitor consumption after changes",
                    ],
                    implementation_effort="medium",
                    impact_estimate=ImpactEstimate(
                        cost_savings_annual=license_metrics.get("consumed_gb", 0) * 0.3 * 365 * 0.10 if license_metrics.get("consumed_gb", 0) > 0 else None,  # Est. 30% reduction * daily cost
                        performance_improvement="Reduces license costs and extends runway",
                    ),
                    before_state=f"License at {consumption_pct:.1f}% utilization",
                    after_state="License optimized to 60-70% utilization with headroom for growth",
                )
            )

        # Recommendation: Expand license if exhaustion imminent
        if exhaustion_days and exhaustion_days <= self.HIGH_EXHAUSTION_DAYS:
            result.add_recommendation(
                Recommendation(
                    id="cost-expand-license",
                    type="cost",
                    priority="p0" if exhaustion_days <= self.CRITICAL_EXHAUSTION_DAYS else "p1",
                    title="Expand License Allocation",
                    description=(
                        f"License exhaustion predicted in {exhaustion_days} day(s). "
                        f"Consider license expansion to avoid service disruption."
                    ),
                    rationale="License exhaustion will cause data loss or service disruption",
                    implementation_steps=[
                        "Contact Cribl sales for license expansion quote",
                        "Calculate required additional capacity based on growth trends",
                        "Implement temporary data reduction while procurement in progress",
                        "Plan for future growth to avoid repeated expansions",
                    ],
                    implementation_effort="low",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Prevents license exhaustion and data loss",
                    ),
                    before_state=f"License exhaustion in {exhaustion_days} day(s)",
                    after_state="License capacity sufficient for 6+ months of growth",
                )
            )
