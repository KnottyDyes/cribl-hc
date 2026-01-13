import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from cribl_hc.analyzers.freshness import FreshnessAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


@pytest.fixture
def analyzer():
    return FreshnessAnalyzer()


@pytest.fixture
def mock_client():
    client = MagicMock(spec=CriblAPIClient)
    client.capture_events = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_detects_high_lag(analyzer, mock_client):
    now = time.time()
    mock_client.capture_events.return_value = [
        {"_time": now - 600},  # 10 minutes lag (Warning)
        {"_time": now - 600},
    ]

    result = await analyzer.analyze(mock_client)

    assert result.success is True
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.id == "freshness-high-lag"
    assert finding.severity == "high"


@pytest.mark.asyncio
async def test_detects_future_timestamps(analyzer, mock_client):
    now = time.time()
    mock_client.capture_events.return_value = [
        {"_time": now + 600},  # 10 minutes in future
    ]

    result = await analyzer.analyze(mock_client)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.id == "freshness-future-timestamps"


@pytest.mark.asyncio
async def test_healthy_freshness(analyzer, mock_client):
    now = time.time()
    mock_client.capture_events.return_value = [
        {"_time": now - 10},  # 10 seconds lag (Fine)
        {"_time": now - 5},
    ]

    result = await analyzer.analyze(mock_client)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.id == "freshness-healthy"
    assert finding.severity == "info"
