import pytest
from unittest.mock import AsyncMock, MagicMock

from cribl_hc.analyzers.endpoint_health import EndpointHealthAnalyzer

# Fixtures


@pytest.fixture
def analyzer():
    """Returns an instance of the EndpointHealthAnalyzer."""
    return EndpointHealthAnalyzer()


@pytest.fixture
def mock_api_client():
    """Returns a mock CriblAPIClient."""
    client = MagicMock()
    client.get_metrics = AsyncMock()
    return client


# Test Data


def get_test_metrics(overrides=None):
    """Helper to create sample metric data for a single output."""
    if overrides is None:
        overrides = {}

    defaults = {
        "requests": {"total": 1000, "failed": 10},  # 1% failure rate
        "latency": {"p99": 150.0},
        "circuit_breaker_open": 0,
        "baseline_latency": 100.0,
    }
    defaults.update(overrides)
    return {"outputs": {"splunk-prod": defaults}}


# Tests for Request Failure Rate


@pytest.mark.asyncio
async def test_failure_rate_healthy(analyzer, mock_api_client):
    """Should not create a finding for a healthy failure rate (< 2%)."""
    metrics = get_test_metrics({"requests": {"total": 1000, "failed": 19}})  # 1.9%
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 0


@pytest.mark.asyncio
async def test_failure_rate_high(analyzer, mock_api_client):
    """Should create a high severity finding for failure rate between 2% and 5%."""
    metrics = get_test_metrics({"requests": {"total": 1000, "failed": 35}})  # 3.5%
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "high"
    assert "High Failure Rate" in finding.title
    assert "3.50%" in finding.description
    assert finding.estimated_impact is not None and finding.estimated_impact != ""
    assert len(finding.remediation_steps) > 0


@pytest.mark.asyncio
async def test_failure_rate_critical(analyzer, mock_api_client):
    """Should create a critical severity finding for failure rate > 5%."""
    metrics = get_test_metrics({"requests": {"total": 1000, "failed": 60}})  # 6.0%
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "critical"
    assert "Critical Failure Rate" in finding.title
    assert "6.00%" in finding.description
    assert finding.estimated_impact is not None and finding.estimated_impact != ""
    assert len(finding.remediation_steps) > 0


@pytest.mark.asyncio
async def test_failure_rate_edge_case_zero_requests(analyzer, mock_api_client):
    """Should not create a finding or error if total requests are zero."""
    metrics = get_test_metrics({"requests": {"total": 0, "failed": 0}})
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 0


# Tests for Latency Spikes


@pytest.mark.asyncio
async def test_latency_healthy(analyzer, mock_api_client):
    """Should not create a finding for normal latency."""
    metrics = get_test_metrics({"latency": {"p99": 199.0}, "baseline_latency": 100.0})
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 0


@pytest.mark.asyncio
async def test_latency_spike_medium(analyzer, mock_api_client):
    """Should create a medium severity finding for a significant latency spike."""
    metrics = get_test_metrics({"latency": {"p99": 201.0}, "baseline_latency": 100.0})
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "medium"
    assert "Latency Spike Detected" in finding.title
    assert "201.00ms" in finding.description
    assert "100.00ms" in finding.description
    assert len(finding.remediation_steps) > 0
    assert finding.estimated_impact == ""


@pytest.mark.asyncio
async def test_latency_edge_case_no_baseline(analyzer, mock_api_client):
    """Should not create a finding if baseline latency is missing."""
    metrics = get_test_metrics({"latency": {"p99": 250.0}, "baseline_latency": None})
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 0


@pytest.mark.asyncio
async def test_latency_edge_case_zero_baseline(analyzer, mock_api_client):
    """Should not create a finding or error if baseline latency is zero."""
    metrics = get_test_metrics({"latency": {"p99": 250.0}, "baseline_latency": 0})
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 0


# Tests for Circuit Breaker


