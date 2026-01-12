import pytest
from unittest.mock import AsyncMock, MagicMock
from cribl_hc.analyzers.backpressure import BackpressureAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


@pytest.fixture
def analyzer():
    return BackpressureAnalyzer()


@pytest.fixture
def mock_client():
    client = MagicMock(spec=CriblAPIClient)
    client.get_metrics = AsyncMock()
    client.get_outputs = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_analyzer_runs_with_metrics(analyzer, mock_client):
    # Mock data
    mock_client.get_outputs.return_value = [{"id": "out1", "type": "splunk"}]
    mock_client.get_metrics.return_value = {
        "outputs": {"out1": {"out": {"events": 1000}, "blocked": {"events": 0}}}
    }

    result = await analyzer.analyze(mock_client)

    assert result.success is True
    # Should not have error finding
    assert not any(f.id == "backpressure-analysis-error" for f in result.findings)
