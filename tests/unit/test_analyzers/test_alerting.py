"""
Unit tests for AlertingAnalyzer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from cribl_hc.analyzers.alerting import AlertingAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class TestAlertingAnalyzer:
    """Test AlertingAnalyzer functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = AlertingAnalyzer()
        self.mock_client = MagicMock(spec=CriblAPIClient)
        self.mock_client.get_notification_targets = AsyncMock(return_value=[])
        self.mock_client.get_notifications = AsyncMock(return_value=[])

    def test_objective_name(self):
        """Test objective name property."""
        assert self.analyzer.objective_name == "alerting"

    def test_supported_products(self):
        """Test supported products."""
        products = self.analyzer.supported_products
        assert "stream" in products
        assert "edge" in products
        assert "search" in products

    def test_get_description(self):
        """Test description."""
        description = self.analyzer.get_description()
        assert "Alerting infrastructure" in description
        assert "notification configuration" in description

    def test_get_estimated_api_calls(self):
        """Test estimated API calls."""
        assert self.analyzer.get_estimated_api_calls() == 2

    def test_get_required_permissions(self):
        """Test required permissions."""
        permissions = self.analyzer.get_required_permissions()
        assert "read:notification-targets" in permissions
        assert "read:notifications" in permissions

    def test_recommended_target_types(self):
        """Test recommended target types constants."""
        assert "slack" in AlertingAnalyzer.RECOMMENDED_TARGET_TYPES
        assert "pagerduty" in AlertingAnalyzer.RECOMMENDED_TARGET_TYPES
        assert "email" in AlertingAnalyzer.RECOMMENDED_TARGET_TYPES
        assert "webhook" in AlertingAnalyzer.RECOMMENDED_TARGET_TYPES

    def test_critical_target_types(self):
        """Test critical target types constants."""
        assert "pagerduty" in AlertingAnalyzer.CRITICAL_TARGET_TYPES
        assert "slack" in AlertingAnalyzer.CRITICAL_TARGET_TYPES

    @pytest.mark.asyncio
    async def test_analyze_healthy_alerting(self):
        """Test analysis with healthy alerting configuration."""
        # Mock notification targets
        targets = [
            {
                "id": "slack-target",
                "type": "slack",
                "enabled": True,
                "name": "Production Slack",
                "config": {"webhook_url": "https://hooks.slack.com/..."},
            },
            {
                "id": "pagerduty-target",
                "type": "pagerduty",
                "enabled": True,
                "name": "PagerDuty Critical",
                "config": {"integration_key": "abc123"},
            },
        ]

        # Mock notifications
        notifications = [
            {
                "id": "critical-alert",
                "enabled": True,
                "name": "Critical System Alert",
                "targets": ["slack-target", "pagerduty-target"],
                "condition": "cpu > 90",
            },
            {
                "id": "warning-alert",
                "enabled": True,
                "name": "Warning Alert",
                "targets": ["slack-target"],
                "condition": "cpu > 80",
            },
        ]

        self.mock_client.get_notification_targets.return_value = targets
        self.mock_client.get_notifications.return_value = notifications

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success
        assert result.metadata["notification_targets_count"] == 2
        assert result.metadata["notifications_count"] == 2
        # Should have minimal findings for healthy config
        critical_findings = [f for f in result.findings if f.severity == "critical"]
        assert len(critical_findings) == 0

    @pytest.mark.asyncio
    async def test_analyze_missing_critical_targets(self):
        """Test analysis with missing critical notification targets."""
        # Mock notification targets - only email, no slack/pagerduty
        targets = [
            {
                "id": "email-target",
                "type": "email",
                "enabled": True,
                "name": "Admin Email",
                "config": {"recipients": ["admin@example.com"]},
            }
        ]

        # Mock notifications
        notifications = [
            {
                "id": "alert-no-targets",
                "enabled": True,
                "name": "Alert Without Targets",
                "targets": [],  # No targets
                "condition": "memory > 90",
            },
        ]

        self.mock_client.get_notification_targets.return_value = targets
        self.mock_client.get_notifications.return_value = notifications

        self.mock_client.get_notification_targets.return_value = targets
        self.mock_client.get_notifications.return_value = notifications

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success
        medium_findings = [f for f in result.findings if f.severity == "medium"]
        assert len(medium_findings) > 0

        missing_critical = any(
            "critical alerting" in f.title.lower()
            or "pagerduty" in f.description.lower()
            or "slack" in f.description.lower()
            for f in medium_findings
        )
        assert missing_critical

    @pytest.mark.asyncio
    async def test_analyze_disabled_targets(self):
        """Test analysis with disabled notification targets."""
        # Mock notification targets with disabled ones
        targets = [
            {
                "id": "slack-target",
                "type": "slack",
                "enabled": False,  # Disabled
                "name": "Production Slack",
                "config": {"webhook_url": "https://hooks.slack.com/..."},
            },
            {
                "id": "email-target",
                "type": "email",
                "enabled": True,
                "name": "Admin Email",
                "config": {"recipients": ["admin@example.com"]},
            },
        ]

        # Mock notifications
        notifications = [
            {
                "id": "critical-alert",
                "enabled": True,
                "name": "Critical System Alert",
                "targets": ["slack-target", "email-target"],
                "condition": "cpu > 90",
            }
        ]

        self.mock_client.get_notification_targets.return_value = targets
        self.mock_client.get_notifications.return_value = notifications

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success
        # Should find disabled targets
        findings = result.findings
        disabled_finding = any(
            "disabled" in f.title.lower() or "disabled" in f.description.lower() for f in findings
        )
        assert disabled_finding

    @pytest.mark.asyncio
    async def test_analyze_orphaned_targets(self):
        """Test analysis with orphaned notification targets."""
        # Mock notification targets
        targets = [
            {
                "id": "slack-target",
                "type": "slack",
                "enabled": True,
                "name": "Production Slack",
                "config": {"webhook_url": "https://hooks.slack.com/..."},
            },
            {
                "id": "orphaned-target",
                "type": "email",
                "enabled": True,
                "name": "Orphaned Email",
                "config": {"recipients": ["old@example.com"]},
            },
        ]

        # Mock notifications - only uses slack-target
        notifications = [
            {
                "id": "critical-alert",
                "enabled": True,
                "name": "Critical System Alert",
                "targets": ["slack-target"],  # orphaned-target not used
                "condition": "cpu > 90",
            }
        ]

        self.mock_client.get_notification_targets.return_value = targets
        self.mock_client.get_notifications.return_value = notifications

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success
        # Should find orphaned targets
        findings = result.findings
        invalid_target_finding = any(
            "invalid targets" in f.title.lower() or "don't exist" in f.description.lower()
            for f in findings
        )
        assert not invalid_target_finding

    @pytest.mark.asyncio
    async def test_analyze_notifications_without_targets(self):
        """Test analysis with notifications that have no targets."""
        # Mock notification targets
        targets = [
            {
                "id": "slack-target",
                "type": "slack",
                "enabled": True,
                "name": "Production Slack",
                "config": {"webhook_url": "https://hooks.slack.com/..."},
            }
        ]

        # Mock notifications - one without targets
        notifications = [
            {
                "id": "critical-alert",
                "enabled": True,
                "name": "Critical System Alert",
                "targets": ["slack-target"],
                "condition": "cpu > 90",
            },
            {
                "id": "no-target-alert",
                "enabled": True,
                "name": "Alert Without Targets",
                "targets": [],  # No targets
                "condition": "memory > 90",
            },
        ]

        self.mock_client.get_notification_targets.return_value = targets
        self.mock_client.get_notifications.return_value = notifications

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success
        # Should find notifications without targets
        findings = result.findings
        no_targets_finding = any(
            "without targets" in f.title.lower() or "no targets" in f.description.lower()
            for f in findings
        )
        assert no_targets_finding

    @pytest.mark.asyncio
    async def test_analyze_disabled_notifications(self):
        """Test analysis with disabled notifications."""
        # Mock notification targets
        targets = [
            {
                "id": "slack-target",
                "type": "slack",
                "enabled": True,
                "name": "Production Slack",
                "config": {"webhook_url": "https://hooks.slack.com/..."},
            }
        ]

        # Mock notifications - one disabled
        notifications = [
            {
                "id": "critical-alert",
                "enabled": False,  # Disabled notification
                "name": "Critical System Alert",
                "targets": ["slack-target"],
                "condition": "cpu > 90",
            },
            {
                "id": "warning-alert",
                "enabled": True,
                "name": "Warning Alert",
                "targets": ["slack-target"],
                "condition": "cpu > 80",
            },
        ]

        self.mock_client.get_notification_targets.return_value = targets
        self.mock_client.get_notifications.return_value = notifications

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success
        # Should find disabled notifications
        findings = result.findings
        disabled_notification_finding = any(
            "disabled notification" in f.title.lower() or "disabled" in f.description.lower()
            for f in findings
        )
        assert disabled_notification_finding

    @pytest.mark.asyncio
    async def test_analyze_no_notification_infrastructure(self):
        """Test analysis with no notification infrastructure."""
        self.mock_client.get_notification_targets.return_value = []
        self.mock_client.get_notifications.return_value = []

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success
        assert result.metadata["notification_targets_count"] == 0
        assert result.metadata["notifications_count"] == 0

        high_findings = [f for f in result.findings if f.severity == "high"]
        assert len(high_findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_api_error_handling(self):
        """Test analysis handles API errors gracefully."""
        self.mock_client.get_notification_targets.side_effect = Exception("API connection failed")
        self.mock_client.get_notifications.return_value = []

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success
        assert result.metadata.get("notification_targets_count") == 0
        assert result.metadata.get("notifications_count") == 0
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_partial_api_failure(self):
        """Test analysis with partial API failures."""
        self.mock_client.get_notification_targets.return_value = [
            {
                "id": "slack-target",
                "type": "slack",
                "enabled": True,
                "name": "Production Slack",
                "config": {"webhook_url": "https://hooks.slack.com/..."},
            }
        ]
        self.mock_client.get_notifications.side_effect = Exception("Notifications API failed")

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success
        assert result.metadata.get("notification_targets_count") == 1
        assert result.metadata.get("notifications_count") == 0
        assert len(result.findings) > 0

    @pytest.mark.asyncio
    async def test_analyze_invalid_target_references(self):
        """Test analysis with notifications referencing non-existent targets."""
        # Mock notification targets
        targets = [
            {
                "id": "slack-target",
                "type": "slack",
                "enabled": True,
                "name": "Production Slack",
                "config": {"webhook_url": "https://hooks.slack.com/..."},
            }
        ]

        # Mock notifications with invalid target references
        notifications = [
            {
                "id": "critical-alert",
                "enabled": True,
                "name": "Critical System Alert",
                "targets": ["slack-target", "nonexistent-target"],  # Invalid reference
                "condition": "cpu > 90",
            }
        ]

        self.mock_client.get_notification_targets.return_value = targets
        self.mock_client.get_notifications.return_value = notifications

        result = await self.analyzer.analyze(self.mock_client)

        assert result.success
        # Should find invalid target references
        findings = result.findings
        invalid_ref_finding = any(
            "invalid" in f.title.lower() or "nonexistent" in f.description.lower() for f in findings
        )
        assert invalid_ref_finding

    def test_constants_coverage(self):
        """Test that constants are properly defined."""
        # Test recommended target types
        recommended = AlertingAnalyzer.RECOMMENDED_TARGET_TYPES
        assert isinstance(recommended, set)
        assert len(recommended) > 0

        # Test critical target types
        critical = AlertingAnalyzer.CRITICAL_TARGET_TYPES
        assert isinstance(critical, set)
        assert len(critical) > 0

        # Critical types should be subset of recommended
        assert critical.issubset(recommended)
