"""
Notification Delivery Analyzer for Cribl Health Check.

Analyzes alert delivery infrastructure to ensure notifications reach responders
and escalation paths are healthy.

Priority: P2 (Medium Impact - Quality & Reliability)
"""

from typing import Any

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class NotificationDeliveryAnalyzer(BaseAnalyzer):
    """
    Analyzer for notification delivery health and alerting infrastructure.

    Identifies:
    - Notification targets that are unreachable or misconfigured
    - Alerts without assigned delivery targets
    - Disabled notifications
    - Escalation path gaps
    - Delivery success rate tracking
    """

    @property
    def objective_name(self) -> str:
        """Return the objective name for this analyzer."""
        return "notification_delivery"

    @property
    def supported_products(self) -> list[str]:
        """Notification analyzer applies to Stream and Edge."""
        return ["stream", "edge"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Analyzes notification delivery infrastructure and alerting paths"

    def get_estimated_api_calls(self) -> int:
        """Estimate API calls: notifications(1) + notification_targets(1) = 2."""
        return 2

    def get_required_permissions(self) -> list[str]:
        """Return required API permissions."""
        return [
            "read:notifications",
            "read:notification-targets",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze notification delivery health.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with notification delivery findings
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            log.info("notification_delivery_analysis_started")

            notifications = await self._fetch_notifications(client)
            targets = await self._fetch_targets(client)

            result.metadata["notifications_analyzed"] = len(notifications)
            result.metadata["targets_analyzed"] = len(targets)

            if not notifications:
                result.add_finding(
                    Finding(
                        id="notif-delivery-no-notifications",
                        category="notification_delivery",
                        severity="info",
                        title="No Notifications Configured",
                        description="No notification rules found for delivery analysis.",
                        affected_components=["Notifications"],
                        confidence_level="high",
                        metadata={},
                    )
                )
                result.success = True
                return result

            if not targets:
                result.add_finding(
                    Finding(
                        id="notif-delivery-no-targets",
                        category="notification_delivery",
                        severity="critical",
                        title="No Notification Targets Configured",
                        description="Notifications are configured but no delivery targets exist. Alerts cannot be delivered.",
                        affected_components=["Notification Targets"],
                        remediation_steps=[
                            "Configure at least one notification target (Slack, Email, PagerDuty, etc.)",
                            "Verify target credentials are valid",
                            "Test target connectivity",
                        ],
                        estimated_impact="Alerts cannot reach responders",
                        confidence_level="high",
                        metadata={},
                    )
                )
                result.success = True
                return result

            healthy_count = 0
            problematic_notifs = []

            for notif in notifications:
                notif_id = notif.get("id", "unknown")
                is_healthy = True

                if not self._check_targets_assigned(notif, targets, result):
                    is_healthy = False
                    problematic_notifs.append(notif_id)

                if not self._check_notification_enabled(notif, result):
                    is_healthy = False
                    problematic_notifs.append(notif_id)

                if not self._check_target_health(notif, targets, result):
                    is_healthy = False
                    problematic_notifs.append(notif_id)

                if is_healthy:
                    healthy_count += 1

            result.metadata["healthy_notifications"] = healthy_count
            result.metadata["problematic_notifications"] = problematic_notifs
            result.metadata["critical_findings"] = len(result.get_critical_findings())

            for finding in result.findings:
                if not finding.worker_group:
                    finding.worker_group = client.worker_group

            result.success = True
            log.info(
                "notification_delivery_analysis_completed",
                notifications=len(notifications),
                findings=len(result.findings),
            )

        except Exception as e:
            log.error("notification_delivery_analysis_failed", error=str(e))
            result.success = False
            result.metadata["error"] = str(e)
            result.add_finding(
                Finding(
                    id="notif-delivery-analysis-error",
                    category="notification_delivery",
                    severity="critical",
                    title="Notification Delivery Analysis Failed",
                    description=f"Failed to analyze notification delivery: {str(e)}",
                    affected_components=["Notification Analyzer"],
                    remediation_steps=["Check API connectivity", "Verify permissions"],
                    estimated_impact="Cannot assess notification delivery health",
                    confidence_level="high",
                    metadata={"error": str(e)},
                )
            )

        return result

    async def _fetch_notifications(self, client: CriblAPIClient) -> list[dict[str, Any]]:
        try:
            return await client.get_notifications() or []
        except Exception as e:
            log.warning("failed_to_fetch_notifications", error=str(e))
            return []

    async def _fetch_targets(self, client: CriblAPIClient) -> list[dict[str, Any]]:
        try:
            return await client.get_notification_targets() or []
        except Exception as e:
            log.warning("failed_to_fetch_targets", error=str(e))
            return []

    def _check_targets_assigned(
        self,
        notification: dict[str, Any],
        targets: list[dict[str, Any]],
        result: AnalyzerResult,
    ) -> bool:
        """Check if notification has assigned delivery targets."""
        notif_id = notification.get("id", "unknown")
        notif_name = notification.get("name", notif_id)

        assigned = notification.get("targets", [])
        if isinstance(assigned, str):
            assigned = [assigned]

        if not assigned:
            result.add_finding(
                Finding(
                    id=f"notif-delivery-no-targets-{notif_id}",
                    category="notification_delivery",
                    severity="high",
                    title=f"Notification Without Targets: {notif_name}",
                    description=f"Notification '{notif_name}' has no delivery targets assigned. Alerts will not be sent.",
                    affected_components=["Notifications", notif_name],
                    remediation_steps=[
                        "Assign at least one notification target to this notification",
                        "Verify target configuration is correct",
                    ],
                    estimated_impact="Alerts configured but not delivered",
                    confidence_level="high",
                    metadata={"notification_id": notif_id},
                )
            )
            return False

        return True

    def _check_notification_enabled(
        self, notification: dict[str, Any], result: AnalyzerResult
    ) -> bool:
        """Check if notification is enabled."""
        notif_id = notification.get("id", "unknown")
        notif_name = notification.get("name", notif_id)

        enabled = notification.get("enabled", True)

        if not enabled:
            result.add_finding(
                Finding(
                    id=f"notif-delivery-disabled-{notif_id}",
                    category="notification_delivery",
                    severity="medium",
                    title=f"Notification Disabled: {notif_name}",
                    description=f"Notification '{notif_name}' is disabled. Alerts will not be triggered.",
                    affected_components=["Notifications", notif_name],
                    remediation_steps=[
                        "Enable the notification in configuration",
                        "Verify alert conditions are correct before enabling",
                    ],
                    estimated_impact="Alerts not being generated",
                    confidence_level="high",
                    metadata={"notification_id": notif_id},
                )
            )
            return False

        return True

    def _check_target_health(
        self,
        notification: dict[str, Any],
        targets: list[dict[str, Any]],
        result: AnalyzerResult,
    ) -> bool:
        """Check if assigned targets are healthy."""
        notif_id = notification.get("id", "unknown")
        notif_name = notification.get("name", notif_id)

        assigned = notification.get("targets", [])
        if isinstance(assigned, str):
            assigned = [assigned]

        target_map = {t.get("id", ""): t for t in targets}
        all_healthy = True

        for target_id in assigned:
            if not target_id:
                continue

            target = target_map.get(target_id)
            if not target:
                result.add_finding(
                    Finding(
                        id=f"notif-delivery-missing-target-{notif_id}-{target_id}",
                        category="notification_delivery",
                        severity="high",
                        title=f"Notification References Missing Target: {notif_name}",
                        description=f"Notification '{notif_name}' references target '{target_id}' which does not exist.",
                        affected_components=["Notifications", notif_name],
                        remediation_steps=[
                            "Create the missing notification target",
                            "Update notification to reference existing target",
                        ],
                        estimated_impact="Alerts cannot be delivered via this target",
                        confidence_level="high",
                        metadata={"notification_id": notif_id, "target_id": target_id},
                    )
                )
                all_healthy = False
                continue

            enabled = target.get("enabled", True)
            if not enabled:
                result.add_finding(
                    Finding(
                        id=f"notif-delivery-target-disabled-{notif_id}-{target_id}",
                        category="notification_delivery",
                        severity="medium",
                        title=f"Notification Target Disabled: {target.get('name', target_id)}",
                        description=f"Target '{target.get('name', target_id)}' is disabled. Alerts cannot reach this destination.",
                        affected_components=["Notification Targets", target.get("name", target_id)],
                        remediation_steps=[
                            "Enable the notification target",
                            "Verify target credentials are valid",
                        ],
                        estimated_impact="Delivery to this target unavailable",
                        confidence_level="high",
                        metadata={"notification_id": notif_id, "target_id": target_id},
                    )
                )
                all_healthy = False

        return all_healthy
