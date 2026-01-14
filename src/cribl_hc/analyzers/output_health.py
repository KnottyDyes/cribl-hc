"""
Output Destination Analyzer for Cribl Health Check.

Analyzes output connectivity, configuration, error rates, and queue status.
"""

from typing import Any

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.recommendation import ImpactEstimate, Recommendation
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class OutputDestinationAnalyzer(BaseAnalyzer):
    """
    Analyzer for output destination health and status.
    """

    ERROR_RATE_HIGH_PERCENT = 5.0
    ERROR_RATE_CRITICAL_PERCENT = 10.0

    QUEUE_DEPTH_WARNING = 1000
    QUEUE_DEPTH_MEDIUM = 10000

    DEPRECATED_TYPES = {"splunk_hec_legacy", "syslog_legacy", "kafka_legacy"}

    @property
    def objective_name(self) -> str:
        return "output_health"

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge"]

    def get_description(self) -> str:
        return "Analyzes output connectivity, configuration, error rates, queue status, and delivery confirmations"

    def get_estimated_api_calls(self) -> int:
        return 3

    def get_required_permissions(self) -> list[str]:
        return [
            "read:outputs",
            "read:metrics",
            "read:system",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        result = self.create_result()

        try:
            log.info("output_health_analysis_started")

            outputs = await client.get_outputs()
            metrics = await client.get_metrics(time_range="1h")
            # Fetch notifications for delivery confirmation checks as per spec
            notifications = await client.get_notifications()

            healthy_count = 0
            error_outputs = []
            total_errors = 0

            output_metrics = self._extract_output_metrics(metrics)

            for output_item in outputs:
                output_id = output_item.get("id", "unknown")
                if output_item.get("disabled", False):
                    continue

                # 1. Destination Connectivity
                status_val = output_item.get("status")
                status_str = "unknown"
                if isinstance(status_val, dict):
                    status_str = status_val.get("health", "unknown")
                elif isinstance(status_val, str):
                    status_str = status_val

                status_str = status_str.lower()

                if status_str in ["error", "critical", "disconnected", "failed", "dead"]:
                    error_outputs.append(output_id)
                    self._report_connectivity_issue(output_item, status_str, result, client)
                elif status_str == "healthy":
                    healthy_count += 1

                # 2. Configuration Validation
                self._validate_configuration(output_item, result, client)

                # 3. Error Rate Tracking & 4. Buffer/Queue Status
                om = output_metrics.get(output_id, {})
                events_out = om.get("events_out", 0)
                errors = om.get("errors", 0)
                total_errors += errors

                total_events = events_out + errors

                if total_events > 0:
                    error_rate = (errors / total_events) * 100
                    if error_rate > self.ERROR_RATE_CRITICAL_PERCENT:
                        self._report_error_rate(
                            output_item, error_rate, errors, "critical", result, client
                        )
                    elif error_rate > self.ERROR_RATE_HIGH_PERCENT:
                        self._report_error_rate(
                            output_item, error_rate, errors, "high", result, client
                        )

                queue_size = om.get("queue_size", 0)
                if queue_size > self.QUEUE_DEPTH_MEDIUM:
                    self._report_queue_depth(output_item, queue_size, "medium", result, client)
                elif queue_size > self.QUEUE_DEPTH_WARNING:
                    self._report_queue_depth(output_item, queue_size, "warning", result, client)

                # 5. Delivery Confirmation
                self._check_delivery_confirmation(output_item, notifications, result, client)

            result.metadata.update(
                {
                    "outputs_analyzed": len(outputs),
                    "healthy_outputs": healthy_count,
                    "error_outputs": error_outputs,
                    "total_errors": total_errors,
                    "critical_findings": len(result.get_critical_findings()),
                }
            )

            result.success = True
            log.info(
                "output_health_analysis_completed",
                outputs=len(outputs),
                findings=len(result.findings),
                healthy=healthy_count,
            )

        except Exception as e:
            log.error("output_health_analysis_failed", error=str(e))
            result.success = False
            result.error = f"Output health analysis failed: {str(e)}"
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="output-analysis-error",
                    title="Output Health Analysis Failed",
                    description=f"Unable to complete output health analysis: {str(e)}",
                    severity="high",
                    category="output_health",
                    confidence_level="high",
                    affected_components=["output_analyzer"],
                    estimated_impact="Unable to assess output destination health",
                    remediation_steps=[
                        "Check API connectivity",
                        "Verify authentication token",
                        "Review error logs",
                    ],
                    metadata={"error": str(e)},
                )
            )

        return result

    def _extract_output_metrics(self, metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
        output_metrics = {}

        outputs_data = metrics.get("outputs", {})
        # Fallback if structure is different
        if not outputs_data:
            # Sometimes metrics might be in 'items' list if gathered differently,
            pass

        for output_id, data in outputs_data.items():
            if isinstance(data, dict):
                output_metrics[output_id] = {
                    "events_out": data.get("out", {}).get("events", 0),
                    "bytes_out": data.get("out", {}).get("bytes", 0),
                    "errors": data.get("errors", 0),
                    "queue_size": data.get("queue", {}).get("size", 0),
                }

                # Sometimes errors is a dict
                if not output_metrics[output_id]["errors"] and isinstance(data.get("errors"), dict):
                    output_metrics[output_id]["errors"] = data.get("errors", {}).get("total", 0)

        # Also support list-based metrics if provided (like in test mocks sometimes)
        if "items" in metrics:
            for item in metrics["items"]:
                dims = item.get("dimensions", {})
                oid = dims.get("output")
                if oid:
                    if oid not in output_metrics:
                        output_metrics[oid] = {"events_out": 0, "errors": 0, "queue_size": 0}

                    name = item.get("name", "")
                    val = item.get("value", 0)

                    if "send.events" in name or "events" in name:
                        output_metrics[oid]["events_out"] += val
                    elif "send.errors" in name or "errors" in name:
                        output_metrics[oid]["errors"] += val
                    elif "queue.size" in name or "queue" in name:
                        output_metrics[oid]["queue_size"] += val

        return output_metrics

    def _report_connectivity_issue(
        self,
        output_item: dict[str, Any],
        status: str,
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        output_id = output_item.get("id", "unknown")
        output_type = output_item.get("type", "unknown")

        result.add_finding(
            self.create_finding(
                client=client,
                id=f"output-connectivity-{output_id}",
                title=f"Output Disconnected: {output_id}",
                description=f"Output {output_id} ({output_type}) is in '{status}' state.",
                severity="critical",
                category="output_health",
                confidence_level="high",
                affected_components=[output_id],
                estimated_impact="Data loss risk or backpressure buildup",
                remediation_steps=[
                    "Check network connectivity to the destination",
                    "Verify output credentials",
                    "Check destination service status",
                    "Review firewall rules",
                ],
                metadata={"output_id": output_id, "output_type": output_type, "status": status},
            )
        )

        result.add_recommendation(
            Recommendation(
                id=f"rec-output-fix-{output_id}",
                type="operations",
                priority="p0",
                title=f"Restore Output Connectivity: {output_id}",
                description=f"Restore connectivity for output {output_id}",
                rationale="Data delivery is stopped for this destination",
                implementation_steps=[
                    "Verify network reachability",
                    "Check authentication credentials",
                    "Review output logs",
                ],
                before_state="Output disconnected",
                after_state="Output connected and sending data",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Resumes data delivery",
                    time_to_implement="15 min",
                    cost_savings_annual=None,
                    storage_reduction_gb=None,
                ),
                implementation_effort="low",
                product_tags=["stream", "edge"],
            )
        )

    def _validate_configuration(
        self,
        output_item: dict[str, Any],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        output_id = output_item.get("id", "unknown")
        output_type = output_item.get("type", "unknown")

        # Check for missing required fields (generic check)
        if output_type == "splunk_hec" and not output_item.get("token"):
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"output-missing-auth-{output_id}",
                    title=f"Missing Authentication: {output_id}",
                    description=f"Output {output_id} ({output_type}) is missing required authentication token.",
                    severity="high",
                    category="configuration",
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

        # Check for deprecated endpoints/types
        if output_type in self.DEPRECATED_TYPES:
            result.add_finding(
                self.create_finding(
                    client=client,
                    id=f"output-deprecated-{output_id}",
                    title=f"Deprecated Output Type: {output_id}",
                    description=f"Output {output_id} uses deprecated type '{output_type}'.",
                    severity="medium",
                    category="configuration",
                    confidence_level="high",
                    affected_components=[output_id],
                    estimated_impact="Future compatibility issues",
                    remediation_steps=[
                        f"Migrate {output_id} to a supported output type",
                    ],
                    metadata={"output_id": output_id, "type": output_type},
                )
            )

    def _report_error_rate(
        self,
        output_item: dict[str, Any],
        error_rate: float,
        error_count: int,
        severity_level: str,
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        output_id = output_item.get("id", "unknown")

        id_prefix = (
            "output-high-error-rate"
            if severity_level == "critical"
            else "output-elevated-error-rate"
        )

        result.add_finding(
            self.create_finding(
                client=client,
                id=f"{id_prefix}-{output_id}",
                title=f"High Output Failure Rate: {output_id}",
                description=f"Output {output_id} has {error_rate:.1f}% failure rate ({error_count} errors).",
                severity=severity_level,
                category="output_health",
                confidence_level="high",
                affected_components=[output_id],
                estimated_impact="Data loss or delivery delays",
                remediation_steps=[
                    "Check destination system health",
                    "Verify network stability",
                    "Check for rate limiting at destination",
                ],
                metadata={
                    "output_id": output_id,
                    "error_rate": error_rate,
                    "error_count": error_count,
                },
            )
        )

    def _report_queue_depth(
        self,
        output_item: dict[str, Any],
        queue_size: int,
        severity_level: str,
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        output_id = output_item.get("id", "unknown")

        severity = "low" if severity_level == "warning" else severity_level

        result.add_finding(
            self.create_finding(
                client=client,
                id=f"output-queue-{output_id}",
                title=f"Output Queue Backlog: {output_id}",
                description=f"Output {output_id} has {queue_size} events queued.",
                severity=severity,
                category="output_health",
                confidence_level="medium",
                affected_components=[output_id],
                estimated_impact="Downstream data delay, potential backpressure",
                remediation_steps=[
                    "Check destination throughput",
                    "Increase worker resources if bottlenecked",
                    "Enable persistent queues if not already",
                ],
                metadata={"output_id": output_id, "queue_size": queue_size},
            )
        )

    def _check_delivery_confirmation(
        self,
        output_item: dict[str, Any],
        notifications: list[dict[str, Any]],
        result: AnalyzerResult,
        client: CriblAPIClient,
    ) -> None:
        output_id = output_item.get("id", "unknown")
        output_type = output_item.get("type", "unknown")

        # 1. Check if confirmations are disabled on critical outputs
        critical_types = {"splunk", "splunk_hec", "elastic", "s3", "minio"}
        if output_type in critical_types:
            # Check for various enable flags
            ack_enabled = (
                output_item.get("ackEnabled")
                or output_item.get("enableAck")
                or output_item.get("enableDeadLetterQueue")  # sometimes implies reliability
                or False
            )

            # S3 usually doesn't have 'ack', but 'enableDeadLetterQueue' or similar reliability settings
            if output_type == "s3":
                # For S3, strictly speaking there isn't an "ACK" but we want to know if it's verifying uploads
                # Usually standard S3 output does verify.
                # Let's skip S3 for "ackEnabled" check unless we know the specific field.
                pass
            elif not ack_enabled:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"output-ack-disabled-{output_id}",
                        title=f"Delivery Confirmation Disabled: {output_id}",
                        description=f"Critical output '{output_id}' ({output_type}) has delivery confirmation disabled.",
                        severity="medium",
                        category="configuration",
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

        # 2. Check for system notifications regarding delivery failures for this output
        # Notifications usually look like: {"id": "...", "text": "Output ... failed to connect", ...}
        for notif in notifications:
            notif_text = str(notif.get("text") or notif.get("message") or "").lower()
            if output_id.lower() in notif_text and (
                "fail" in notif_text or "error" in notif_text or "drop" in notif_text
            ):
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"output-delivery-fail-{output_id}",
                        title=f"Delivery Failure Notification: {output_id}",
                        description=f"System notification indicates delivery failure: {notif_text[:100]}...",
                        severity="medium",
                        category="output_health",
                        confidence_level="medium",
                        affected_components=[output_id],
                        estimated_impact="Confirmed delivery failures reported by system",
                        remediation_steps=[
                            "Investigate system notifications",
                            "Check destination logs",
                        ],
                        metadata={"output_id": output_id, "notification": notif_text},
                    )
                )
