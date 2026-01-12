import pytest
from unittest.mock import AsyncMock, MagicMock
from cribl_hc.analyzers.sensitive_data import SensitiveDataAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


@pytest.fixture
def analyzer():
    return SensitiveDataAnalyzer()


@pytest.fixture
def mock_client():
    client = MagicMock(spec=CriblAPIClient)
    client.capture_events = AsyncMock()
    client.worker_group = "default"
    return client


@pytest.mark.asyncio
async def test_detects_ssn(analyzer, mock_client):
    mock_client.capture_events.return_value = [
        {"_raw": "User: John Doe, SSN: 123-45-6789, Status: Active"},
        {"_raw": "Safe event here"},
    ]

    result = await analyzer.analyze(mock_client)

    assert result.success is True
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.id == "sensitive-data-ssn"
    assert finding.severity == "critical"
    assert "Social Security Number" in finding.title


@pytest.mark.asyncio
async def test_detects_credit_card(analyzer, mock_client):
    mock_client.capture_events.return_value = [
        {"_raw": "Payment processed for card 4111 1111 1111 1111 yesterday."},
    ]

    result = await analyzer.analyze(mock_client)

    assert len(result.findings) == 1
    assert result.findings[0].id == "sensitive-data-credit_card"


@pytest.mark.asyncio
async def test_no_sensitive_data(analyzer, mock_client):
    mock_client.capture_events.return_value = [
        {"_raw": "Just a normal log line"},
        {"_raw": "Another safe line"},
    ]

    result = await analyzer.analyze(mock_client)

    assert len(result.findings) == 1
    assert result.findings[0].id == "sensitive-data-clean"
    assert result.findings[0].severity == "info"


@pytest.mark.asyncio
async def test_aws_key_detection(analyzer, mock_client):
    mock_client.capture_events.return_value = [
        {"_raw": "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"},
    ]

    result = await analyzer.analyze(mock_client)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.id == "sensitive-data-aws_key"
    assert finding.severity == "high"
