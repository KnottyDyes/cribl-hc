"""
Route Performance Analyzer for Cribl Health Check.

Analyzes route throughput, latency, error rates, and traffic distribution
to identify performance bottlenecks and optimization opportunities.

Priority: P2 (Medium Impact - Performance Optimization)
"""

import statistics
from datetime import datetime
from typing import Any, Literal

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class RoutePerformanceAnalyzer(BaseAnalyzer):
    """
    Analyzer for route performance and traffic distribution.

    Identifies:
    - Routes with zero throughput (underutilized)
    - Routes with high latency (p99 spikes)
    - Routes with high error rates
    - Pipelines overloaded by specific routes
    - Imbalanced traffic distribution across routes
    """

    THROUGHPUT_SPIKE_THRESHOLD = 2.0
    LATENCY_P99_HIGH_MS = 5000.0
    LATENCY_P99_CRITICAL_MS = 10000.0
    ERROR_RATE_HIGH_PERCENT = 5.0
    ERROR_RATE_CRITICAL_PERCENT = 10.0
    PIPELINE_OVERLOAD_EVENTS_SEC = 5000.0
    BALANCE_CV_THRESHOLD = 0.5

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "route_performance"

    @property
    def supported_products(self) -> list[str]:
        """Route performance analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Analyzes route throughput, latency, error rates, and traffic balance"

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls: routes(1) + metrics(1) + pipelines(1) = 3."""
        return 3

    def get_required_permissions(self) -> list[str]:
        """Return required API permissions."""
        return [
            "read:routes",
            "read:pipelines",
            "read:metrics",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze route performance across all routes.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with route performance findings and recommendations
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            log.info("route_performance_analysis_started")

            routes = await client.get_routes()
            pipelines = await client.get_pipelines()
            metrics = await client.get_metrics(time_range="1h")

            if not metrics:
                self._report_metrics_unavailable(client, result)
                return result

            route_metrics = self._extract_route_metrics(metrics)

            result.metadata.update(
                {
                    "routes_analyzed": len(routes),
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "healthy_routes": 0,
                    "bottleneck_routes": [],
                    "avg_latency_p99": 0.0,
                    "total_throughput": 0.0,
                    "critical_findings": 0,
                }
            )

            if not routes:
                result.add_finding(
                    Finding(
                        id="route-perf-no-routes",
                        category="route_performance",
                        severity="info",
                        title="No Routes Configured",
                        description="No routes found for performance analysis.",
                        affected_components=["Routes"],
                        confidence_level="high",
                        metadata={},
                    )
                )
                result.success = True
                return result

            route_throughputs = []
            all_p99_latencies = []

            for route in routes:
                route_id = route.get("id", "unknown")
                route.setdefault("_name", route.get("name") or route_id)
                r_metrics = route_metrics.get(route_id, {})

                throughput = self._analyze_throughput(route, r_metrics, result)
                route_throughputs.append(throughput)
                result.metadata["total_throughput"] += throughput

                p99_latency = self._analyze_latency(route, r_metrics, result)
                if p99_latency > 0:
                    all_p99_latencies.append(p99_latency)

                self._analyze_error_rates(route, r_metrics, result)
                self._analyze_pipeline_overload(route, throughput, pipelines, result)

            if all_p99_latencies:
                result.metadata["avg_latency_p99"] = sum(all_p99_latencies) / len(all_p99_latencies)

            self._analyze_route_balance(route_throughputs, result)

            problematic_routes = set()
            for f in result.findings:
                if f.severity in ["critical", "high", "medium"]:
                    for comp in f.affected_components:
                        if comp in [r.get("id") for r in routes]:
                            problematic_routes.add(comp)

            result.metadata["healthy_routes"] = len(routes) - len(problematic_routes)
            result.metadata["bottleneck_routes"] = list(problematic_routes)
            result.metadata["critical_findings"] = len(result.get_critical_findings())

            self._add_summary_metadata(result)

            for finding in result.findings:
                if not finding.worker_group:
                    finding.worker_group = client.worker_group

            result.success = True
            log.info(
                "route_performance_analysis_completed",
                routes=len(routes),
                findings=len(result.findings),
            )

        except Exception as e:
            log.error("route_performance_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)
            result.add_finding(
                Finding(
                    id="route-perf-analysis-error",
                    category="route_performance",
                    severity="critical",
                    title="Route Performance Analysis Failed",
                    description=f"Failed to analyze route performance: {str(e)}",
                    affected_components=["Route Analyzer"],
                    remediation_steps=["Check API connectivity", "Verify permissions"],
                    estimated_impact="Cannot assess route performance",
                    confidence_level="high",
                    metadata={"error": str(e)},
                )
            )

        return result

    def _report_metrics_unavailable(self, client: CriblAPIClient, result: AnalyzerResult) -> None:
        """Report that metrics are unavailable."""
        result.add_finding(
            Finding(
                id="route-perf-metrics-unavailable",
                category="route_performance",
                severity="info",
                title="Metrics Unavailable for Route Analysis",
                description=(
                    "System metrics are not available. "
                    "Route performance analysis requires runtime metrics data."
                ),
                affected_components=["Monitoring", "Metrics"],
                remediation_steps=[
                    "Check infrastructure-level metrics",
                    "Review route configurations directly",
                ],
                estimated_impact="Limited visibility into route performance",
                confidence_level="high",
                metadata={"deployment_type": "cloud" if client.is_cloud else "self-hosted"},
            )
        )
        result.success = True

    def _extract_route_metrics(self, metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Extract route-specific metrics.
        Returns dict keyed by route ID.
        """
        route_metrics = {}
        routes_data = metrics.get("routes", {})

        for route_id, data in routes_data.items():
            if isinstance(data, dict):
                events_in = data.get("in", {}).get("events", 0)
                latencies = data.get("latencies", [])

                route_metrics[route_id] = {
                    "events_in": events_in,
                    "events_out": data.get("out", {}).get("events", 0),
                    "errors": data.get("errors", 0),
                    "latencies": latencies,
                    "total_time_ms": data.get("processing_time_ms", 0),
                }
        return route_metrics

    def _calculate_percentile(self, data: list[float], percentile: float) -> float:
        """
        Calculate percentile from a list of values.
        percentile is 0-100.
        """
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = int((percentile / 100) * (len(sorted_data) - 1))
        index = max(0, min(index, len(sorted_data) - 1))
        return sorted_data[index]

    def _analyze_throughput(
        self, route: dict[str, Any], metrics: dict[str, Any], result: AnalyzerResult
    ) -> float:
        route_id = route.get("id", "unknown")
        route_name = route.get("name") or route_id
        events_in = metrics.get("events_in", 0)

        seconds = 3600
        events_per_sec = events_in / seconds

        if events_per_sec == 0 and not route.get("disabled", False):
            result.add_finding(
                Finding(
                    id=f"route-perf-zero-throughput-{route_id}",
                    category="route_performance",
                    severity="low",
                    title=f"Zero Throughput: {route_name}",
                    description=f"Route '{route_name}' has zero throughput over the last hour.",
                    affected_components=["Routes", route_id],
                    remediation_steps=[
                        "Verify if data sources are active",
                        "Check route filter conditions",
                        "Consider disabling unused routes",
                    ],
                    estimated_impact="Unused configuration clutter",
                    confidence_level="high",
                    metadata={"route_id": route_id, "throughput": 0},
                )
            )

        return events_per_sec

    def _analyze_latency(
        self, route: dict[str, Any], metrics: dict[str, Any], result: AnalyzerResult
    ) -> float:
        route_id = route.get("id", "unknown")
        route_name = route.get("name") or route_id
        latencies = metrics.get("latencies", [])

        if not latencies:
            total_time = metrics.get("total_time_ms", 0)
            count = metrics.get("events_in", 0)
            if count > 0:
                avg = total_time / count
                return avg
            return 0.0

        p99 = self._calculate_percentile(latencies, 99)

        if p99 > self.LATENCY_P99_CRITICAL_MS:
            self._report_high_latency(route_id, route_name, p99, "critical", result)
        elif p99 > self.LATENCY_P99_HIGH_MS:
            self._report_high_latency(route_id, route_name, p99, "high", result)

        return p99

    def _report_high_latency(
        self,
        route_id: str,
        route_name: str,
        p99_ms: float,
        severity: Literal["critical", "high", "medium", "low", "info"],
        result: AnalyzerResult,
    ) -> None:
        result.add_finding(
            Finding(
                id=f"route-perf-latency-{route_id}",
                category="route_performance",
                severity=severity,
                title=f"High Latency on Route: {route_name}",
                description=(
                    f"Route '{route_name}' has a p99 latency of {p99_ms:.2f}ms, "
                    f"exceeding the {self.LATENCY_P99_HIGH_MS}ms threshold."
                ),
                affected_components=["Routes", route_id],
                remediation_steps=[
                    "Check pipeline performance linked to this route",
                    "Review filter complexity",
                    "Optimize functions in the pipeline",
                ],
                estimated_impact=f"High processing delay ({p99_ms:.2f}ms)",
                confidence_level="high",
                metadata={"route_id": route_id, "p99_latency": p99_ms},
            )
        )

    def _analyze_error_rates(
        self, route: dict[str, Any], metrics: dict[str, Any], result: AnalyzerResult
    ) -> None:
        route_id = route.get("id", "unknown")
        route_name = route.get("name") or route_id
        events_in = metrics.get("events_in", 0)
        errors = metrics.get("errors", 0)

        if events_in == 0:
            return

        error_rate_percent = (errors / events_in) * 100

        if error_rate_percent > self.ERROR_RATE_CRITICAL_PERCENT:
            self._report_error_rate(route_id, route_name, error_rate_percent, "critical", result)
        elif error_rate_percent > self.ERROR_RATE_HIGH_PERCENT:
            self._report_error_rate(route_id, route_name, error_rate_percent, "high", result)

    def _report_error_rate(
        self,
        route_id: str,
        route_name: str,
        rate: float,
        severity: Literal["critical", "high", "medium", "low", "info"],
        result: AnalyzerResult,
    ) -> None:
        result.add_finding(
            Finding(
                id=f"route-perf-errors-{route_id}",
                category="route_performance",
                severity=severity,
                title=f"High Error Rate on Route: {route_name}",
                description=f"Route '{route_name}' has an error rate of {rate:.2f}%.",
                affected_components=["Routes", route_id],
                remediation_steps=[
                    "Check system logs for error details",
                    "Verify data format matches expectations",
                    "Review pipeline error handling",
                ],
                estimated_impact=f"{rate:.2f}% of events failing",
                confidence_level="high",
                metadata={"route_id": route_id, "error_rate": rate},
            )
        )

    def _analyze_pipeline_overload(
        self,
        route: dict[str, Any],
        throughput: float,
        pipelines: list[dict[str, Any]],
        result: AnalyzerResult,
    ) -> None:
        route_id = route.get("id", "unknown")
        route_name = route.get("name") or route_id
        pipeline_id = route.get("pipeline", "")

        if not pipeline_id or throughput < self.PIPELINE_OVERLOAD_EVENTS_SEC:
            return

        result.add_finding(
            Finding(
                id=f"route-perf-overload-{route_id}",
                category="route_performance",
                severity="medium",
                title=f"High Volume to Single Pipeline: {pipeline_id}",
                description=(
                    f"Route '{route_name}' is sending {throughput:.0f} events/sec to "
                    f"pipeline '{pipeline_id}', which may cause contention."
                ),
                affected_components=["Routes", route_id, "Pipelines", pipeline_id],
                remediation_steps=[
                    "Consider splitting traffic to multiple pipelines",
                    "Ensure pipeline is optimized for high volume",
                    "Use worker groups to distribute load",
                ],
                estimated_impact="Potential processing delays",
                confidence_level="medium",
                metadata={
                    "route_id": route_id,
                    "pipeline_id": pipeline_id,
                    "throughput": throughput,
                },
            )
        )

    def _analyze_route_balance(self, throughputs: list[float], result: AnalyzerResult) -> None:
        """Analyze traffic balance across routes using Coefficient of Variation."""
        if not throughputs or len(throughputs) < 2:
            return

        active_throughputs = [t for t in throughputs if t > 0]
        if len(active_throughputs) < 2:
            return

        mean = statistics.mean(active_throughputs)
        if mean == 0:
            return

        stdev = statistics.stdev(active_throughputs)
        cv = stdev / mean

        if cv > self.BALANCE_CV_THRESHOLD:
            result.add_finding(
                Finding(
                    id="route-perf-imbalance",
                    category="route_performance",
                    severity="medium",
                    title="Imbalanced Route Traffic Distribution",
                    description=(
                        f"Traffic is unevenly distributed across routes (CV: {cv:.2f}). "
                        "Some routes are handling significantly more load than others."
                    ),
                    affected_components=["Routes"],
                    remediation_steps=[
                        "Review routing rules for optimization",
                        "Distribute heavy data sources across multiple routes",
                    ],
                    estimated_impact="Inefficient resource utilization",
                    confidence_level="medium",
                    metadata={"coefficient_of_variation": cv},
                )
            )

    def _add_summary_metadata(self, result: AnalyzerResult) -> None:
        """Add summary status."""
        criticals = result.metadata.get("critical_findings", 0)

        highs = len([f for f in result.findings if f.severity == "high"])
        mediums = len([f for f in result.findings if f.severity == "medium"])

        if criticals > 0:
            result.metadata["overall_status"] = "critical"
        elif highs > 0:
            result.metadata["overall_status"] = "warning"
        elif mediums > 0:
            result.metadata["overall_status"] = "needs_optimization"
        else:
            result.metadata["overall_status"] = "healthy"
