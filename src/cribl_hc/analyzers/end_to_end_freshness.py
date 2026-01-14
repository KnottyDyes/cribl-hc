"""
End-to-End Freshness Monitor Analyzer for Cribl Health Check.

Calculates the actual processing latency by measuring the delta between
event creation time and output time, identifying silent pipeline lag
issues that affect data freshness.
"""

import time
from collections import defaultdict
from statistics import mean, median
from typing import Any, Optional

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.utils.logger import get_logger


class EndToEndFreshnessAnalyzer(BaseAnalyzer):
    """
    Analyzer for monitoring end-to-end data freshness and pipeline latency.

    Phase B - Enterprise Operations

    Measures the actual time events spend in the pipeline from input to output,
    detecting processing bottlenecks and latency issues that affect data freshness.
    """

    # Thresholds in seconds
    HIGH_LATENCY_THRESHOLD = 30  # 30 seconds
    CRITICAL_LATENCY_THRESHOLD = 120  # 2 minutes
    MIN_SAMPLES_FOR_ANALYSIS = 10

    def __init__(self) -> None:
        """Initialize the end-to-end freshness analyzer."""
        super().__init__()
        self.log = get_logger(__name__)

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "end_to_end_freshness"

    @property
    def supported_products(self) -> list[str]:
        """End-to-end freshness applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Measures end-to-end pipeline latency from input to output time"

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls: event sampling at multiple points."""
        return 2  # Input and output sampling

    def get_required_permissions(self) -> list[str]:
        """Return required API permissions."""
        return ["read:system", "execute:capture"]

    async def post_analyze_cleanup(self) -> None:
        """Optional cleanup after analysis completes."""
        pass

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform end-to-end freshness analysis.

        Strategy:
        1. Sample events at output points (with input timestamps)
        2. Calculate processing latency (output_time - input_time)
        3. Identify bottlenecks and high-latency pipelines
        4. Generate findings with pipeline-specific insights
        """
        result = self.create_result()

        try:
            # Sample events from outputs to measure end-to-end latency
            output_events = await client.capture_events(
                filter_expr="true", max_events=100, duration=10, level=1
            )

            result.metadata["events_sampled"] = len(output_events)

            if len(output_events) < self.MIN_SAMPLES_FOR_ANALYSIS:
                result.add_finding(
                    self.create_finding(
                        id="e2e-freshness-insufficient-data",
                        title="Insufficient Data for End-to-End Analysis",
                        description=f"Only {len(output_events)} events sampled, need at least {self.MIN_SAMPLES_FOR_ANALYSIS} for meaningful latency analysis.",
                        severity="info",
                        category="performance",
                        confidence_level="medium",
                        affected_components=["pipeline:processing"],
                        metadata={"events_sampled": len(output_events)},
                    )
                )
                return result

            # Analyze latency patterns
            latency_analysis = self._analyze_latency_patterns(output_events)

            # Detect high latency issues
            latency_findings = self._detect_high_latency(latency_analysis, result)

            # Detect pipeline bottlenecks
            bottleneck_findings = self._detect_pipeline_bottlenecks(latency_analysis, result)

            # Add all findings
            for finding in latency_findings + bottleneck_findings:
                result.add_finding(finding)

            # Summary finding
            self._add_summary_finding(result, latency_analysis)

        except Exception as e:
            self.log.error("end_to_end_freshness_analysis_failed", error=str(e))
            result.success = False
            result.error = str(e)

        return result

    def _analyze_latency_patterns(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze latency patterns across events and pipelines."""
        current_time = time.time()

        # Group events by pipeline for analysis
        pipeline_latencies = defaultdict(list)
        source_latencies = defaultdict(list)
        all_latencies = []

        events_with_timestamps = 0

        for event in events:
            # Try to get input timestamp (when event entered the system)
            input_time = self._extract_input_timestamp(event)
            output_time = event.get("_time", current_time)

            if input_time is None:
                # If no explicit input time, estimate based on event age
                # This is less accurate but better than nothing
                event_age = current_time - output_time
                if event_age > 0:
                    input_time = output_time - min(
                        event_age * 0.1, 60
                    )  # Estimate 10% processing time, max 1min
                else:
                    continue

            latency = output_time - input_time

            # Skip unrealistic latencies (negative or extremely high)
            if latency < 0 or latency > 3600:  # 1 hour max
                continue

            events_with_timestamps += 1
            all_latencies.append(latency)

            # Group by pipeline
            pipeline = event.get("cribl_pipe", event.get("pipeline", "unknown"))
            pipeline_latencies[pipeline].append(latency)

            # Group by source
            source = event.get("source", event.get("input", "unknown"))
            source_latencies[source].append(latency)

        return {
            "events_with_timestamps": events_with_timestamps,
            "all_latencies": all_latencies,
            "pipeline_latencies": dict(pipeline_latencies),
            "source_latencies": dict(source_latencies),
            "current_time": current_time,
        }

    def _extract_input_timestamp(self, event: dict[str, Any]) -> Optional[float]:
        """Extract the input timestamp from an event."""
        # Look for common input timestamp fields
        input_time_fields = [
            "input_time",
            "_input_time",
            "ingest_time",
            "_ingest_time",
            "received_at",
            "arrival_time",
            "cribl_input_time",
        ]

        for field in input_time_fields:
            if field in event:
                try:
                    return float(event[field])
                except (ValueError, TypeError):
                    continue

        # Look for time differences in field names
        for key, value in event.items():
            if "time" in key.lower() and "input" in key.lower():
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue

        # If no explicit input time, we'll estimate in the calling function
        return None

    def _detect_high_latency(
        self, latency_analysis: dict[str, Any], result: AnalyzerResult
    ) -> list[Any]:
        """Detect events with high end-to-end latency."""
        findings = []

        all_latencies = latency_analysis["all_latencies"]
        if not all_latencies:
            return findings

        # Calculate statistics
        avg_latency = mean(all_latencies)
        median_latency = median(all_latencies)
        max_latency = max(all_latencies)
        high_latency_count = len(
            [latency for latency in all_latencies if latency > self.HIGH_LATENCY_THRESHOLD]
        )
        critical_latency_count = len(
            [latency for latency in all_latencies if latency > self.CRITICAL_LATENCY_THRESHOLD]
        )

        result.metadata.update(
            {
                "avg_latency_seconds": round(avg_latency, 2),
                "median_latency_seconds": round(median_latency, 2),
                "max_latency_seconds": round(max_latency, 2),
                "high_latency_events": high_latency_count,
                "critical_latency_events": critical_latency_count,
            }
        )

        # Flag critical latency issues
        if critical_latency_count > 0:
            severity = "critical" if critical_latency_count > len(all_latencies) * 0.1 else "high"

            findings.append(
                self.create_finding(
                    id="e2e-freshness-critical-latency",
                    title="Critical End-to-End Latency Detected",
                    description=f"{critical_latency_count} events ({critical_latency_count / len(all_latencies):.1%}) "
                    f"took longer than {self.CRITICAL_LATENCY_THRESHOLD}s to process. "
                    f"Max latency: {max_latency:.1f}s, Average: {avg_latency:.1f}s.",
                    severity=severity,
                    category="performance",
                    confidence_level="high",
                    affected_components=["pipeline:processing"],
                    estimated_impact="Severely delayed data delivery, SLA breaches, real-time processing failures",
                    remediation_steps=[
                        "Identify which pipelines are causing the delays",
                        "Check for pipeline backpressure and queue buildup",
                        "Review resource utilization (CPU, memory) on workers",
                        "Consider scaling worker groups or optimizing pipeline functions",
                        "Monitor for persistent high latency trends",
                    ],
                    metadata={
                        "critical_events": critical_latency_count,
                        "total_events": len(all_latencies),
                        "max_latency": round(max_latency, 2),
                        "avg_latency": round(avg_latency, 2),
                        "threshold": self.CRITICAL_LATENCY_THRESHOLD,
                    },
                )
            )

        # Flag high latency issues (less critical than critical threshold)
        elif high_latency_count > len(all_latencies) * 0.05:  # 5% of events
            findings.append(
                self.create_finding(
                    id="e2e-freshness-high-latency",
                    title="High End-to-End Latency Detected",
                    description=f"{high_latency_count} events ({high_latency_count / len(all_latencies):.1%}) "
                    f"took longer than {self.HIGH_LATENCY_THRESHOLD}s to process. "
                    f"Average latency: {avg_latency:.1f}s.",
                    severity="high",
                    category="performance",
                    confidence_level="high",
                    affected_components=["pipeline:processing"],
                    estimated_impact="Delayed data delivery, potential SLA concerns",
                    remediation_steps=[
                        "Monitor pipeline performance metrics",
                        "Check for intermittent bottlenecks",
                        "Review recent pipeline configuration changes",
                        "Consider optimizing expensive functions (regex, lookups)",
                    ],
                    metadata={
                        "high_latency_events": high_latency_count,
                        "total_events": len(all_latencies),
                        "avg_latency": round(avg_latency, 2),
                        "threshold": self.HIGH_LATENCY_THRESHOLD,
                    },
                )
            )

        return findings

    def _detect_pipeline_bottlenecks(
        self, latency_analysis: dict[str, Any], result: AnalyzerResult
    ) -> list[Any]:
        """Detect pipelines with consistently high latency."""
        findings = []

        pipeline_latencies = latency_analysis["pipeline_latencies"]

        # Calculate overall average for comparison
        all_latencies = latency_analysis["all_latencies"]
        if not all_latencies:
            return findings

        overall_avg = mean(all_latencies)

        # Find pipelines with significantly higher latency
        bottleneck_pipelines = []
        for pipeline, latencies in pipeline_latencies.items():
            if len(latencies) < 3:  # Need minimum samples
                continue

            pipeline_avg = mean(latencies)
            pipeline_max = max(latencies)

            # Pipeline is bottleneck if it's 3x slower than average
            if pipeline_avg > overall_avg * 3:
                bottleneck_pipelines.append(
                    {
                        "pipeline": pipeline,
                        "avg_latency": pipeline_avg,
                        "max_latency": pipeline_max,
                        "event_count": len(latencies),
                        "slowdown_factor": pipeline_avg / overall_avg,
                    }
                )

        # Sort by severity (highest latency first)
        bottleneck_pipelines.sort(key=lambda x: x["avg_latency"], reverse=True)

        for bottleneck in bottleneck_pipelines[:5]:  # Top 5 bottlenecks
            severity = "critical" if bottleneck["slowdown_factor"] > 5 else "high"

            findings.append(
                self.create_finding(
                    id=f"e2e-freshness-pipeline-bottleneck-{bottleneck['pipeline']}",
                    title=f"Pipeline Bottleneck: {bottleneck['pipeline']}",
                    description=f"Pipeline '{bottleneck['pipeline']}' has {bottleneck['slowdown_factor']:.1f}x "
                    f"higher latency than average ({bottleneck['avg_latency']:.1f}s vs {overall_avg:.1f}s). "
                    f"Max latency: {bottleneck['max_latency']:.1f}s across {bottleneck['event_count']} events.",
                    severity=severity,
                    category="performance",
                    confidence_level="high",
                    affected_components=[f"pipeline:{bottleneck['pipeline']}"],
                    estimated_impact="Delayed processing for events through this pipeline, downstream data freshness issues",
                    remediation_steps=[
                        f"Analyze pipeline '{bottleneck['pipeline']}' functions for performance bottlenecks",
                        "Check for expensive operations (complex regex, large lookups)",
                        "Review function order - move filtering earlier in pipeline",
                        "Consider splitting complex pipelines into smaller ones",
                        "Monitor resource usage during high latency periods",
                    ],
                    metadata={
                        "pipeline": bottleneck["pipeline"],
                        "avg_latency": round(bottleneck["avg_latency"], 2),
                        "max_latency": round(bottleneck["max_latency"], 2),
                        "overall_avg": round(overall_avg, 2),
                        "slowdown_factor": round(bottleneck["slowdown_factor"], 2),
                        "event_count": bottleneck["event_count"],
                    },
                )
            )

        return findings

    def _add_summary_finding(
        self, result: AnalyzerResult, latency_analysis: dict[str, Any]
    ) -> None:
        """Add summary finding for end-to-end freshness analysis."""
        all_latencies = latency_analysis["all_latencies"]
        events_with_timestamps = latency_analysis["events_with_timestamps"]

        if not all_latencies:
            result.add_finding(
                self.create_finding(
                    id="e2e-freshness-no-data",
                    title="End-to-End Freshness: No Data Available",
                    description="Unable to measure end-to-end latency - no events with timing information found.",
                    severity="info",
                    category="performance",
                    confidence_level="low",
                    affected_components=["pipeline:processing"],
                )
            )
            return

        avg_latency = mean(all_latencies)
        max_latency = max(all_latencies)
        healthy_events = len(
            [latency for latency in all_latencies if latency <= self.HIGH_LATENCY_THRESHOLD]
        )

        # Determine overall health
        health_percentage = (healthy_events / len(all_latencies)) * 100

        if health_percentage >= 95:
            severity = "info"
            status = "Excellent"
            description = f"End-to-end freshness is healthy. {health_percentage:.1f}% of events processed within {self.HIGH_LATENCY_THRESHOLD}s."
        elif health_percentage >= 80:
            severity = "low"
            status = "Good"
            description = f"End-to-end freshness is acceptable. {health_percentage:.1f}% of events processed within {self.HIGH_LATENCY_THRESHOLD}s."
        elif health_percentage >= 50:
            severity = "medium"
            status = "Needs Attention"
            description = f"End-to-end freshness issues detected. Only {health_percentage:.1f}% of events processed within {self.HIGH_LATENCY_THRESHOLD}s."
        else:
            severity = "high"
            status = "Critical Issues"
            description = f"Severe end-to-end freshness problems. Only {health_percentage:.1f}% of events processed within {self.HIGH_LATENCY_THRESHOLD}s."

        result.add_finding(
            self.create_finding(
                id="e2e-freshness-summary",
                title=f"End-to-End Freshness: {status}",
                description=f"{description} Average latency: {avg_latency:.1f}s, Max: {max_latency:.1f}s.",
                severity=severity,
                category="performance",
                confidence_level="high",
                affected_components=["pipeline:processing"],
                metadata={
                    "events_analyzed": len(all_latencies),
                    "events_with_timestamps": events_with_timestamps,
                    "avg_latency_seconds": round(avg_latency, 2),
                    "max_latency_seconds": round(max_latency, 2),
                    "healthy_percentage": round(health_percentage, 1),
                    "healthy_events": healthy_events,
                },
            )
        )
