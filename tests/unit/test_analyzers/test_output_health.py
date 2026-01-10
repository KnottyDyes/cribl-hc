import pytest
from unittest.mock import AsyncMock, MagicMock

from cribl_hc.analyzers.output_health import OutputDestinationAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


def create_output(
    output_id: str,
    output_type: str = "splunk",
    status: str = "healthy",
    enabled: bool = True,
    token: str = "valid-token",
    ack_enabled: bool = True,
) -> dict:
    return {
        "id": output_id,
        "type": output_type,
        "status": {"health": status},
        "enabled": enabled,
        "token": token,
        "ackEnabled": ack_enabled,
        "enableAck": ack_enabled,
    }


def create_output_metrics(
    output_id: str, events: int = 1000, errors: int = 0, queue_size: int = 0
) -> list:
    return [
        {"dimensions": {"output": output_id}, "name": "send.events", "value": events},
        {"dimensions": {"output": output_id}, "name": "send.errors", "value": errors},
        {"dimensions": {"output": output_id}, "name": "queue.size", "value": queue_size},
    ]


class TestOutputDestinationAnalyzer:
    """Test suite for OutputDestinationAnalyzer."""

    @pytest.fixture
    def mock_client(self):
        client = AsyncMock(spec=CriblAPIClient)
        client.get_outputs = AsyncMock(return_value=[])
        client.get_metrics = AsyncMock(return_value={})
        return client

    @pytest.mark.asyncio
    async def test_healthy_outputs_no_findings(self, mock_client):
        """Test that healthy outputs produce no findings."""
        outputs = [
            create_output("out-1", status="healthy"),
            create_output("out-2", status="healthy"),
        ]

        metrics = {"items": []}
        metrics["items"].extend(create_output_metrics("out-1", events=1000, errors=0))
        metrics["items"].extend(create_output_metrics("out-2", events=2000, errors=0))

        mock_client.get_outputs.return_value = outputs
        mock_client.get_metrics.return_value = metrics

        analyzer = OutputDestinationAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 0
        assert result.metadata["outputs_analyzed"] == 2
        assert result.metadata["healthy_outputs"] == 2

    @pytest.mark.asyncio
    async def test_unreachable_output_critical(self, mock_client):
        """Test that unreachable output is flagged as CRITICAL."""
        outputs = [create_output("out-dead", status="dead")]

        mock_client.get_outputs.return_value = outputs
        mock_client.get_metrics.return_value = {"items": []}

        analyzer = OutputDestinationAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "critical"
        assert finding.id == "output-unreachable-out-dead"

    @pytest.mark.asyncio
    async def test_missing_credentials_high(self, mock_client):
        """Test that missing credentials for splunk_hec is flagged as HIGH."""
        outputs = [create_output("out-no-auth", output_type="splunk_hec", token="")]

        mock_client.get_outputs.return_value = outputs
        mock_client.get_metrics.return_value = {"items": []}

        analyzer = OutputDestinationAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "high"
        assert "Missing Authentication" in finding.title

    @pytest.mark.asyncio
    async def test_deprecated_output_type(self, mock_client):
        """Test that deprecated output type is flagged as MEDIUM."""
        outputs = [create_output("out-legacy", output_type="splunk_hec_legacy")]

        mock_client.get_outputs.return_value = outputs
        mock_client.get_metrics.return_value = {"items": []}

        analyzer = OutputDestinationAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "medium"
        assert "Deprecated Output Type" in finding.title

    @pytest.mark.asyncio
    async def test_error_rate_high(self, mock_client):
        """Test that error rate > 5% is flagged as HIGH."""
        outputs = [create_output("out-err")]

        # 7% error rate: 70 errors, 930 success = 1000 total
        metrics = {"items": create_output_metrics("out-err", events=930, errors=70)}

        mock_client.get_outputs.return_value = outputs
        mock_client.get_metrics.return_value = metrics

        analyzer = OutputDestinationAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "high"
        assert finding.id == "output-elevated-error-rate-out-err"
        assert round(finding.metadata["error_rate"], 1) == 7.0

    @pytest.mark.asyncio
    async def test_error_rate_critical(self, mock_client):
        """Test that error rate > 10% is flagged as CRITICAL."""
        outputs = [create_output("out-err-crit")]

        # 12% error rate: 120 errors, 880 success = 1000 total
        metrics = {"items": create_output_metrics("out-err-crit", events=880, errors=120)}

        mock_client.get_outputs.return_value = outputs
        mock_client.get_metrics.return_value = metrics

        analyzer = OutputDestinationAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "critical"
        assert finding.id == "output-high-error-rate-out-err-crit"
        assert finding.metadata["error_rate"] == 12.0

    @pytest.mark.asyncio
    async def test_queue_backing_up(self, mock_client):
        """Test that queue size > 10000 is flagged as MEDIUM."""
        outputs = [create_output("out-queue")]

        metrics = {"items": create_output_metrics("out-queue", queue_size=15000)}

        mock_client.get_outputs.return_value = outputs
        mock_client.get_metrics.return_value = metrics

        analyzer = OutputDestinationAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "medium"
        assert "Queue Backing Up" in finding.title
        assert finding.metadata["queue_size"] == 15000

    @pytest.mark.asyncio
    async def test_delivery_confirmation_disabled(self, mock_client):
        """Test that disabled delivery confirmation for critical types is flagged as MEDIUM."""
        outputs = [create_output("out-no-ack", output_type="splunk", ack_enabled=False)]

        mock_client.get_outputs.return_value = outputs
        mock_client.get_metrics.return_value = {"items": []}

        analyzer = OutputDestinationAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "medium"
        assert "Delivery Confirmation Disabled" in finding.title

    @pytest.mark.asyncio
    async def test_no_outputs_available(self, mock_client):
        """Test behavior when no outputs are configured."""
        mock_client.get_outputs.return_value = []
        mock_client.get_metrics.return_value = {"items": []}

        analyzer = OutputDestinationAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 0
        assert result.metadata["outputs_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_client):
        """Test graceful handling of API errors during output fetch."""
        # When get_outputs fails, analyzer gracefully returns empty list (graceful degradation)
        mock_client.get_outputs.side_effect = Exception("API Failure")
        mock_client.get_metrics.return_value = {"items": []}

        analyzer = OutputDestinationAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should succeed with no findings (empty list handled gracefully)
        assert result.success is True
        assert len(result.findings) == 0
        assert result.metadata["outputs_analyzed"] == 0
