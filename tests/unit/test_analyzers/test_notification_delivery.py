import pytest
from unittest.mock import AsyncMock

from cribl_hc.analyzers.notification_delivery import NotificationDeliveryAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


def create_notification(
    notif_id: str, name: str = "test_notif", enabled: bool = True, targets: list = None
) -> dict:
    if targets is None:
        targets = ["target-1"]
    return {
        "id": notif_id,
        "name": name,
        "enabled": enabled,
        "targets": targets,
    }


def create_target(
    target_id: str,
    name: str = "slack_target",
    enabled: bool = True,
) -> dict:
    return {
        "id": target_id,
        "name": name,
        "enabled": enabled,
        "type": "slack",
    }


class TestNotificationDeliveryAnalyzer:
    @pytest.fixture
    def mock_client(self):
        client = AsyncMock(spec=CriblAPIClient)
        client.get_notifications = AsyncMock(return_value=[])
        client.get_notification_targets = AsyncMock(return_value=[])
        client.worker_group = "default"
        return client

    @pytest.mark.asyncio
    async def test_healthy_notifications(self, mock_client):
        notifications = [create_notification("notif-1")]
        targets = [create_target("target-1")]

        mock_client.get_notifications.return_value = notifications
        mock_client.get_notification_targets.return_value = targets

        analyzer = NotificationDeliveryAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["notifications_analyzed"] == 1
        assert result.metadata["targets_analyzed"] == 1

    @pytest.mark.asyncio
    async def test_notification_no_targets(self, mock_client):
        notifications = [create_notification("notif-no-targets", targets=[])]
        targets = [create_target("target-1")]

        mock_client.get_notifications.return_value = notifications
        mock_client.get_notification_targets.return_value = targets

        analyzer = NotificationDeliveryAnalyzer()
        result = await analyzer.analyze(mock_client)

        findings = [f for f in result.findings if "no-targets" in f.id.lower()]
        assert len(findings) >= 1
        assert findings[0].severity == "high"

    @pytest.mark.asyncio
    async def test_notification_disabled(self, mock_client):
        notifications = [create_notification("notif-disabled", enabled=False)]
        targets = [create_target("target-1")]

        mock_client.get_notifications.return_value = notifications
        mock_client.get_notification_targets.return_value = targets

        analyzer = NotificationDeliveryAnalyzer()
        result = await analyzer.analyze(mock_client)

        findings = [f for f in result.findings if "disabled" in f.id.lower()]
        assert len(findings) >= 1
        assert findings[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_missing_target(self, mock_client):
        notifications = [create_notification("notif-1", targets=["target-missing"])]
        targets = [create_target("target-1")]

        mock_client.get_notifications.return_value = notifications
        mock_client.get_notification_targets.return_value = targets

        analyzer = NotificationDeliveryAnalyzer()
        result = await analyzer.analyze(mock_client)

        findings = [f for f in result.findings if "missing-target" in f.id.lower()]
        assert len(findings) >= 1
        assert findings[0].severity == "high"

    @pytest.mark.asyncio
    async def test_target_disabled(self, mock_client):
        notifications = [create_notification("notif-1", targets=["target-1"])]
        targets = [create_target("target-1", enabled=False)]

        mock_client.get_notifications.return_value = notifications
        mock_client.get_notification_targets.return_value = targets

        analyzer = NotificationDeliveryAnalyzer()
        result = await analyzer.analyze(mock_client)

        findings = [f for f in result.findings if "target-disabled" in f.id.lower()]
        assert len(findings) >= 1
        assert findings[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_no_notifications_configured(self, mock_client):
        mock_client.get_notifications.return_value = []
        mock_client.get_notification_targets.return_value = [create_target("target-1")]

        analyzer = NotificationDeliveryAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        assert "no-notifications" in result.findings[0].id.lower()

    @pytest.mark.asyncio
    async def test_no_targets_configured(self, mock_client):
        notifications = [create_notification("notif-1")]

        mock_client.get_notifications.return_value = notifications
        mock_client.get_notification_targets.return_value = []

        analyzer = NotificationDeliveryAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        assert "no-targets" in result.findings[0].id.lower()
        assert result.findings[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_client):
        mock_client.get_notifications.side_effect = Exception("API Failure")

        analyzer = NotificationDeliveryAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["notifications_analyzed"] == 0
        assert len(result.findings) == 1
