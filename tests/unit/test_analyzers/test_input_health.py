import pytest
import time
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

from cribl_hc.analyzers.input_health import InputSourceAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


# Helper functions for generating test data
def create_input(
    input_id: str,
    status: str = "healthy",
    input_type: str = "splunk",
    last_event_time: Optional[float] = None,
    disabled: bool = False,
) -> dict:
    if last_event_time is None:
        last_event_time = time.time()

    return {
        "id": input_id,
        "type": input_type,
        "disabled": disabled,
        "status": {
            "health": status,
            "lastEventTime": int(last_event_time * 1000),  # milliseconds
        },
    }


def create_metrics(inputs_data: dict) -> dict:
    return {"inputs": inputs_data}


def create_input_metric(
    events_in: int = 1000, bytes_in: int = 10000, errors: int = 0, queue_size: int = 0
) -> dict:
    return {
        "in": {"events": events_in, "bytes": bytes_in},
        "errors": errors,
        "queue": {"size": queue_size},
    }


class TestInputSourceAnalyzer:
    """Test suite for InputSourceAnalyzer."""

    @pytest.fixture
    def mock_client(self):
        client = AsyncMock(spec=CriblAPIClient)
        client.get_inputs = AsyncMock(return_value=[])
        client.get_metrics = AsyncMock(return_value={})
        return client

    @pytest.mark.asyncio
    async def test_healthy_inputs_no_findings(self, mock_client):
        """Test that healthy inputs produce no findings."""
        inputs = [
            create_input("input-1", status="healthy"),
            create_input("input-2", status="healthy"),
        ]

        metrics_data = {
            "input-1": create_input_metric(events_in=1000, errors=0),
            "input-2": create_input_metric(events_in=2000, errors=0),
        }

        mock_client.get_inputs.return_value = inputs
        mock_client.get_metrics.return_value = create_metrics(metrics_data)

        analyzer = InputSourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 0
        assert result.metadata["inputs_analyzed"] == 2
        assert result.metadata["healthy_inputs"] == 2
        assert result.metadata["total_errors"] == 0

    @pytest.mark.asyncio
    async def test_disconnected_input_critical(self, mock_client):
        """Test that disconnected input is flagged as CRITICAL."""
        inputs = [create_input("input-bad", status="disconnected")]

        mock_client.get_inputs.return_value = inputs
        # Metrics might be empty or present
        mock_client.get_metrics.return_value = create_metrics({})

        analyzer = InputSourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "critical"
        assert finding.id == "input-connectivity-input-bad"
        assert "Disconnected" in finding.title

    @pytest.mark.asyncio
    async def test_data_lag_high_severity(self, mock_client):
        """Test that input with > 5 min lag is flagged as HIGH."""
        current_time = time.time()
        # 10 minutes ago
        lag_time = current_time - (10 * 60)

        inputs = [create_input("input-lag", status="healthy", last_event_time=lag_time)]

        mock_client.get_inputs.return_value = inputs
        mock_client.get_metrics.return_value = create_metrics(
            {"input-lag": create_input_metric(events_in=0)}
        )

        analyzer = InputSourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "high"
        assert finding.id == "input-lag-input-lag"
        assert "Data Lag" in finding.title

    @pytest.mark.asyncio
    async def test_data_lag_critical_severity(self, mock_client):
        """Test that input with > 60 min lag is flagged as CRITICAL."""
        current_time = time.time()
        # 70 minutes ago
        lag_time = current_time - (70 * 60)

        inputs = [create_input("input-lag-crit", status="healthy", last_event_time=lag_time)]

        mock_client.get_inputs.return_value = inputs
        mock_client.get_metrics.return_value = create_metrics(
            {"input-lag-crit": create_input_metric(events_in=0)}
        )

        analyzer = InputSourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "critical"
        assert "Data Lag" in finding.title

    @pytest.mark.asyncio
    async def test_error_rate_high(self, mock_client):
        """Test that error rate > 5% is flagged as HIGH."""
        inputs = [create_input("input-err")]

        # 7% error rate (70 errors / 1000 events)
        metrics_data = {"input-err": create_input_metric(events_in=1000, errors=70)}

        mock_client.get_inputs.return_value = inputs
        mock_client.get_metrics.return_value = create_metrics(metrics_data)

        analyzer = InputSourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "high"
        assert finding.id == "input-errors-input-err"
        assert "High Error Rate" in finding.title
        assert round(finding.metadata["error_rate"], 1) == 7.0

    @pytest.mark.asyncio
    async def test_error_rate_critical(self, mock_client):
        """Test that error rate > 10% is flagged as CRITICAL."""
        inputs = [create_input("input-err-crit")]

        # 12% error rate (120 errors / 1000 events)
        metrics_data = {"input-err-crit": create_input_metric(events_in=1000, errors=120)}

        mock_client.get_inputs.return_value = inputs
        mock_client.get_metrics.return_value = create_metrics(metrics_data)

        analyzer = InputSourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "critical"
        assert finding.metadata["error_rate"] == 12.0

    @pytest.mark.asyncio
    async def test_queue_depth_warning(self, mock_client):
        """Test that queue depth > 1000 is flagged as LOW (warning level mapped to low)."""
        inputs = [create_input("input-queue")]

        # Queue size 2000 (Warning > 1000)
        metrics_data = {"input-queue": create_input_metric(queue_size=2000)}

        mock_client.get_inputs.return_value = inputs
        mock_client.get_metrics.return_value = create_metrics(metrics_data)

        analyzer = InputSourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        # In code: if severity_level == "warning": severity = "low"
        assert finding.severity == "low"
        assert finding.id == "input-queue-input-queue"
        assert "Queue" in finding.title

    @pytest.mark.asyncio
    async def test_queue_depth_overflow(self, mock_client):
        """Test that queue depth > 10000 is flagged as MEDIUM."""
        inputs = [create_input("input-queue-overflow")]

        # Queue size 15000 (Medium > 10000)
        metrics_data = {"input-queue-overflow": create_input_metric(queue_size=15000)}

        mock_client.get_inputs.return_value = inputs
        mock_client.get_metrics.return_value = create_metrics(metrics_data)

        analyzer = InputSourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "medium"
        assert finding.metadata["queue_size"] == 15000

    @pytest.mark.asyncio
    async def test_no_inputs_available(self, mock_client):
        """Test behavior when no inputs are configured."""
        mock_client.get_inputs.return_value = []
        mock_client.get_metrics.return_value = create_metrics({})

        analyzer = InputSourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 0
        assert result.metadata["inputs_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_client):
        """Test graceful handling of API errors."""
        mock_client.get_inputs.side_effect = Exception("API Failure")

        analyzer = InputSourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is False
        assert result.error is not None
        assert "API Failure" in result.error
        assert len(result.findings) == 1
        assert result.findings[0].id == "input-analysis-error"
