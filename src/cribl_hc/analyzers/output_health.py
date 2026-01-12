from typing import Any, Dict, List, Optional

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class OutputDestinationAnalyzer(BaseAnalyzer):
    """
    Analyzer for output destination health and configuration.

    Evaluates:
    - Destination connectivity and reachability
    - Configuration validity (required fields, authentication)
    - Error rates and delivery reliability
    - Buffer/queue status
    - Delivery confirmation settings
    """

    DEPRECATED_TYPES = {"splunk_hec_legacy", "syslog_legacy"}

    @property
    def objective_name(self) -> str:
        """Return 'output_health' as the objective name."""
        return "output_health"

    @property
    def supported_products(self) -> List[str]:
        """Output analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Output destination health, connectivity, and configuration analysis"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls needed.
        - outputs(1) + metrics(1) = 2 calls
        """
        return 2

    def get_required_permissions(self) -> List[str]:
        """List required API permissions."""
        return ["read:outputs", "read:metrics"]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze output destination health and configuration.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with output health findings
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            self.log.info("output_health_analysis_started")

            outputs = await self._fetch_outputs(client)
            metrics = await self._fetch_metrics(client)

            result.metadata["outputs_analyzed"] = len(outputs)

            healthy_count = 0
            unreachable_outputs = []
            error_outputs = []

            for output in outputs:
                is_healthy = True
                output_id = output.get("id", "unknown")

                if not self._check_connectivity(output, result, client):
                    is_healthy = False
                    unreachable_outputs.append(output_id)

                if not self._validate_configuration(output, result, client):
                    is_healthy = False

                error_rate_issues = self._check_error_rates(output, metrics, result, client)
                if error_rate_issues:
                    is_healthy = False
                    error_outputs.append({"id": output_id, "issues": error_rate_issues})

                if not self._check_buffer_status(output, metrics, result, client):
                    is_healthy = False

                if not self._check_delivery_confirmation(output, result, client):
                    pass

                if is_healthy:
                    healthy_count += 1

            result.metadata["healthy_outputs"] = healthy_count
            result.metadata["unreachable_outputs"] = unreachable_outputs
            result.metadata["error_outputs"] = error_outputs
            result.metadata["critical_findings"] = len(result.get_critical_findings())

            result.success = True
            self.log.info(
                "output_health_analysis_completed",
                outputs=len(outputs),
                healthy=healthy_count,
                findings=len(result.findings),
            )

        except Exception as e:
            self.log.error("output_health_analysis_failed", error=str(e))
            result.error = f"Output health analysis failed: {str(e)}"
            result.success = False

        return result

    async def _fetch_outputs(self, client: CriblAPIClient) -> List[Dict[str, Any]]:
        try:
            return await client.get_outputs() or []
        except Exception as e:
            self.log.warning("failed_to_fetch_outputs", error=str(e))
            return []

    async def _fetch_metrics(self, client: CriblAPIClient) -> Dict[str, Any]:
        try:
            return await client.get_metrics(time_range="1h") or {}
        except Exception as e:
            self.log.warning("failed_to_fetch_metrics", error=str(e))
            return {}

    def _check_connectivity(
        self, output: Dict[str, Any], result: AnalyzerResult, client: CriblAPIClient
    ) -> bool:
        output_id = output.get("id", "unknown")
        status = output.get("status", {}).get("health", "unknown")

        if status in ["dead", "failed", "error"]:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"output-unreachable-{output_id}",
                    category="output_health",
                    severity="critical",
                    title=f"Output Destination Unreachable: {output_id}",
                    description=f"Output '{output_id}' is reporting status '{status}'. Data loss risk.",
                    confidence_level="high",
                    affected_components=[output_id],
                    estimated_impact="Potential data loss or queuing.",
                    remediation_steps=[
                        f"Check network connectivity to {output.get('type')} destination",
                        "Verify destination service is up and running",
                        "Check authentication credentials",
                    ],
                    metadata={"output_id": output_id, "status": status},
                )
            )
            return False

        return True

    def _validate_configuration(
        self, output: Dict[str, Any], result: AnalyzerResult, client: CriblAPIClient
    ) -> bool:
        output_id = output.get("id", "unknown")
        output_type = output.get("type", "unknown")
        is_valid = True

        if output.get("enabled", True):
            if output_type == "splunk_hec" and not output.get("token"):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"output-missing-auth-{output_id}",
                        category="output_health",
                        severity="high",
                        title=f"Missing Authentication: {output_id}",
                        description=f"Output '{output_id}' ({output_type}) is missing required authentication token.",
                        confidence_level="high",
                        affected_components=[output_id],
                        estimated_impact="Output will fail to deliver data without authentication.",
                        remediation_steps=[
                            "Configure authentication token for the output",
                            "Verify destination credentials",
                        ],
                        metadata={"output_id": output_id, "type": output_type},
                    )
                )
                is_valid = False

        if output_type in self.DEPRECATED_TYPES:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"output-deprecated-type-{output_id}",
                    category="output_health",
                    severity="medium",
                    title=f"Deprecated Output Type: {output_id}",
                    description=f"Output '{output_id}' uses deprecated type '{output_type}'.",
                    confidence_level="high",
                    affected_components=[output_id],
                    remediation_steps=[
                        f"Migrate output '{output_id}' to a supported type",
                        "Consult Cribl documentation for migration guide",
                    ],
                    metadata={"output_id": output_id, "type": output_type},
                )
            )

        return is_valid

    def _check_error_rates(
        self,
        output: Dict[str, Any],
        metrics: Dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> List[str]:
        output_id = output.get("id", "unknown")
        issues = []

        items = metrics.get("items", [])
        if not items:
            return issues

        events = 0
        errors = 0

        for item in items:
            dims = item.get("dimensions", {})
            if dims.get("output") == output_id:
                name = item.get("name", "")
                val = item.get("value", 0)

                if "send.events" in name or "events" in name:
                    events += val
                elif "send.errors" in name or "errors" in name:
                    errors += val

        total = events + errors
        if total > 0:
            error_rate = (errors / total) * 100

            if error_rate > 10:
                issues.append(f"Critical error rate: {error_rate:.1f}%")
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"output-high-error-rate-{output_id}",
                        category="output_health",
                        severity="critical",
                        title=f"Critical Output Error Rate: {output_id}",
                        description=f"Output '{output_id}' has >10% failure rate ({error_rate:.1f}%).",
                        confidence_level="high",
                        affected_components=[output_id],
                        estimated_impact="Significant data loss occurring.",
                        remediation_steps=[
                            "Check destination availability",
                            "Review network configuration",
                            "Check output logs for specific error messages",
                        ],
                        metadata={"output_id": output_id, "error_rate": error_rate},
                    )
                )
            elif error_rate > 5:
                issues.append(f"High error rate: {error_rate:.1f}%")
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"output-elevated-error-rate-{output_id}",
                        category="output_health",
                        severity="high",
                        title=f"Elevated Output Error Rate: {output_id}",
                        description=f"Output '{output_id}' has >5% failure rate ({error_rate:.1f}%).",
                        confidence_level="high",
                        affected_components=[output_id],
                        estimated_impact=f"Approximately {error_rate:.1f}% of data may be lost.",
                        remediation_steps=[
                            "Monitor destination performance",
                            "Check for intermittent network issues",
                        ],
                        metadata={"output_id": output_id, "error_rate": error_rate},
                    )
                )

        return issues

    def _check_buffer_status(
        self,
        output: Dict[str, Any],
        metrics: Dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> bool:
        output_id = output.get("id", "unknown")

        queue_size = 0
        items = metrics.get("items", [])

        for item in items:
            dims = item.get("dimensions", {})
            if dims.get("output") == output_id and "queue" in item.get("name", ""):
                queue_size += item.get("value", 0)

        if queue_size > 50000:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"output-queue-critical-{output_id}",
                    category="output_health",
                    severity="high",
                    title=f"Critical Queue Depth: {output_id}",
                    description=f"Output '{output_id}' queue size is critical ({queue_size} events).",
                    confidence_level="high",
                    affected_components=[output_id],
                    estimated_impact="High latency and potential backpressure.",
                    remediation_steps=[
                        "Check destination ingestion rate",
                        "Verify network bandwidth",
                        "Consider enabling Persistent Queues if not enabled",
                    ],
                    metadata={"output_id": output_id, "queue_size": queue_size},
                )
            )
            return False
        elif queue_size > 10000:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"output-queue-warning-{output_id}",
                    category="output_health",
                    severity="medium",
                    title=f"Queue Backing Up: {output_id}",
                    description=f"Output '{output_id}' queue size is growing ({queue_size} events).",
                    confidence_level="medium",
                    affected_components=[output_id],
                    remediation_steps=[
                        "Monitor queue growth trend",
                        "Check destination performance",
                    ],
                    metadata={"output_id": output_id, "queue_size": queue_size},
                )
            )
            return False

        return True

    def _check_delivery_confirmation(
        self, output: Dict[str, Any], result: AnalyzerResult, client: CriblAPIClient
    ) -> bool:
        output_id = output.get("id", "unknown")
        output_type = output.get("type", "unknown")

        critical_types = {"splunk", "splunk_hec", "elastic", "s3", "minio"}

        if output_type in critical_types:
            ack_enabled = output.get("ackEnabled") or output.get("enableAck") or False

            if not ack_enabled:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"output-ack-disabled-{output_id}",
                        category="output_health",
                        severity="medium",
                        title=f"Delivery Confirmation Disabled: {output_id}",
                        description=f"Critical output '{output_id}' ({output_type}) has delivery confirmation disabled.",
                        confidence_level="high",
                        affected_components=[output_id],
                        estimated_impact="Data loss may go undetected if destination accepts but fails to persist.",
                        remediation_steps=[
                            "Enable Delivery Confirmation/Acknowledgments in output settings",
                            "Ensure destination supports acknowledgments",
                        ],
                        metadata={"output_id": output_id, "type": output_type},
                    )
                )
                return False

        return True
