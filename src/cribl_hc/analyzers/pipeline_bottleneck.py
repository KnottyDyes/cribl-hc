"""
Pipeline Bottleneck Analyzer for Cribl Health Check.

Analyzes pipelines for throughput bottlenecks and data loss issues.

Identifies:
- Silent failures (input > 0, output = 0)
- Unexpected drop rates vs configured
- Processing time anomalies
- Throughput cliffs (unbalanced load distribution)

Priority: P1 (High Impact - Production Operations)
"""

from datetime import datetime
from statistics import mean, stdev
from typing import Any, Literal

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.core.metrics_collector import MetricsCollector
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class PipelineBottleneckAnalyzer(BaseAnalyzer):
    """
    Analyzer for pipeline throughput bottlenecks and data loss.

    Identifies:
    - Silent failures: data entering pipeline but nothing leaving
    - Unexpected drop rates: actual drop rate exceeds configured threshold
    - Processing time anomalies: pipeline taking longer than baseline
    - Throughput cliffs: one pipeline handles >> mean throughput

    Priority: P1 (High Impact - addresses production data loss and performance issues)
    """

    PROCESSING_TIME_ANOMALY_PERCENT = 50.0
    THROUGHPUT_CLIFF_STDEV_THRESHOLD = 1.5
    DROP_RATE_VARIANCE_PERCENT = 20.0
    DEFAULT_EXPECTED_DROP_RATE = 5.0
    DEFAULT_BASELINE_PROCESSING_TIME_MS = 100.0

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "pipeline_bottleneck"

    @property
    def supported_products(self) -> list[str]:
        """Pipeline bottleneck analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Identifies pipeline throughput bottlenecks and data loss issues"

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls: pipelines(1) + metrics(1) = 2."""
        return 2

    def get_required_permissions(self) -> list[str]:
        """Return required API permissions."""
        return ["read:pipelines", "read:metrics"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze all pipelines for bottlenecks.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with pipeline bottleneck findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            log.info("pipeline_bottleneck_analysis_started")

            pipelines_data = await client.get_pipelines()

            if isinstance(pipelines_data, list):
                pipelines = {p.get("id", f"pipe-{i}"): p for i, p in enumerate(pipelines_data)}
            else:
                pipelines = pipelines_data or {}

            metrics = await client.get_metrics(time_range="1h")

            collector = MetricsCollector()
            normalized = collector.normalize_metrics(metrics)
            ratios = collector.calculate_event_ratios(normalized)

            pipeline_metrics = normalized.get("pipelines", {})

            result.metadata.update(
                {
                    "total_pipelines": len(pipelines),
                    "pipelines_analyzed": len(pipeline_metrics),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                }
            )

            if not pipelines:
                result.add_finding(
                    Finding(
                        id="pipeline_bottleneck-no_pipelines",
                        category="pipeline_bottleneck",
                        severity="info",
                        title="No Pipelines Configured",
                        description="No pipelines found for bottleneck analysis.",
                        affected_components=["Pipelines"],
                        confidence_level="high",
                        metadata={},
                    )
                )
                result.success = True
                return result

            if not pipeline_metrics:
                result.add_finding(
                    Finding(
                        id="pipeline_bottleneck-metrics_unavailable",
                        category="pipeline_bottleneck",
                        severity="info",
                        title="Pipeline Metrics Unavailable",
                        description=(
                            "Pipeline metrics are not available for this deployment. "
                            "Bottleneck analysis requires runtime metrics data. "
                            "This is typically unavailable via API for Cribl Cloud deployments."
                        ),
                        affected_components=["Monitoring", "Metrics"],
                        remediation_steps=[
                            "Use Cribl's built-in monitoring dashboard",
                            "Check infrastructure-level metrics (CPU, memory)",
                            "For Cribl Cloud, enable real-time monitoring via the UI",
                        ],
                        estimated_impact="Limited visibility into pipeline performance",
                        confidence_level="high",
                        metadata={"deployment_type": "cloud" if client.is_cloud else "self-hosted"},
                    )
                )
                result.success = True
                return result

            for pipeline_id, pipeline_config in pipelines.items():
                self._analyze_pipeline(
                    pipeline_id,
                    pipeline_config,
                    pipeline_metrics.get(pipeline_id, {}),
                    ratios.get(pipeline_id, {}),
                    result,
                )

            self._check_throughput_cliff(pipeline_metrics, result)

            self._score_analysis(result)

            result.success = True
            log.info(
                "pipeline_bottleneck_analysis_completed",
                findings=len(result.findings),
                recommendations=len(result.recommendations),
            )

        except Exception as e:
            log.error("pipeline_bottleneck_analysis_failed", error=str(e))
            result.success = False
            result.error = f"Pipeline bottleneck analysis failed: {str(e)}"

        return result

    def _analyze_pipeline(
        self,
        pipeline_id: str,
        config: dict[str, Any],
        metrics: dict[str, Any],
        ratios: dict[str, float],
        result: AnalyzerResult,
    ) -> None:
        """Analyze single pipeline for all 4 check types."""
        self._check_silent_failure(pipeline_id, config, metrics, result)
        self._check_drop_rate_variance(pipeline_id, config, metrics, ratios, result)
        self._check_processing_time_anomaly(pipeline_id, config, metrics, result)

    def _check_silent_failure(
        self,
        pipeline_id: str,
        config: dict[str, Any],
        metrics: dict[str, Any],
        result: AnalyzerResult,
    ) -> None:
        """Check for silent failures (CRITICAL): in > 0, out = 0, not disabled."""
        in_events = metrics.get("in_events", 0)
        out_events = metrics.get("out_events", 0)
        is_disabled = config.get("disabled", False)

        if is_disabled:
            return

        if in_events > 0 and out_events == 0:
            finding_id = f"pipeline_bottleneck-silent_failure-{pipeline_id}"

            result.add_finding(
                Finding(
                    id=finding_id,
                    category="pipeline_bottleneck",
                    severity="critical",
                    title=f"Silent Failure: {pipeline_id}",
                    description=(
                        f"Pipeline '{pipeline_id}' received {in_events:,} events but produced "
                        f"zero output events. Data is entering the pipeline but nothing is leaving. "
                        f"This indicates a critical data loss issue."
                    ),
                    affected_components=[f"pipeline:{pipeline_id}"],
                    remediation_steps=[
                        "Check pipeline logs for errors or exceptions",
                        "Verify all pipeline functions are executing correctly",
                        "Check if output destinations are disabled or misconfigured",
                        "Review filter rules to ensure events are not being dropped unintentionally",
                        "Test pipeline with sample data in interactive mode",
                    ],
                    estimated_impact=(
                        "Complete data loss from this pipeline. No events reaching destinations."
                    ),
                    confidence_level="high",
                    metadata={
                        "in_events": in_events,
                        "out_events": out_events,
                        "drop_rate": 1.0,
                    },
                )
            )

            result.add_recommendation(
                Recommendation(
                    id=f"rec-silent_failure-{pipeline_id}",
                    type="emergency",
                    priority="p0",
                    title=f"Investigate Silent Failure in {pipeline_id}",
                    description=(
                        f"Pipeline '{pipeline_id}' is experiencing a silent failure where all "
                        f"input events are being dropped. Immediate investigation is required."
                    ),
                    rationale=(
                        "Silent failures represent complete data loss and require immediate remediation"
                    ),
                    implementation_steps=[
                        f"Open pipeline '{pipeline_id}' in Cribl UI",
                        "Review pipeline function order and configuration",
                        "Check for null output functions or disabled outputs",
                        "Review last 24 hours of pipeline logs for errors",
                        "Test with sample data to reproduce issue",
                        "Fix identified issues and re-enable pipeline",
                    ],
                    before_state=f"Pipeline '{pipeline_id}' silently dropping all {in_events:,} events",
                    after_state="Pipeline successfully processes events through to outputs",
                    impact_estimate=ImpactEstimate(
                        performance_improvement="Restore 100% data flow",
                        cost_savings_annual=None,
                        storage_reduction_gb=None,
                        time_to_implement=None,
                    ),
                    implementation_effort="medium",
                    related_findings=[finding_id],
                    product_tags=["stream", "edge"],
                )
            )

    def _check_drop_rate_variance(
        self,
        pipeline_id: str,
        config: dict[str, Any],
        metrics: dict[str, Any],
        ratios: dict[str, float],
        result: AnalyzerResult,
    ) -> None:
        """Check for unexpected drop rate variance (HIGH/MEDIUM)."""
        in_events = metrics.get("in_events", 0)

        if in_events == 0:
            return

        drop_ratio = ratios.get("drop_ratio", 0.0)
        actual_drop_rate = drop_ratio * 100.0

        expected_drop_rate = self._get_expected_drop_rate(config)

        drop_rate_difference = actual_drop_rate - expected_drop_rate

        if drop_rate_difference > 0:
            variance_percent = (
                (drop_rate_difference / expected_drop_rate * 100.0)
                if expected_drop_rate > 0
                else 100.0
            )

            if variance_percent > self.DROP_RATE_VARIANCE_PERCENT:
                severity: Literal["critical", "high", "medium", "low", "info"] = "high"
                priority: Literal["p0", "p1", "p2", "p3"] = "p1"
                variance_desc = "significantly exceeds"
            else:
                severity = "medium"
                priority = "p2"
                variance_desc = "slightly exceeds"

            finding_id = f"pipeline_bottleneck-drop_variance-{pipeline_id}"

            result.add_finding(
                Finding(
                    id=finding_id,
                    category="pipeline_bottleneck",
                    severity=severity,
                    title=f"Drop Rate Variance: {pipeline_id}",
                    description=(
                        f"Pipeline '{pipeline_id}' drop rate ({actual_drop_rate:.2f}%) "
                        f"{variance_desc} expected ({expected_drop_rate:.2f}%). "
                        f"Actual variance: {variance_percent:.1f}%. This may indicate unexpected filtering "
                        f"or processing errors beyond configured drop rules."
                    ),
                    affected_components=[f"pipeline:{pipeline_id}"],
                    remediation_steps=[
                        "Review configured filter rules and their expected drop rates",
                        "Check pipeline logs for errors or exceptions",
                        "Verify filter function conditions are as intended",
                        "Check if new filters or rules were recently added",
                        "Review data quality and schema changes upstream",
                    ],
                    estimated_impact=f"Losing {drop_rate_difference:.2f}% more events than expected",
                    confidence_level="high",
                    metadata={
                        "in_events": in_events,
                        "drop_events": metrics.get("drop_events", 0),
                        "actual_drop_rate_percent": actual_drop_rate,
                        "expected_drop_rate_percent": expected_drop_rate,
                        "variance_percent": variance_percent,
                    },
                )
            )

            result.add_recommendation(
                Recommendation(
                    id=f"rec-drop_variance-{pipeline_id}",
                    type="troubleshooting",
                    priority=priority,
                    title=f"Investigate Drop Rate Variance in {pipeline_id}",
                    description=(
                        f"Pipeline '{pipeline_id}' is dropping {variance_percent:.1f}% more events "
                        f"than configured. Review filters and rules."
                    ),
                    rationale="Unexpected drops indicate misconfiguration or unintended data loss",
                    implementation_steps=[
                        f"Open pipeline '{pipeline_id}' in Cribl UI",
                        "Review all filter functions and their conditions",
                        "Check recent changes to pipeline configuration",
                        "Analyze sample events to see what's being dropped",
                        "Compare actual drop rate with expected",
                        "Adjust filters if necessary",
                    ],
                    before_state=f"Drop rate: {actual_drop_rate:.2f}% (exceeds {expected_drop_rate:.2f}% by {variance_percent:.1f}%)",
                    after_state=f"Drop rate: ~{expected_drop_rate:.2f}% (matches configured filters)",
                    impact_estimate=ImpactEstimate(
                        performance_improvement=f"Recover {drop_rate_difference:.2f}% of dropped events",
                        cost_savings_annual=None,
                        storage_reduction_gb=None,
                        time_to_implement=None,
                    ),
                    implementation_effort="low",
                    related_findings=[finding_id],
                    product_tags=["stream", "edge"],
                )
            )

    def _check_processing_time_anomaly(
        self,
        pipeline_id: str,
        config: dict[str, Any],
        metrics: dict[str, Any],
        result: AnalyzerResult,
    ) -> None:
        """Check for processing time anomalies (MEDIUM)."""
        processing_time_ms = metrics.get("processing_time_ms", 0.0)

        if processing_time_ms <= 0:
            return

        baseline_ms = self._get_baseline_processing_time(config)

        time_increase_percent = (
            ((processing_time_ms - baseline_ms) / baseline_ms * 100.0) if baseline_ms > 0 else 0.0
        )

        if time_increase_percent >= self.PROCESSING_TIME_ANOMALY_PERCENT:
            finding_id = f"pipeline_bottleneck-time_anomaly-{pipeline_id}"

            result.add_finding(
                Finding(
                    id=finding_id,
                    category="pipeline_bottleneck",
                    severity="medium",
                    title=f"Processing Time Anomaly: {pipeline_id}",
                    description=(
                        f"Pipeline '{pipeline_id}' processing time ({processing_time_ms:.2f}ms) "
                        f"exceeds baseline ({baseline_ms:.2f}ms) by {time_increase_percent:.1f}%. "
                        f"This may indicate downstream backpressure, CPU contention, or GC pauses."
                    ),
                    affected_components=[f"pipeline:{pipeline_id}"],
                    remediation_steps=[
                        "Check downstream destination health and capacity",
                        "Review worker CPU and memory utilization",
                        "Check for GC (garbage collection) pauses in worker logs",
                        "Analyze pipeline function performance",
                        "Consider scaling workers if CPU is high",
                        "Check network latency to destinations",
                    ],
                    estimated_impact=(
                        f"Pipeline latency increased by {time_increase_percent:.1f}%, affecting throughput"
                    ),
                    confidence_level="medium",
                    metadata={
                        "processing_time_ms": processing_time_ms,
                        "baseline_ms": baseline_ms,
                        "increase_percent": time_increase_percent,
                    },
                )
            )

            result.add_recommendation(
                Recommendation(
                    id=f"rec-time_anomaly-{pipeline_id}",
                    type="optimization",
                    priority="p2",
                    title=f"Investigate Processing Time Spike in {pipeline_id}",
                    description=(
                        f"Pipeline '{pipeline_id}' processing time is {time_increase_percent:.1f}% "
                        f"above baseline. Check downstream and infrastructure resources."
                    ),
                    rationale="Processing time spikes affect throughput and event delivery latency",
                    implementation_steps=[
                        f"Check processing time trend for pipeline '{pipeline_id}'",
                        "Review worker CPU/memory metrics at time of spike",
                        "Check destination health and connectivity",
                        "Review pipeline function complexity and optimization",
                        "Enable function timing instrumentation if available",
                        "Monitor for recurring patterns",
                    ],
                    before_state=f"Processing time: {processing_time_ms:.2f}ms (baseline: {baseline_ms:.2f}ms)",
                    after_state=f"Processing time: ~{baseline_ms:.2f}ms or below",
                    impact_estimate=ImpactEstimate(
                        performance_improvement=f"Reduce processing latency by {time_increase_percent:.1f}%",
                        cost_savings_annual=None,
                        storage_reduction_gb=None,
                        time_to_implement=None,
                    ),
                    implementation_effort="medium",
                    related_findings=[finding_id],
                    product_tags=["stream", "edge"],
                )
            )

    def _check_throughput_cliff(
        self,
        pipeline_metrics: dict[str, dict[str, Any]],
        result: AnalyzerResult,
    ) -> None:
        """Check for throughput cliffs (MEDIUM)."""
        if not pipeline_metrics or len(pipeline_metrics) < 2:
            return

        throughputs = []
        pipeline_ids = []

        for pipeline_id, metrics in pipeline_metrics.items():
            in_events = metrics.get("in_events", 0)
            if in_events > 0:
                throughputs.append(in_events)
                pipeline_ids.append(pipeline_id)

        if len(throughputs) < 2:
            return

        mean_throughput = mean(throughputs)
        try:
            stdev_throughput = stdev(throughputs) if len(throughputs) > 1 else 0
        except (ValueError, ZeroDivisionError):
            stdev_throughput = 0

        if stdev_throughput == 0:
            return

        for pipeline_id, throughput in zip(pipeline_ids, throughputs):
            z_score = (
                (throughput - mean_throughput) / stdev_throughput if stdev_throughput > 0 else 0
            )

            if z_score >= self.THROUGHPUT_CLIFF_STDEV_THRESHOLD:
                multiple = throughput / mean_throughput

                finding_id = f"pipeline_bottleneck-throughput_cliff-{pipeline_id}"

                result.add_finding(
                    Finding(
                        id=finding_id,
                        category="pipeline_bottleneck",
                        severity="medium",
                        title=f"Throughput Cliff: {pipeline_id}",
                        description=(
                            f"Pipeline '{pipeline_id}' handles {multiple:.1f}x the mean throughput "
                            f"({throughput:,} events vs {mean_throughput:,.0f} mean). "
                            f"This suggests uneven load distribution, potentially due to filter rules "
                            f"directing traffic or misconfiguration."
                        ),
                        affected_components=[f"pipeline:{pipeline_id}"],
                        remediation_steps=[
                            "Review route filter rules that direct traffic to this pipeline",
                            "Check if filter conditions are too broad or too specific",
                            "Consider splitting pipeline or distributing load across multiple pipelines",
                            "Verify that filter rules on other pipelines are correctly configured",
                            "Monitor load distribution after making changes",
                        ],
                        estimated_impact=(
                            "Unbalanced load may cause this pipeline to bottleneck "
                            "while others are underutilized"
                        ),
                        confidence_level="high",
                        metadata={
                            "throughput": throughput,
                            "mean_throughput": mean_throughput,
                            "stdev_throughput": stdev_throughput,
                            "z_score": z_score,
                            "multiple_of_mean": multiple,
                        },
                    )
                )

                result.add_recommendation(
                    Recommendation(
                        id=f"rec-throughput_cliff-{pipeline_id}",
                        type="optimization",
                        priority="p2",
                        title=f"Rebalance Load for {pipeline_id}",
                        description=(
                            f"Pipeline '{pipeline_id}' is handling {multiple:.1f}x the average throughput. "
                            f"Consider rebalancing load across pipelines."
                        ),
                        rationale="Uneven load distribution causes hot spots and potential bottlenecks",
                        implementation_steps=[
                            f"Review all routes feeding into pipeline '{pipeline_id}'",
                            "Analyze filter conditions on all pipelines",
                            "Consider splitting high-throughput pipeline",
                            "Create new pipeline for subset of traffic",
                            "Adjust route filters to balance load",
                            "Monitor throughput distribution after changes",
                        ],
                        before_state=f"Pipeline '{pipeline_id}' handling {throughput:,} events ({multiple:.1f}x mean)",
                        after_state=f"Throughput balanced across pipelines (~{mean_throughput:,.0f} per pipeline)",
                        impact_estimate=ImpactEstimate(
                            performance_improvement=(
                                f"Distribute load evenly, reduce hot spot on '{pipeline_id}'"
                            ),
                            cost_savings_annual=None,
                            storage_reduction_gb=None,
                            time_to_implement=None,
                        ),
                        implementation_effort="medium",
                        related_findings=[finding_id],
                        product_tags=["stream", "edge"],
                    )
                )

    def _get_expected_drop_rate(self, config: dict[str, Any]) -> float:
        """Extract expected drop rate from pipeline configuration."""
        expected_drop = config.get("expectedDropRate", self.DEFAULT_EXPECTED_DROP_RATE)

        try:
            return float(expected_drop)
        except (ValueError, TypeError):
            return self.DEFAULT_EXPECTED_DROP_RATE

    def _get_baseline_processing_time(self, config: dict[str, Any]) -> float:
        """Extract baseline processing time from pipeline configuration."""
        baseline = config.get("baselineProcessingTimeMs", self.DEFAULT_BASELINE_PROCESSING_TIME_MS)

        try:
            return float(baseline)
        except (ValueError, TypeError):
            return self.DEFAULT_BASELINE_PROCESSING_TIME_MS

    def _score_analysis(self, result: AnalyzerResult) -> None:
        """Score overall analysis and update metadata."""
        critical_findings = len(result.get_critical_findings())
        high_findings = len(result.get_high_findings())

        if critical_findings > 0:
            overall_status = "critical"
        elif high_findings > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        result.metadata.update(
            {
                "overall_status": overall_status,
                "critical_findings": critical_findings,
                "high_findings": high_findings,
                "total_findings": len(result.findings),
                "total_recommendations": len(result.recommendations),
            }
        )