@pytest.mark.asyncio
async def test_circuit_breaker_closed(analyzer, mock_api_client):
    """Should not create a finding if the circuit breaker is closed."""
    metrics = get_test_metrics({"circuit_breaker_open": 0})
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 0


@pytest.mark.asyncio
async def test_circuit_breaker_open_critical(analyzer, mock_api_client):
    """Should create a critical finding if the circuit breaker is open."""
    metrics = get_test_metrics({"circuit_breaker_open": 1})
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "critical"
    assert "Circuit Breaker Open" in finding.title
    assert finding.estimated_impact is not None and finding.estimated_impact != ""
    assert len(finding.remediation_steps) > 0


# General and Edge Case Tests


@pytest.mark.asyncio
async def test_no_outputs_data(analyzer, mock_api_client):
    """Should return an empty result if no outputs are in the metrics."""
    mock_api_client.get_metrics.return_value = {"outputs": {}}

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 0


@pytest.mark.asyncio
async def test_multiple_findings(analyzer, mock_api_client):
    """Should correctly identify and report multiple issues for a single destination."""
    metrics = get_test_metrics(
        {
            "requests": {"total": 1000, "failed": 70},  # Critical failure rate
            "latency": {"p99": 300.0},  # Medium latency spike
            "baseline_latency": 120.0,
            "circuit_breaker_open": 1,  # Critical circuit breaker
        }
    )
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 3
    severities = sorted([f.severity for f in result.findings])
    assert severities == ["critical", "critical", "medium"]


@pytest.mark.asyncio
async def test_multiple_destinations(analyzer, mock_api_client):
    """Should correctly analyze multiple destinations."""
    metrics = {
        "outputs": {
            "splunk-prod": {
                "requests": {"total": 1000, "failed": 60},  # Critical
                "latency": {"p99": 150.0},
                "circuit_breaker_open": 0,
                "baseline_latency": 100.0,
            },
            "s3-archive": {
                "requests": {"total": 5000, "failed": 10},  # Healthy
                "latency": {"p99": 500.0},  # Medium
                "circuit_breaker_open": 0,
                "baseline_latency": 200.0,
            },
        }
    }
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 2
    splunk_finding = next(f for f in result.findings if f.affected_components == ["splunk-prod"])
    s3_finding = next(f for f in result.findings if f.affected_components == ["s3-archive"])

    assert splunk_finding.severity == "critical"
    assert s3_finding.severity == "medium"


# Finding Validation Tests


@pytest.mark.asyncio
async def test_pydantic_validation_critical_finding(analyzer, mock_api_client):
    """Ensures a critical finding has required fields (remediation and impact)."""
    metrics = get_test_metrics({"requests": {"total": 1000, "failed": 100}})  # 10%
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "critical"
    assert finding.estimated_impact
    assert len(finding.remediation_steps) > 0


@pytest.mark.asyncio
async def test_pydantic_validation_high_finding(analyzer, mock_api_client):
    """Ensures a high severity finding has required fields (remediation and impact)."""
    metrics = get_test_metrics({"requests": {"total": 1000, "failed": 40}})  # 4%
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "high"
    assert finding.estimated_impact
    assert len(finding.remediation_steps) > 0


@pytest.mark.asyncio
async def test_pydantic_validation_medium_finding(analyzer, mock_api_client):
    """Ensures a medium severity finding has remediation steps."""
    metrics = get_test_metrics({"latency": {"p99": 250.0}, "baseline_latency": 100.0})
    mock_api_client.get_metrics.return_value = metrics

    result = await analyzer.analyze(mock_api_client)

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "medium"
    assert not finding.estimated_impact  # Should be empty for medium
    assert len(finding.remediation_steps) > 0


@pytest.mark.asyncio
async def test_no_metrics_for_output(analyzer, mock_api_client):
    """Should not fail if an output has no metrics."""
    metrics = {
        "outputs": {
            "splunk-prod": {}  # No metrics at all
        }
    }
    mock_api_client.get_metrics.return_value = metrics
    result = await analyzer.analyze(mock_api_client)
    assert len(result.findings) == 0
