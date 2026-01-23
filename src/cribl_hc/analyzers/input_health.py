"""
Input Source Analyzer for Cribl Health Check.

Analyzes input connectivity, data freshness/lag, error rates, and queue depth.
"""

import time
from typing import Any, Optional

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class InputSourceAnalyzer(BaseAnalyzer):
    """
    Analyzer for input source health and status.
    """

    ERROR_RATE_HIGH_PERCENT = 5.0
    ERROR_RATE_CRITICAL_PERCENT = 10.0

    NO_DATA_HIGH_MINUTES = 5
    NO_DATA_CRITICAL_MINUTES = 60

    QUEUE_DEPTH_WARNING = 1000
    QUEUE_DEPTH_MEDIUM = 10000

    @property
    def objective_name(self) -> str:
        return "input_health"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge"]

    def get_description(self) -> str:
        return "Analyzes input connectivity, data freshness, error rates, and queue depth"

    def get_estimated_api_calls(self) -> int:
        return 2

    def get_required_permissions(self) -> list[str]:
        return [
            "read:inputs",
            "read:metrics",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            log.info("input_health_analysis_started")

            inputs = await client.get_inputs()
            metrics = await client.get_metrics(time_range="1h")

            healthy_count = 0
            error_inputs = []
            total_errors = 0

            input_metrics = self._extract_input_metrics(metrics)
            current_time = time.time()

            for input_item in inputs:
                input_id = input_item.get("id", "unknown")
                if input_item.get("disabled", False):
                    continue

                status_str = input_item.get("status", "unknown")
                if isinstance(status_str, dict):
                    status_str = status_str.get("health", "unknown")

                status_str = str(status_str).lower()
                im = input_metrics.get(input_id, {})

                if status_str in ["error", "critical", "disconnected"]:
                    error_inputs.append(input_id)
                    self._report_connectivity_issue(input_item, status_str, result, client)
                elif status_str == "healthy":
                    healthy_count += 1

                last_event_ts = self._get_last_event_timestamp(input_item)

                if last_event_ts:
                    time_diff_seconds = current_time - last_event_ts
                    time_diff_minutes = time_diff_seconds / 60

                    if time_diff_minutes > self.NO_DATA_CRITICAL_MINUTES:
                        self._report_data_lag(
                            input_item, time_diff_minutes, "critical", result, client
                        )
                    elif time_diff_minutes > self.NO_DATA_HIGH_MINUTES:
                        self._report_data_lag(input_item, time_diff_minutes, "high", result, client)

                events_in = im.get("events_in", 0)
                errors = im.get("errors", 0)
                total_errors += errors

                if events_in > 0:
                    error_rate = (errors / events_in) * 100
                    if error_rate > self.ERROR_RATE_CRITICAL_PERCENT:
                        self._report_error_rate(
                            input_item, error_rate, errors, "critical", result, client
                        )
                    elif error_rate > self.ERROR_RATE_HIGH_PERCENT:
                        self._report_error_rate(
                            input_item, error_rate, errors, "high", result, client
                        )

                queue_size = im.get("queue_size", 0)
                if queue_size > self.QUEUE_DEPTH_MEDIUM:
                    self._report_queue_depth(input_item, queue_size, "medium", result, client)
                elif queue_size > self.QUEUE_DEPTH_WARNING:
                    self._report_queue_depth(input_item, queue_size, "warning", result, client)

            result.metadata.update(
                {
                    "inputs_analyzed": len(inputs),
                    "healthy_inputs": healthy_count,
                    "error_inputs": error_inputs,
                    "total_errors": total_errors,
                    "critical_findings": len(result.get_critical_findings()),
                }
            )

            result.success = True
            log.info(
                "input_health_analysis_completed",
                inputs=len(inputs),
                findings=len(result.findings),
                healthy=healthy_count,
            )

        except Exception as e:
            log.error("input_health_analysis_failed", error=str(e))
            result.success = False
            result.error = f"Input health analysis failed: {str(e)}"
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="input-analysis-error",
                    title="Input Health Analysis Failed",
                    description=f"Unable to complete input health analysis: {str(e)}",
                    severity="high",
                    category="input_health",
                    confidence_level="high",
                    affected_components=["input_analyzer"],
                    estimated_impact="Unable to assess input source health",
                    remediation_steps=[
                        "Check API connectivity",
                        "Verify authentication token",
                        "Review error logs",
                    ],
                    metadata={"error": str(e)},
                )
            )

        return result

    def _extract_input_metrics(self, metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
        input_metrics = {}

        inputs_data = metrics.get("inputs", {})
        if not inputs_data:
            inputs_data = metrics.get("sources", {})

        for input_id, data in inputs_data.items():
            if isinstance(data, dict):
                input_metrics[input_id] = {
                    "events_in": data.get("in", {}).get("events", 0),
                    "bytes_in": data.get("in", {}).get("bytes", 0),
                    "errors": data.get("errors", 0),
                    "queue_size": data.get("queue", {}).get("size", 0),
                }

                if not input_metrics[input_id]["errors"] and isinstance(data.get("errors"), dict):
                    input_metrics[input_id]["errors"] = data.get("errors", {}).get("total", 0)

        return input_metrics

    def _get_last_event_timestamp(self, input_item: dict[str, Any]) -> Optional[float]:
        status = input_item.get("status")
        if isinstance(status, dict):
            ts = status.get("lastEventTime") or status.get("lastEvent")
            if ts:
                if ts > 1000000000000:
                    return ts / 1000.0
                return float(ts)
        return None

    def _report_connectivity_issue(
        self,
        input_item: dict[str, Any],
        status: str,
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        input_id = input_item.get("id", "unknown")
        input_type = input_item.get("type", "unknown")

        result.add_finding(
            self.create_finding(
                client=client,
                id=f"input-connectivity-{input_id}",
                title=f"Input Disconnected: {input_id}",
                description=f"Input {input_id} ({input_type}) is in '{status}' state.",
                severity="critical",
                category="input_health",
                confidence_level="high",
                affected_components=[f"input:{input_id}"],
                estimated_impact="Data collection interrupted for this source",
                remediation_steps=[
                    "Check network connectivity to the source",
                    "Verify input configuration credentials",
                    "Check firewall rules",
                    "Restart the input if stuck",
                ],
                metadata={"input_id": input_id, "input_type": input_type, "status": status},
            )
        )

        result.add_recommendation(
            Recommendation(
                id=f"rec-input-fix-{input_id}",
                type="operations",
                priority="p0",
                title=f"Restore Connectivity: {input_id}",
                description=f"Restore connectivity for input {input_id}",
                rationale="Data ingestion is stopped for this source",
                implementation_steps=[
                    "Verify network reachability",
                    "Check authentication credentials",
                    "Review input logs for specific error messages",
                ],
                before_state="Input disconnected",
                after_state="Input connected and receiving data",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Resumes data ingestion",
                    time_to_implement="15 min",
                    cost_savings_annual=None,
                    storage_reduction_gb=None,
                ),
                implementation_effort="low",
                product_tags=["stream", "edge"],
            )
        )

    def _report_data_lag(
        self,
        input_item: dict[str, Any],
        lag_minutes: float,
        severity_level: str,
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        input_id = input_item.get("id", "unknown")

        result.add_finding(
            self.create_finding(
                client=client,
                id=f"input-lag-{input_id}",
                title=f"Data Lag Detected: {input_id}",
                description=f"No data received from input {input_id} for {lag_minutes:.1f} minutes.",
                severity=severity_level,
                category="input_health",
                confidence_level="medium",
                affected_components=[f"input:{input_id}"],
                estimated_impact="Delayed data availability or silent failure",
                remediation_steps=[
                    "Check if the source system is generating data",
                    "Verify network path for latency or drops",
                    "Check for backpressure downstream blocking inputs",
                ],
                metadata={"input_id": input_id, "lag_minutes": lag_minutes},
            )
        )

    def _report_error_rate(
        self,
        input_item: dict[str, Any],
        error_rate: float,
        error_count: int,
        severity_level: str,
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        input_id = input_item.get("id", "unknown")

        result.add_finding(
            self.create_finding(
                client=client,
                id=f"input-errors-{input_id}",
                title=f"High Error Rate: {input_id}",
                description=f"Input {input_id} has {error_rate:.1f}% error rate ({error_count} errors).",
                severity=severity_level,
                category="input_health",
                confidence_level="high",
                affected_components=[f"input:{input_id}"],
                estimated_impact="Data loss or quality degradation",
                remediation_steps=[
                    "Review input logs for error details",
                    "Check data format compatibility",
                    "Verify authentication/authorization if applicable",
                ],
                metadata={
                    "input_id": input_id,
                    "error_rate": error_rate,
                    "error_count": error_count,
                },
            )
        )

    def _report_queue_depth(
        self,
        input_item: dict[str, Any],
        queue_size: int,
        severity_level: str,
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        input_id = input_item.get("id", "unknown")

        severity = "low" if severity_level == "warning" else severity_level

        result.add_finding(
            self.create_finding(
                client=client,
                id=f"input-queue-{input_id}",
                title=f"Input Queue Buildup: {input_id}",
                description=f"Input {input_id} has {queue_size} events queued.",
                severity=severity,
                category="input_health",
                confidence_level="medium",
                affected_components=[f"input:{input_id}"],
                estimated_impact="Processing latency",
                remediation_steps=[
                    "Check worker CPU/Memory usage",
                    "Verify pipeline performance",
                    "Check for blocking outputs",
                ],
                metadata={"input_id": input_id, "queue_size": queue_size},
            )
        )
