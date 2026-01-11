from typing import Any, Dict

from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding


class EndpointHealthAnalyzer(BaseAnalyzer):
    """
    Analyzes the health of Cribl Stream endpoints (Destinations).
    """

    @property
    def objective_name(self) -> str:
        """
        Return the objective name for this analyzer.
        """
        return "Endpoint Health"

    def get_required_permissions(self) -> list[str]:
        return ["read:metrics"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform analysis on endpoint health metrics.
        """
        result = self.create_result()
        metrics_data = await client.get_metrics()

        outputs = metrics_data.get("outputs", {})

        if not outputs:
            return result

        for output_id, metrics in outputs.items():
            self._check_request_failure_rate(result, output_id, metrics)
            self._check_latency_spikes(result, output_id, metrics)
            self._check_circuit_breaker_state(result, output_id, metrics)
            self._check_destination_uptime(result, output_id, metrics)

        return result

    def _check_request_failure_rate(
        self, result: AnalyzerResult, output_id: str, metrics: Dict[str, Any]
    ):
        """Checks for high request failure rates to a destination."""
        requests = metrics.get("requests", {})
        total_requests = requests.get("total", 0)
        failed_requests = requests.get("failed", 0)

        if total_requests == 0:
            return

        failure_rate = (failed_requests / total_requests) * 100
        remediation = [
            "Investigate the downstream service for availability and errors.",
            "Check network connectivity between Cribl Stream workers and the destination.",
            "Review destination configuration for correctness (e.g., credentials, endpoint URL).",
            "Examine Cribl Stream logs for specific error messages related to this destination.",
        ]

        if failure_rate > 5:
            impact = "Significant data loss is occurring. Events sent to this destination are being dropped."
            title = f"Critical Failure Rate for {output_id}"
            description = (
                f"Destination '{output_id}' has a request failure rate of {failure_rate:.2f}%, "
                f"exceeding the 5% critical threshold. This indicates a severe and ongoing issue "
                f"with the downstream system or connectivity."
            )
            result.add_finding(
                self.create_finding(
                    id=f"endpoint-failure-rate-critical-{output_id}",
                    category="Endpoint Health",
                    severity="critical",
                    title=title,
                    description=description,
                    affected_components=[output_id],
                    remediation_steps=remediation,
                    estimated_impact=impact,
                    metadata={
                        "failure_rate": f"{failure_rate:.2f}%",
                        "total_requests": total_requests,
                    },
                )
            )
        elif failure_rate >= 2:
            impact = "Moderate data loss is occurring. A significant portion of events are failing to reach the destination."
            title = f"High Failure Rate for {output_id}"
            description = (
                f"Destination '{output_id}' has a request failure rate of {failure_rate:.2f}%, "
                f"which is between the 2% and 5% high-severity threshold. This suggests a persistent problem "
                f"that could lead to significant data loss if not addressed."
            )
            result.add_finding(
                self.create_finding(
                    id=f"endpoint-failure-rate-high-{output_id}",
                    category="Endpoint Health",
                    severity="high",
                    title=title,
                    description=description,
                    affected_components=[output_id],
                    remediation_steps=remediation,
                    estimated_impact=impact,
                    metadata={
                        "failure_rate": f"{failure_rate:.2f}%",
                        "total_requests": total_requests,
                    },
                )
            )

    def _check_latency_spikes(
        self, result: AnalyzerResult, output_id: str, metrics: Dict[str, Any]
    ):
        """Detects significant spikes in p99 latency."""
        latency_metrics = metrics.get("latency", {})
        p99_latency = latency_metrics.get("p99")
        baseline_latency = metrics.get("baseline_latency")

        if p99_latency is None or baseline_latency is None or baseline_latency <= 0:
            return

        if p99_latency > (baseline_latency * 2):
            title = f"Latency Spike Detected for {output_id}"
            description = (
                f"Destination '{output_id}' is experiencing high latency. "
                f"The p99 latency is {p99_latency:.2f}ms, which is more than double the baseline of {baseline_latency:.2f}ms. "
                f"This can lead to backpressure and potential data loss."
            )
            remediation = [
                "Check the performance and load of the downstream service.",
                "Investigate network latency between Cribl Stream workers and the destination.",
                "Ensure the destination is adequately provisioned to handle the current data volume.",
            ]
            result.add_finding(
                self.create_finding(
                    id=f"endpoint-latency-spike-{output_id}",
                    category="Endpoint Health",
                    severity="medium",
                    title=title,
                    description=description,
                    affected_components=[output_id],
                    remediation_steps=remediation,
                    metadata={
                        "p99_latency_ms": p99_latency,
                        "baseline_latency_ms": baseline_latency,
                    },
                )
            )

    def _check_circuit_breaker_state(
        self, result: AnalyzerResult, output_id: str, metrics: Dict[str, Any]
    ):
        """Checks if the destination's circuit breaker is open."""
        is_open = metrics.get("circuit_breaker_open", 0)

        if is_open:
            impact = "Data flow to this destination is completely blocked, leading to data loss until the circuit breaker closes."
            title = f"Circuit Breaker Open for {output_id}"
            description = (
                f"The circuit breaker for destination '{output_id}' is open. "
                f"This means the destination is considered unhealthy, and Cribl Stream has stopped sending data to it to prevent further issues."
            )
            remediation = [
                "Immediately investigate the downstream service for a major outage or performance degradation.",
                "Resolve the underlying issue causing request failures or timeouts.",
                "Monitor the destination in Cribl Stream; the circuit breaker will close automatically once the destination is healthy again.",
            ]
            result.add_finding(
                self.create_finding(
                    id=f"endpoint-circuit-breaker-open-{output_id}",
                    category="Endpoint Health",
                    severity="critical",
                    title=title,
                    description=description,
                    affected_components=[output_id],
                    remediation_steps=remediation,
                    estimated_impact=impact,
                    metadata={},
                )
            )

    def _check_destination_uptime(
        self, result: AnalyzerResult, output_id: str, metrics: Dict[str, Any]
    ):
        """Checks the uptime ratio of the destination (deferred)."""
        # This check is deferred due to the complexity of historical data.
        pass
