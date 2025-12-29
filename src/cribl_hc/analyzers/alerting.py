"""
Alerting Infrastructure Analyzer for Cribl Health Check.

Analyzes notification targets and alert configurations to ensure
alerting infrastructure is properly configured for operational visibility.

Priority: P3 (Alerting - important for operational awareness)
"""

from typing import Any, Dict, List, Set
from cribl_hc.analyzers.base import BaseAnalyzer, AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.utils.logger import get_logger

log = get_logger(__name__)


class AlertingAnalyzer(BaseAnalyzer):
    """
    Analyzer for alerting infrastructure health.

    Identifies:
    - Missing notification targets
    - Disabled notifications
    - Notifications without targets
    - Missing critical alert types (PagerDuty, etc.)
    - Orphaned notification targets

    Priority: P3 (Alerting infrastructure - important for operational visibility)

    Example:
        >>> async with CriblAPIClient(url, token) as client:
        ...     analyzer = AlertingAnalyzer()
        ...     result = await analyzer.analyze(client)
        ...     print(f"Notification targets: {result.metadata['notification_targets_count']}")
    """

    # Recommended notification target types for production environments
    RECOMMENDED_TARGET_TYPES = {"slack", "pagerduty", "email", "webhook"}
    CRITICAL_TARGET_TYPES = {"pagerduty", "slack"}  # At least one of these

    @property
    def objective_name(self) -> str:
        """Return 'alerting' as the objective name."""
        return "alerting"

    @property
    def supported_products(self) -> List[str]:
        """Alerting analyzer applies to Stream, Edge, and Search."""
        return ["stream", "edge", "search"]

    def get_description(self) -> str:
        """Get human-readable description."""
        return "Alerting infrastructure health and notification configuration analysis"

    def get_estimated_api_calls(self) -> int:
        """
        Estimate API calls needed.

        - notification_targets(1) + notifications(1) = 2 calls
        """
        return 2

    def get_required_permissions(self) -> List[str]:
        """List required API permissions."""
        return [
            "read:notification-targets",
            "read:notifications",
        ]

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Analyze alerting infrastructure configuration.

        Checks notification targets and alert rules for completeness
        and proper configuration.

        Args:
            client: Authenticated Cribl API client

        Returns:
            AnalyzerResult with alerting infrastructure findings
        """
        result = AnalyzerResult(objective=self.objective_name)

        try:
            self.log.info("alerting_analysis_started")

            # Fetch notification targets and notifications
            targets = await self._fetch_notification_targets(client)
            notifications = await self._fetch_notifications(client)

            result.metadata["notification_targets_count"] = len(targets)
            result.metadata["notifications_count"] = len(notifications)

            # Analyze notification targets
            target_issues = self._analyze_notification_targets(targets, result)

            # Analyze notifications
            notification_issues = self._analyze_notifications(notifications, targets, result)

            # Check for critical alerting gaps
            self._check_critical_alerting_gaps(targets, notifications, result)

            # Generate recommendations
            self._generate_alerting_recommendations(
                targets, notifications, target_issues, notification_issues, result
            )

            # Calculate alerting health score
            alerting_score = self._calculate_alerting_score(
                targets, notifications, target_issues, notification_issues
            )
            result.metadata["alerting_health_score"] = alerting_score
            result.metadata["target_issues_count"] = len(target_issues)
            result.metadata["notification_issues_count"] = len(notification_issues)

            result.success = True
            self.log.info(
                "alerting_analysis_completed",
                targets=len(targets),
                notifications=len(notifications),
                findings=len(result.findings),
                alerting_score=alerting_score,
            )

        except Exception as e:
            self.log.error("alerting_analysis_failed", error=str(e))
            result.error = f"Alerting analysis failed: {str(e)}"
            result.success = False

        return result

    async def _fetch_notification_targets(
        self, client: CriblAPIClient
    ) -> List[Dict[str, Any]]:
        """Fetch notification target configurations."""
        try:
            return await client.get_notification_targets() or []
        except Exception as e:
            self.log.warning("failed_to_fetch_notification_targets", error=str(e))
            return []

    async def _fetch_notifications(
        self, client: CriblAPIClient
    ) -> List[Dict[str, Any]]:
        """Fetch notification configurations."""
        try:
            return await client.get_notifications() or []
        except Exception as e:
            self.log.warning("failed_to_fetch_notifications", error=str(e))
            return []

    def _analyze_notification_targets(
        self,
        targets: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> List[Dict[str, Any]]:
        """
        Analyze notification target configurations.

        Checks:
        - No targets configured
        - Target types in use
        - Disabled targets

        Args:
            targets: List of notification target configurations
            result: AnalyzerResult to add findings to

        Returns:
            List of target issues found
        """
        target_issues = []

        # Check for no targets configured
        if not targets:
            result.add_finding(Finding(
                id="alerting-no-targets",
                category="alerting",
                severity="high",
                title="No Notification Targets Configured",
                description=(
                    "No notification targets are configured. Alerts and notifications "
                    "will not be delivered. Configure at least one notification target "
                    "(Slack, PagerDuty, email, or webhook) for operational visibility."
                ),
                confidence_level="high",
                estimated_impact="No alerts will be delivered for system issues",
                remediation_steps=[
                    "Configure at least one notification target in Settings > Notification Targets",
                    "Recommended: Configure Slack for team notifications",
                    "Recommended: Configure PagerDuty for critical alerts",
                    "Test notification delivery after configuration"
                ],
                documentation_links=[
                    "https://docs.cribl.io/stream/notifications-targets/"
                ],
                metadata={}
            ))
            target_issues.append({"issue": "no_targets"})
            return target_issues

        # Analyze target types
        target_types: Set[str] = set()
        disabled_targets: List[str] = []
        targets_by_type: Dict[str, List[str]] = {}

        for target in targets:
            target_id = target.get("id", "unknown")
            target_type = target.get("type", "unknown").lower()
            enabled = target.get("enabled", True)

            target_types.add(target_type)
            targets_by_type.setdefault(target_type, []).append(target_id)

            if not enabled:
                disabled_targets.append(target_id)

        result.metadata["target_types"] = list(target_types)
        result.metadata["targets_by_type"] = targets_by_type

        # Check for disabled targets
        if disabled_targets:
            result.add_finding(Finding(
                id="alerting-disabled-targets",
                category="alerting",
                severity="low",
                title=f"Disabled Notification Targets: {len(disabled_targets)} Found",
                description=(
                    f"{len(disabled_targets)} notification target(s) are disabled: "
                    f"{', '.join(disabled_targets)}. Ensure these are intentionally disabled."
                ),
                confidence_level="high",
                remediation_steps=[
                    "Review disabled targets to ensure they're intentionally disabled",
                    "Re-enable targets that should be active",
                    "Remove targets that are no longer needed"
                ],
                affected_components=disabled_targets,
                metadata={"disabled_targets": disabled_targets}
            ))
            target_issues.append({"issue": "disabled_targets", "count": len(disabled_targets)})

        # Check for missing critical target types
        has_critical = bool(target_types & self.CRITICAL_TARGET_TYPES)
        if not has_critical:
            result.add_finding(Finding(
                id="alerting-no-critical-targets",
                category="alerting",
                severity="medium",
                title="No Critical Alerting Integration",
                description=(
                    "No critical alerting integration (PagerDuty or Slack) is configured. "
                    "Consider adding at least one for timely incident response."
                ),
                confidence_level="high",
                remediation_steps=[
                    "Configure PagerDuty integration for on-call alerting",
                    "Or configure Slack integration for team notifications",
                    "Ensure critical alerts are routed to these targets"
                ],
                documentation_links=[
                    "https://docs.cribl.io/stream/pager-duty-notification-targets/",
                    "https://docs.cribl.io/stream/slack-notification-targets/"
                ],
                metadata={"configured_types": list(target_types)}
            ))
            target_issues.append({"issue": "no_critical_targets"})

        return target_issues

    def _analyze_notifications(
        self,
        notifications: List[Dict[str, Any]],
        targets: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> List[Dict[str, Any]]:
        """
        Analyze notification configurations.

        Checks:
        - No notifications configured
        - Disabled notifications
        - Notifications without targets
        - Notifications with invalid targets

        Args:
            notifications: List of notification configurations
            targets: List of notification targets (for validation)
            result: AnalyzerResult to add findings to

        Returns:
            List of notification issues found
        """
        notification_issues = []

        if not notifications:
            # Only warn if targets exist but no notifications use them
            if targets:
                result.add_finding(Finding(
                    id="alerting-no-notifications",
                    category="alerting",
                    severity="medium",
                    title="No Notifications Configured",
                    description=(
                        "Notification targets are configured but no notifications are defined. "
                        "Configure notifications to receive alerts for system events."
                    ),
                    confidence_level="high",
                    remediation_steps=[
                        "Create notifications for critical events (worker offline, high CPU, etc.)",
                        "Assign appropriate notification targets",
                        "Test notification delivery"
                    ],
                    metadata={"target_count": len(targets)}
                ))
                notification_issues.append({"issue": "no_notifications"})
            return notification_issues

        # Build target ID lookup
        valid_target_ids = {t.get("id") for t in targets}

        # Analyze each notification
        disabled_count = 0
        no_targets_count = 0
        invalid_targets: List[Dict[str, Any]] = []

        for notification in notifications:
            notification_id = notification.get("id", "unknown")
            enabled = notification.get("enabled", True)
            notification_targets = notification.get("targets", [])

            if not enabled:
                disabled_count += 1

            # Check for notifications without targets
            if not notification_targets:
                no_targets_count += 1
                result.add_finding(Finding(
                    id=f"alerting-notification-no-targets-{notification_id}",
                    category="alerting",
                    severity="medium",
                    title=f"Notification Without Targets: {notification_id}",
                    description=(
                        f"Notification '{notification_id}' has no targets configured. "
                        f"This notification will not be delivered."
                    ),
                    confidence_level="high",
                    remediation_steps=[
                        f"Add notification targets to '{notification_id}'",
                        "Or disable/remove if no longer needed"
                    ],
                    metadata={"notification_id": notification_id}
                ))
                notification_issues.append({"issue": "no_targets", "notification": notification_id})

            # Check for invalid target references
            for target_ref in notification_targets:
                target_id = target_ref if isinstance(target_ref, str) else target_ref.get("id")
                if target_id and target_id not in valid_target_ids:
                    invalid_targets.append({
                        "notification": notification_id,
                        "invalid_target": target_id
                    })

        # Report disabled notifications
        if disabled_count > 0:
            result.add_finding(Finding(
                id="alerting-disabled-notifications",
                category="alerting",
                severity="low",
                title=f"Disabled Notifications: {disabled_count} Found",
                description=(
                    f"{disabled_count} notification(s) are disabled. "
                    f"Review to ensure these are intentionally disabled."
                ),
                confidence_level="high",
                remediation_steps=[
                    "Review disabled notifications",
                    "Re-enable or remove as appropriate"
                ],
                metadata={"disabled_count": disabled_count}
            ))
            notification_issues.append({"issue": "disabled_notifications", "count": disabled_count})

        # Report invalid target references
        if invalid_targets:
            result.add_finding(Finding(
                id="alerting-invalid-target-refs",
                category="alerting",
                severity="high",
                title=f"Notifications with Invalid Targets: {len(invalid_targets)} Found",
                description=(
                    "Some notifications reference targets that don't exist. "
                    "These notifications will fail to deliver."
                ),
                confidence_level="high",
                remediation_steps=[
                    "Update notifications to use valid target IDs",
                    "Or create the missing notification targets",
                    "Remove orphaned target references"
                ],
                metadata={"invalid_targets": invalid_targets}
            ))
            notification_issues.append({"issue": "invalid_targets", "count": len(invalid_targets)})

        return notification_issues

    def _check_critical_alerting_gaps(
        self,
        targets: List[Dict[str, Any]],
        notifications: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Check for critical gaps in alerting infrastructure.

        Args:
            targets: List of notification targets
            notifications: List of notifications
            result: AnalyzerResult to add findings to
        """
        # Check if there's any working alerting at all
        enabled_targets = [t for t in targets if t.get("enabled", True)]
        enabled_notifications = [n for n in notifications if n.get("enabled", True)]

        if not enabled_targets or not enabled_notifications:
            result.add_finding(Finding(
                id="alerting-no-active-alerts",
                category="alerting",
                severity="high",
                title="No Active Alerting Configuration",
                description=(
                    "No active alerting configuration detected. "
                    f"Enabled targets: {len(enabled_targets)}, "
                    f"Enabled notifications: {len(enabled_notifications)}. "
                    "System events will not trigger alerts."
                ),
                confidence_level="high",
                estimated_impact="No visibility into system issues through alerts",
                remediation_steps=[
                    "Enable at least one notification target",
                    "Configure notifications for critical events",
                    "Test end-to-end alert delivery"
                ],
                metadata={
                    "enabled_targets": len(enabled_targets),
                    "enabled_notifications": len(enabled_notifications)
                }
            ))

    def _generate_alerting_recommendations(
        self,
        targets: List[Dict[str, Any]],
        notifications: List[Dict[str, Any]],
        target_issues: List[Dict[str, Any]],
        notification_issues: List[Dict[str, Any]],
        result: AnalyzerResult
    ) -> None:
        """
        Generate recommendations for improving alerting infrastructure.

        Args:
            targets: List of notification targets
            notifications: List of notifications
            target_issues: Issues found with targets
            notification_issues: Issues found with notifications
            result: AnalyzerResult to add recommendations to
        """
        # Recommend PagerDuty if not configured
        target_types = {t.get("type", "").lower() for t in targets}
        if "pagerduty" not in target_types and targets:
            result.add_recommendation(Recommendation(
                id="alerting-add-pagerduty",
                type="alerting",
                priority="p2",
                title="Add PagerDuty Integration for On-Call Alerting",
                description=(
                    "PagerDuty integration is not configured. Consider adding "
                    "PagerDuty for on-call alerting and incident management."
                ),
                rationale=(
                    "PagerDuty provides robust on-call scheduling, escalation policies, "
                    "and incident tracking that complement Cribl's alerting"
                ),
                implementation_steps=[
                    "Create PagerDuty service for Cribl alerts",
                    "Generate integration key in PagerDuty",
                    "Configure PagerDuty notification target in Cribl",
                    "Route critical alerts to PagerDuty",
                    "Configure escalation policies in PagerDuty"
                ],
                before_state="Alerts only sent to existing channels",
                after_state="Critical alerts trigger PagerDuty incidents",
                impact_estimate=ImpactEstimate(
                    performance_improvement="Reduced MTTR through on-call integration"
                ),
                implementation_effort="low",
                documentation_links=[
                    "https://docs.cribl.io/stream/pager-duty-notification-targets/"
                ]
            ))

        # Recommend alert documentation
        if len(notifications) > 5:
            result.add_recommendation(Recommendation(
                id="alerting-document-alerts",
                type="alerting",
                priority="p3",
                title="Document Alert Runbooks",
                description=(
                    f"You have {len(notifications)} notifications configured. "
                    "Ensure runbooks exist for responding to each alert type."
                ),
                rationale=(
                    "Documented runbooks reduce incident response time and "
                    "ensure consistent handling of alerts"
                ),
                implementation_steps=[
                    "Create runbook for each notification type",
                    "Include investigation steps and remediation actions",
                    "Link runbooks from alert messages where possible",
                    "Review and update runbooks regularly"
                ],
                implementation_effort="medium",
            ))

    def _calculate_alerting_score(
        self,
        targets: List[Dict[str, Any]],
        notifications: List[Dict[str, Any]],
        target_issues: List[Dict[str, Any]],
        notification_issues: List[Dict[str, Any]]
    ) -> int:
        """
        Calculate alerting infrastructure health score (0-100).

        Args:
            targets: List of notification targets
            notifications: List of notifications
            target_issues: Issues found with targets
            notification_issues: Issues found with notifications

        Returns:
            Health score from 0 to 100
        """
        score = 100

        # No targets configured = major penalty
        if not targets:
            score -= 50

        # No notifications = moderate penalty
        if not notifications:
            score -= 30

        # Deduct for each issue type
        for issue in target_issues:
            if issue.get("issue") == "no_targets":
                score -= 30
            elif issue.get("issue") == "no_critical_targets":
                score -= 15
            elif issue.get("issue") == "disabled_targets":
                score -= 5

        for issue in notification_issues:
            if issue.get("issue") == "no_notifications":
                score -= 20
            elif issue.get("issue") == "no_targets":
                score -= 10
            elif issue.get("issue") == "invalid_targets":
                score -= 15
            elif issue.get("issue") == "disabled_notifications":
                score -= 5

        return max(0, score)
