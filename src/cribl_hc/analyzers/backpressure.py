"""
Backpressure Analyzer for Cribl Health Check.

Analyzes destination backpressure, persistent queue depth, queue exhaustion
prediction, and HTTP destination retry patterns.

Priority: P1 (High Impact - Production Operations)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class BackpressureAnalyzer(BaseAnalyzer):
    """
    Analyzer for runtime backpressure and queue health.

    Identifies:
    - Destinations experiencing backpressure (blocked outputs)
    - Persistent queues approaching capacity
    - Queue exhaustion predictions based on growth trends
    - HTTP destinations with high retry rates (5xx errors)

    Priority: P1 (High Impact - addresses production operational issues)
    """

    # Backpressure thresholds
    BACKPRESSURE_WARNING_PERCENT = 10.0  # >10% blocked events
    BACKPRESSURE_CRITICAL_PERCENT = 25.0  # >25% blocked events

    # Persistent Queue thresholds
    PQ_WARNING_PERCENT = 70.0  # Queue 70% full
    PQ_CRITICAL_PERCENT = 90.0  # Queue 90% full
    PQ_SIZE_WARNING_GB = 5.0  # 5GB queue size warning
    PQ_SIZE_CRITICAL_GB = 10.0  # 10GB queue size critical

    # HTTP retry thresholds
    HTTP_RETRY_WARNING_PERCENT = 5.0  # >5% retry rate
    HTTP_RETRY_CRITICAL_PERCENT = 15.0  # >15% retry rate

    # Queue growth prediction
    EXHAUSTION_WARNING_HOURS = 24  # Warn if exhaustion within 24 hours
    EXHAUSTION_CRITICAL_HOURS = 4  # Critical if exhaustion within 4 hours

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "backpressure"

    @property
    def supported_products(self) -> List[str]:
        """Backpressure analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Analyzes destination backpressure, queue health, and retry patterns"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls: outputs(1) + metrics(1) = 2.
        """
        return 2

    def get_required_permissions(self) -> List[str]:
        """Return required API permissions."""
        return [
            "read:outputs",
            "read:metrics",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze backpressure and queue health across destinations.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with backpressure findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            log.info("backpressure_analysis_started")

            # Fetch outputs/destinations configuration
            outputs = await client.get_outputs()

            # Fetch metrics for runtime data
            metrics = await client.get_metrics(time_range="1h")

            # Extract relevant metrics
            output_metrics = self._extract_output_metrics(metrics)
            pq_metrics = self._extract_pq_metrics(metrics)

            # Initialize metadata
            result.metadata.update({
                "total_outputs": len(outputs),
                "outputs_with_pq": sum(1 for o in outputs if o.get("pqEnabled")),
                "analysis_timestamp": datetime.utcnow().isoformat()
            })

            # Handle empty state
            if not outputs:
                result.add_finding(
                    Finding(
                        id="backpressure-no-outputs",
                        category="backpressure",
                        severity="info",
                        title="No Outputs Configured",
                        description="No output destinations found for backpressure analysis.",
                        affected_components=["Outputs"],
                        confidence_level="high",
                        metadata={}
                    )
                )
                result.success = True
                return result

            # Analyze backpressure on outputs
            self._analyze_output_backpressure(outputs, output_metrics, result)

            # Analyze persistent queues
            self._analyze_persistent_queues(outputs, pq_metrics, result)

            # Analyze HTTP destination retry patterns
            self._analyze_http_retries(outputs, output_metrics, result)

            # Predict queue exhaustion
            self._predict_queue_exhaustion(outputs, pq_metrics, result)

            # Add summary metadata
            self._add_summary_metadata(result)

            result.success = True
            log.info(
                "backpressure_analysis_completed",
                outputs=len(outputs),
                findings=len(result.findings),
                recommendations=len(result.recommendations)
            )

        except Exception as e:
            log.error("backpressure_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)
            result.add_finding(
                Finding(
                    id="backpressure-analysis-error",
                    category="backpressure",
                    severity="critical",
                    title="Backpressure Analysis Failed",
                    description=f"Failed to analyze backpressure: {str(e)}",
                    affected_components=["Backpressure Analyzer"],
                    remediation_steps=["Check API connectivity", "Verify permissions"],
                    estimated_impact="Cannot assess destination health",
                    confidence_level="high",
                    metadata={"error": str(e)}
                )
            )

        return result

    def _extract_output_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Extract output-specific metrics from the metrics response.

        Returns dict keyed by output ID with metrics like:
        - events_out: total events sent
        - events_blocked: events blocked due to backpressure
        - bytes_out: total bytes sent
        - retries: number of retries (for HTTP outputs)
        - errors_5xx: 5xx error count
        """
        output_metrics = {}

        # Metrics may be nested under various keys depending on Cribl version
        # Common patterns: metrics.outputs, metrics.destinations, or flat structure
        outputs_data = metrics.get("outputs", {})
        if not outputs_data:
            outputs_data = metrics.get("destinations", {})

        for output_id, data in outputs_data.items():
            if isinstance(data, dict):
                output_metrics[output_id] = {
                    "events_out": data.get("out", {}).get("events", 0),
                    "events_blocked": data.get("blocked", {}).get("events", 0),
                    "bytes_out": data.get("out", {}).get("bytes", 0),
                    "retries": data.get("retries", 0),
                    "errors_5xx": data.get("errors", {}).get("5xx", 0),
                    "errors_total": data.get("errors", {}).get("total", 0),
                    "backpressure_time_ms": data.get("backpressure", {}).get("time_ms", 0),
                }

        return output_metrics

    def _extract_pq_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Extract persistent queue metrics from the metrics response.

        Returns dict keyed by output ID with:
        - queue_size_bytes: current queue size
        - queue_size_max_bytes: maximum configured size
        - queue_events: number of events in queue
        - queue_growth_rate: bytes/second growth rate (if available)
        """
        pq_metrics = {}

        # PQ metrics may be under pq, persistent_queues, or nested in outputs
        pq_data = metrics.get("pq", {})
        if not pq_data:
            pq_data = metrics.get("persistent_queues", {})

        for output_id, data in pq_data.items():
            if isinstance(data, dict):
                pq_metrics[output_id] = {
                    "queue_size_bytes": data.get("size_bytes", 0),
                    "queue_size_max_bytes": data.get("max_size_bytes", 0),
                    "queue_events": data.get("events", 0),
                    "queue_growth_rate": data.get("growth_rate_bps", 0),
                    "queue_drain_rate": data.get("drain_rate_bps", 0),
                }

        return pq_metrics

    def _analyze_output_backpressure(
        self,
        outputs: List[Dict[str, Any]],
        output_metrics: Dict[str, Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """Analyze backpressure on output destinations."""
        outputs_with_backpressure = []
        critical_backpressure = []

        for output in outputs:
            output_id = output.get("id", "unknown")
            output_type = output.get("type", "unknown")

            metrics = output_metrics.get(output_id, {})
            events_out = metrics.get("events_out", 0)
            events_blocked = metrics.get("events_blocked", 0)

            if events_out + events_blocked > 0:
                blocked_percent = (events_blocked / (events_out + events_blocked)) * 100

                if blocked_percent >= self.BACKPRESSURE_CRITICAL_PERCENT:
                    critical_backpressure.append(output_id)
                    self._report_backpressure(
                        output_id, output_type, blocked_percent, "critical", result
                    )
                elif blocked_percent >= self.BACKPRESSURE_WARNING_PERCENT:
                    outputs_with_backpressure.append(output_id)
                    self._report_backpressure(
                        output_id, output_type, blocked_percent, "warning", result
                    )

        result.metadata["outputs_with_backpressure"] = len(outputs_with_backpressure)
        result.metadata["outputs_critical_backpressure"] = len(critical_backpressure)

    def _report_backpressure(
        self,
        output_id: str,
        output_type: str,
        blocked_percent: float,
        severity_level: str,
        result: AnalyzerResult
    ) -> None:
        """Report a backpressure finding."""
        severity = "high" if severity_level == "critical" else "medium"

        result.add_finding(
            Finding(
                id=f"backpressure-output-{output_id}",
                category="backpressure",
                severity=severity,
                title=f"Backpressure on Destination: {output_id}",
                description=(
                    f"Destination '{output_id}' ({output_type}) has {blocked_percent:.1f}% "
                    f"of events blocked due to backpressure. This indicates the destination "
                    f"cannot keep up with incoming data volume."
                ),
                affected_components=["Outputs", output_id],
                remediation_steps=[
                    "Check destination availability and performance",
                    "Review destination connection settings (timeouts, batch sizes)",
                    "Enable or increase persistent queue capacity",
                    "Consider scaling the destination or adding load balancing",
                    "Review pipeline routing to reduce volume to this destination"
                ],
                estimated_impact="Data buffering or potential data loss",
                confidence_level="high",
                metadata={
                    "output_id": output_id,
                    "output_type": output_type,
                    "blocked_percent": round(blocked_percent, 2)
                }
            )
        )

        if severity_level == "critical":
            result.add_recommendation(
                Recommendation(
                    id=f"rec-backpressure-{output_id}",
                    type="operations",
                    priority="p1",
                    title=f"Resolve Critical Backpressure on {output_id}",
                    description=(
                        f"Destination '{output_id}' is experiencing severe backpressure "
                        f"({blocked_percent:.1f}% blocked). Immediate action recommended."
                    ),
                    rationale="Critical backpressure can lead to data loss or queue exhaustion.",
                    implementation_steps=[
                        "Check destination health and connectivity immediately",
                        f"Verify {output_type} destination is accepting connections",
                        "Review and increase batch sizes if appropriate",
                        "Enable persistent queuing to buffer during outages",
                        "Consider adding destination capacity or replicas"
                    ],
                    before_state=f"{blocked_percent:.1f}% events blocked",
                    after_state="Events flowing normally to destination",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Eliminates data buffering delays"
                    ),
                    implementation_effort="medium",
                    product_tags=["stream", "edge"]
                )
            )

    def _analyze_persistent_queues(
        self,
        outputs: List[Dict[str, Any]],
        pq_metrics: Dict[str, Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """Analyze persistent queue health."""
        pq_warnings = []
        pq_critical = []

        for output in outputs:
            output_id = output.get("id", "unknown")
            pq_enabled = output.get("pqEnabled", False)

            if not pq_enabled:
                continue

            pq_config = output.get("pq", {})
            max_size = pq_config.get("maxSize", 0)  # Usually in bytes or GB string
            max_size_bytes = self._parse_size_to_bytes(max_size)

            metrics = pq_metrics.get(output_id, {})
            current_size = metrics.get("queue_size_bytes", 0)

            # Calculate usage percentage
            if max_size_bytes > 0:
                usage_percent = (current_size / max_size_bytes) * 100
            else:
                usage_percent = 0

            current_size_gb = current_size / (1024 ** 3)

            # Check thresholds
            if usage_percent >= self.PQ_CRITICAL_PERCENT or current_size_gb >= self.PQ_SIZE_CRITICAL_GB:
                pq_critical.append(output_id)
                self._report_pq_issue(
                    output_id, current_size_gb, usage_percent, "critical", result
                )
            elif usage_percent >= self.PQ_WARNING_PERCENT or current_size_gb >= self.PQ_SIZE_WARNING_GB:
                pq_warnings.append(output_id)
                self._report_pq_issue(
                    output_id, current_size_gb, usage_percent, "warning", result
                )

        result.metadata["pq_warnings"] = len(pq_warnings)
        result.metadata["pq_critical"] = len(pq_critical)

    def _parse_size_to_bytes(self, size_value: Any) -> int:
        """Parse size value (bytes, string like '10GB') to bytes."""
        if isinstance(size_value, (int, float)):
            return int(size_value)

        if isinstance(size_value, str):
            size_value = size_value.strip().upper()
            # Order matters - check longer suffixes first
            multipliers = [
                ("TB", 1024 ** 4),
                ("GB", 1024 ** 3),
                ("MB", 1024 ** 2),
                ("KB", 1024),
                ("B", 1),
            ]
            for suffix, multiplier in multipliers:
                if size_value.endswith(suffix):
                    try:
                        number = float(size_value[:-len(suffix)])
                        return int(number * multiplier)
                    except ValueError:
                        return 0
        return 0

    def _report_pq_issue(
        self,
        output_id: str,
        current_size_gb: float,
        usage_percent: float,
        severity_level: str,
        result: AnalyzerResult
    ) -> None:
        """Report a persistent queue issue."""
        severity = "high" if severity_level == "critical" else "medium"

        result.add_finding(
            Finding(
                id=f"backpressure-pq-{output_id}",
                category="backpressure",
                severity=severity,
                title=f"Persistent Queue Filling: {output_id}",
                description=(
                    f"Persistent queue for '{output_id}' is at {usage_percent:.1f}% capacity "
                    f"({current_size_gb:.2f} GB). Queue may fill completely if destination "
                    f"backpressure continues."
                ),
                affected_components=["Persistent Queue", output_id],
                remediation_steps=[
                    "Check destination availability immediately",
                    "Monitor queue drain rate vs growth rate",
                    "Consider increasing queue size as temporary measure",
                    "Address root cause of destination backpressure",
                    "Review if destination scaling is needed"
                ],
                estimated_impact="Risk of data loss when queue fills",
                confidence_level="high",
                metadata={
                    "output_id": output_id,
                    "queue_size_gb": round(current_size_gb, 2),
                    "usage_percent": round(usage_percent, 2)
                }
            )
        )

        if severity_level == "critical":
            result.add_recommendation(
                Recommendation(
                    id=f"rec-pq-drain-{output_id}",
                    type="operations",
                    priority="p0",
                    title=f"Urgent: Drain Persistent Queue for {output_id}",
                    description=(
                        f"Persistent queue at {usage_percent:.1f}% ({current_size_gb:.2f} GB). "
                        "Immediate action needed to prevent data loss."
                    ),
                    rationale="When persistent queues fill, incoming data is lost.",
                    implementation_steps=[
                        "Immediately check destination connectivity",
                        "Verify destination is accepting connections",
                        "Monitor queue drain rate - should be positive",
                        "Consider temporarily routing traffic elsewhere",
                        "Scale destination if it cannot handle volume"
                    ],
                    before_state=f"Queue at {usage_percent:.1f}% capacity",
                    after_state="Queue draining, destination healthy",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Prevents data loss"
                    ),
                    implementation_effort="high",
                    product_tags=["stream", "edge"]
                )
            )

    def _analyze_http_retries(
        self,
        outputs: List[Dict[str, Any]],
        output_metrics: Dict[str, Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """Analyze HTTP destination retry patterns."""
        http_retry_issues = []

        # HTTP output types
        http_types = ["http", "splunk_hec", "elastic", "webhook", "datadog", "newrelic"]

        for output in outputs:
            output_id = output.get("id", "unknown")
            output_type = output.get("type", "").lower()

            # Only analyze HTTP-based outputs
            if not any(http_type in output_type for http_type in http_types):
                continue

            metrics = output_metrics.get(output_id, {})
            events_out = metrics.get("events_out", 0)
            errors_5xx = metrics.get("errors_5xx", 0)
            retries = metrics.get("retries", 0)

            if events_out > 0:
                # Calculate retry rate based on 5xx errors or explicit retries
                error_events = max(errors_5xx, retries)
                retry_rate = (error_events / events_out) * 100

                if retry_rate >= self.HTTP_RETRY_CRITICAL_PERCENT:
                    http_retry_issues.append(output_id)
                    self._report_http_retries(
                        output_id, output_type, retry_rate, errors_5xx, "critical", result
                    )
                elif retry_rate >= self.HTTP_RETRY_WARNING_PERCENT:
                    http_retry_issues.append(output_id)
                    self._report_http_retries(
                        output_id, output_type, retry_rate, errors_5xx, "warning", result
                    )

        result.metadata["http_outputs_with_retries"] = len(http_retry_issues)

    def _report_http_retries(
        self,
        output_id: str,
        output_type: str,
        retry_rate: float,
        errors_5xx: int,
        severity_level: str,
        result: AnalyzerResult
    ) -> None:
        """Report HTTP retry pattern finding."""
        severity = "high" if severity_level == "critical" else "medium"

        result.add_finding(
            Finding(
                id=f"backpressure-http-retries-{output_id}",
                category="backpressure",
                severity=severity,
                title=f"High Retry Rate: {output_id}",
                description=(
                    f"HTTP destination '{output_id}' ({output_type}) has a {retry_rate:.1f}% "
                    f"retry rate with {errors_5xx} 5xx errors. This indicates the destination "
                    f"is struggling to handle the load."
                ),
                affected_components=["Outputs", output_id],
                remediation_steps=[
                    "Check destination service health and logs",
                    "Review destination capacity and scaling",
                    "Check for rate limiting on the destination",
                    "Review batch size and timeout settings",
                    "Consider adding request queuing or load balancing"
                ],
                estimated_impact="Increased latency and destination load",
                confidence_level="high",
                metadata={
                    "output_id": output_id,
                    "output_type": output_type,
                    "retry_rate_percent": round(retry_rate, 2),
                    "errors_5xx": errors_5xx
                }
            )
        )

    def _predict_queue_exhaustion(
        self,
        outputs: List[Dict[str, Any]],
        pq_metrics: Dict[str, Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """Predict when persistent queues will exhaust based on growth trends."""
        exhaustion_predictions = []

        for output in outputs:
            output_id = output.get("id", "unknown")
            pq_enabled = output.get("pqEnabled", False)

            if not pq_enabled:
                continue

            pq_config = output.get("pq", {})
            max_size = pq_config.get("maxSize", 0)
            max_size_bytes = self._parse_size_to_bytes(max_size)

            metrics = pq_metrics.get(output_id, {})
            current_size = metrics.get("queue_size_bytes", 0)
            growth_rate = metrics.get("queue_growth_rate", 0)  # bytes per second
            drain_rate = metrics.get("queue_drain_rate", 0)

            # Net growth rate (positive = queue growing)
            net_growth_rate = growth_rate - drain_rate

            if net_growth_rate > 0 and max_size_bytes > current_size:
                # Calculate hours until exhaustion
                remaining_bytes = max_size_bytes - current_size
                seconds_to_full = remaining_bytes / net_growth_rate
                hours_to_full = seconds_to_full / 3600

                if hours_to_full <= self.EXHAUSTION_CRITICAL_HOURS:
                    exhaustion_predictions.append((output_id, hours_to_full, "critical"))
                    self._report_exhaustion_prediction(
                        output_id, hours_to_full, current_size, max_size_bytes, "critical", result
                    )
                elif hours_to_full <= self.EXHAUSTION_WARNING_HOURS:
                    exhaustion_predictions.append((output_id, hours_to_full, "warning"))
                    self._report_exhaustion_prediction(
                        output_id, hours_to_full, current_size, max_size_bytes, "warning", result
                    )

        result.metadata["exhaustion_predictions"] = len(exhaustion_predictions)

    def _report_exhaustion_prediction(
        self,
        output_id: str,
        hours_to_full: float,
        current_size: int,
        max_size: int,
        severity_level: str,
        result: AnalyzerResult
    ) -> None:
        """Report queue exhaustion prediction."""
        severity = "critical" if severity_level == "critical" else "high"
        current_gb = current_size / (1024 ** 3)
        max_gb = max_size / (1024 ** 3)

        result.add_finding(
            Finding(
                id=f"backpressure-exhaustion-{output_id}",
                category="backpressure",
                severity=severity,
                title=f"Queue Exhaustion Predicted: {output_id}",
                description=(
                    f"At current growth rate, persistent queue for '{output_id}' will "
                    f"fill completely in approximately {hours_to_full:.1f} hours. "
                    f"Current: {current_gb:.2f} GB / {max_gb:.2f} GB."
                ),
                affected_components=["Persistent Queue", output_id],
                remediation_steps=[
                    "Immediately investigate destination backpressure",
                    "Check destination health and capacity",
                    "Consider temporarily increasing queue size",
                    "Route traffic to alternative destinations if available",
                    "Prepare for potential data loss if queue fills"
                ],
                estimated_impact=f"Data loss in ~{hours_to_full:.1f} hours if unaddressed",
                confidence_level="medium",
                metadata={
                    "output_id": output_id,
                    "hours_to_exhaustion": round(hours_to_full, 2),
                    "current_size_gb": round(current_gb, 2),
                    "max_size_gb": round(max_gb, 2)
                }
            )
        )

        result.add_recommendation(
            Recommendation(
                id=f"rec-exhaustion-prevent-{output_id}",
                type="operations",
                priority="p0" if severity_level == "critical" else "p1",
                title=f"Prevent Queue Exhaustion: {output_id}",
                description=(
                    f"Queue predicted to fill in {hours_to_full:.1f} hours. "
                    "Take immediate action to prevent data loss."
                ),
                rationale="Proactive intervention prevents data loss.",
                implementation_steps=[
                    "Check destination connectivity and health",
                    "Identify root cause of backpressure",
                    "Scale destination if capacity limited",
                    "Consider data routing alternatives",
                    "Increase queue size as temporary buffer"
                ],
                before_state=f"Queue filling, {hours_to_full:.1f}h until full",
                after_state="Queue draining, destination healthy",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Prevents data loss"
                ),
                implementation_effort="high",
                product_tags=["stream", "edge"]
            )
        )

    def _add_summary_metadata(self, result: AnalyzerResult) -> None:
        """Add summary metadata to result."""
        backpressure_count = result.metadata.get("outputs_with_backpressure", 0)
        critical_count = result.metadata.get("outputs_critical_backpressure", 0)
        pq_warnings = result.metadata.get("pq_warnings", 0)
        pq_critical = result.metadata.get("pq_critical", 0)

        # Calculate overall backpressure health score
        total_issues = backpressure_count + critical_count + pq_warnings + pq_critical
        total_outputs = result.metadata.get("total_outputs", 1)

        if total_outputs > 0:
            health_ratio = 1 - (total_issues / total_outputs)
            result.metadata["backpressure_health_score"] = round(max(0, health_ratio * 100), 2)
        else:
            result.metadata["backpressure_health_score"] = 100.0

        # Overall status
        if critical_count > 0 or pq_critical > 0:
            result.metadata["overall_status"] = "critical"
        elif backpressure_count > 0 or pq_warnings > 0:
            result.metadata["overall_status"] = "warning"
        else:
            result.metadata["overall_status"] = "healthy"
