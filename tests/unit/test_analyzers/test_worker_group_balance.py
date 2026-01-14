"""
Unit tests for the WorkerGroupBalanceAnalyzer.
"""

from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.worker_group_balance import WorkerGroupBalanceAnalyzer

# Test Data Scenarios
# --------------------

BALANCED_DATA = {
    "workers": [
        {
            "id": "worker1",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 25.0,
            "mem.usage": 30.0,
        },
        {
            "id": "worker2",
            "group": "default",
            "total.in": 1050,
            "cpu.usage": 26.0,
            "mem.usage": 31.0,
        },
        {
            "id": "worker3",
            "group": "default",
            "total.in": 980,
            "cpu.usage": 24.0,
            "mem.usage": 29.0,
        },
    ]
}

UNBALANCED_LOAD_DATA = {
    "workers": [
        {
            "id": "worker1",
            "group": "default",
            "total.in": 5000,
            "cpu.usage": 50.0,
            "mem.usage": 50.0,
        },
        {"id": "worker2", "group": "default", "total.in": 100, "cpu.usage": 5.0, "mem.usage": 10.0},
        {"id": "worker3", "group": "default", "total.in": 200, "cpu.usage": 6.0, "mem.usage": 12.0},
    ]
}

HIGH_CPU_VARIANCE_DATA = {
    "workers": [
        {
            "id": "worker1",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 80.0,
            "mem.usage": 40.0,
        },
        {
            "id": "worker2",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 10.0,
            "mem.usage": 42.0,
        },
        {
            "id": "worker3",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 12.0,
            "mem.usage": 38.0,
        },
    ]
}

HIGH_MEM_VARIANCE_DATA = {
    "workers": [
        {
            "id": "worker1",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 30.0,
            "mem.usage": 90.0,
        },
        {
            "id": "worker2",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 32.0,
            "mem.usage": 20.0,
        },
        {
            "id": "worker3",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 28.0,
            "mem.usage": 22.0,
        },
    ]
}

# Note: The analyzer's parser assumes historical data comes from the API.
# The mock data simulates what the parser expects.
CAPACITY_EXHAUSTION_CPU_DATA = {
    "workers": [
        {
            "id": "worker1",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 80.0,
            "mem.usage": 50.0,
            "historical_cpu": [70.0, 72.0, 75.0, 78.0],
        },
        {
            "id": "worker2",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 40.0,
            "mem.usage": 50.0,
        },
    ]
}

CAPACITY_EXHAUSTION_MEM_DATA = {
    "workers": [
        {
            "id": "worker1",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 50.0,
            "mem.usage": 75.0,
            "historical_mem": [75.0, 77.0, 80.0, 83.0],
        },
        {
            "id": "worker2",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 50.0,
            "mem.usage": 40.0,
        },
    ]
}

STABLE_TREND_DATA = {
    "workers": [
        {
            "id": "worker1",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 80.0,
            "mem.usage": 85.0,
            "historical_cpu": [80.0, 79.0, 81.0, 80.0],
            "historical_mem": [85.0, 84.0, 85.0, 84.0],
        },
    ]
}

# Edge Case Data
NO_WORKERS_DATA = {"workers": []}
SINGLE_WORKER_DATA = {
    "workers": [
        {
            "id": "worker1",
            "group": "default",
            "total.in": 1000,
            "cpu.usage": 25.0,
            "mem.usage": 30.0,
        }
    ]
}
NO_TRAFFIC_DATA = {
    "workers": [
        {"id": "worker1", "group": "default", "total.in": 0, "cpu.usage": 5.0, "mem.usage": 10.0},
        {"id": "worker2", "group": "default", "total.in": 0, "cpu.usage": 5.0, "mem.usage": 10.0},
    ]
}
MISSING_METRICS_DATA = {
    "workers": [
        {"id": "worker1", "group": "default", "total.in": 1000},
        {"id": "worker2", "group": "default", "cpu.usage": 25.0},
        {"id": "worker3", "group": "default", "mem.usage": 30.0},
    ]
}


@pytest.fixture
def analyzer():
    """Fixture for the WorkerGroupBalanceAnalyzer."""
    return WorkerGroupBalanceAnalyzer()


def mock_api_client(mock_data):
    """Factory to create a mock CriblAPIClient."""
    mock_client = AsyncMock()
    mock_client.get_metrics = AsyncMock(return_value=mock_data)
    return mock_client


@pytest.mark.asyncio
async def test_balanced_group_no_findings(analyzer):
    """1. Test a perfectly balanced group, expecting no findings."""
    client = mock_api_client(BALANCED_DATA)
    result = await analyzer.analyze(client)
    assert result.success is True
    assert not result.findings


@pytest.mark.asyncio
async def test_unbalanced_load_finding(analyzer):
    """2. Test an unbalanced load, expecting a medium severity finding."""
    client = mock_api_client(UNBALANCED_LOAD_DATA)
    result = await analyzer.analyze(client)
    assert len(result.findings) >= 1
    finding = result.findings[0]
    assert finding.severity == "medium"
    assert finding.title.startswith("Uneven Load Distribution")
    assert "gini_coefficient" in finding.metadata
    assert finding.metadata["gini_coefficient"] > 0.4
    assert finding.remediation_steps


@pytest.mark.asyncio
async def test_high_cpu_variance_finding(analyzer):
    """3. Test high CPU variance, expecting a high severity finding."""
    client = mock_api_client(HIGH_CPU_VARIANCE_DATA)
    result = await analyzer.analyze(client)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "high"
    assert "High CPU Utilization Variance" in finding.title
    assert "cpu_cv" in finding.metadata
    assert finding.metadata["cpu_cv"] > 0.5
    assert finding.remediation_steps
    assert finding.estimated_impact


@pytest.mark.asyncio
async def test_high_mem_variance_finding(analyzer):
    """4. Test high memory variance, expecting a high severity finding."""
    client = mock_api_client(HIGH_MEM_VARIANCE_DATA)
    result = await analyzer.analyze(client)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "high"
    assert "High Memory Utilization Variance" in finding.title
    assert "mem_cv" in finding.metadata
    assert finding.metadata["mem_cv"] > 0.5
    assert finding.remediation_steps
    assert finding.estimated_impact


@pytest.mark.asyncio
async def test_capacity_exhaustion_cpu_finding(analyzer):
    """5. Test CPU capacity exhaustion prediction, expecting a medium finding."""
    client = mock_api_client(CAPACITY_EXHAUSTION_CPU_DATA)
    result = await analyzer.analyze(client)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "medium"
    assert "Predicted CPU Exhaustion" in finding.title
    assert finding.metadata["predicted_utilization_pct"] > 90.0
    assert finding.remediation_steps


@pytest.mark.asyncio
async def test_capacity_exhaustion_mem_finding(analyzer):
    """6. Test memory capacity exhaustion prediction, expecting a medium finding."""
    client = mock_api_client(CAPACITY_EXHAUSTION_MEM_DATA)
    result = await analyzer.analyze(client)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "medium"
    assert "Predicted Memory Exhaustion" in finding.title
    assert finding.metadata["predicted_utilization_pct"] > 90.0
    assert finding.remediation_steps


@pytest.mark.asyncio
async def test_stable_trend_no_exhaustion_finding(analyzer):
    """7. Test a stable (non-increasing) trend, expecting no exhaustion finding."""
    client = mock_api_client(STABLE_TREND_DATA)
    result = await analyzer.analyze(client)
    assert not result.findings


@pytest.mark.asyncio
async def test_no_workers_info_finding(analyzer):
    """8. Test with no worker data, expecting an informational finding."""
    client = mock_api_client(NO_WORKERS_DATA)
    result = await analyzer.analyze(client)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == "info"
    assert finding.title == "No Worker Metrics Found"


@pytest.mark.asyncio
async def test_single_worker_no_findings(analyzer):
    """9. Test with a single worker; no balance checks should run."""
    client = mock_api_client(SINGLE_WORKER_DATA)
    result = await analyzer.analyze(client)
    assert not result.findings


@pytest.mark.asyncio
async def test_no_traffic_no_load_finding(analyzer):
    """10. Test with no traffic, expecting no load imbalance finding."""
    client = mock_api_client(NO_TRAFFIC_DATA)
    result = await analyzer.analyze(client)
    assert all("Load Distribution" not in f.title for f in result.findings)


@pytest.mark.asyncio
async def test_missing_metrics_handles_gracefully(analyzer):
    """11. Test with missing metrics, ensuring it doesn't crash."""
    client = mock_api_client(MISSING_METRICS_DATA)
    result = await analyzer.analyze(client)
    assert result.success is True
    assert not result.findings


@pytest.mark.asyncio
async def test_api_error_handled(analyzer):
    """12. Test that an API error is handled gracefully."""
    mock_client = AsyncMock()
    mock_client.get_metrics.side_effect = Exception("API connection failed")
    result = await analyzer.analyze(mock_client)
    assert result.success is False
    assert result.error == "API connection failed"
    assert not result.findings


def test_pydantic_validation_medium_finding_ok(analyzer):
    """13. Verify a valid medium severity finding passes Pydantic validation."""
    finding = analyzer.create_finding(
        id="test-medium",
        category="Test",
        severity="medium",
        title="Test Medium",
        description="Desc",
        remediation_steps=["Step 1"],
    )
    assert finding.remediation_steps


def test_pydantic_validation_high_finding_ok(analyzer):
    """14. Verify a valid high severity finding passes Pydantic validation."""
    finding = analyzer.create_finding(
        id="test-high",
        category="Test",
        severity="high",
        title="Test High",
        description="Desc",
        remediation_steps=["Step 1"],
        estimated_impact="High impact",
    )
    assert finding.remediation_steps and finding.estimated_impact


def test_pydantic_validation_medium_fails_without_remediation(analyzer):
    """15. Verify medium finding fails validation without remediation steps."""
    with pytest.raises(ValueError, match="Remediation steps required"):
        analyzer.create_finding(
            id="test-fail",
            category="Test",
            severity="medium",
            title="Test Fail",
            description="Desc",
        )


def test_pydantic_validation_high_fails_without_impact(analyzer):
    """16. Verify high finding fails validation without estimated impact."""
    with pytest.raises(ValueError, match="Estimated impact required"):
        analyzer.create_finding(
            id="test-fail",
            category="Test",
            severity="high",
            title="Test Fail",
            description="Desc",
            remediation_steps=["Step 1"],
        )


@pytest.mark.asyncio
async def test_two_groups_analyzed_independently(analyzer):
    """17. Test that two separate worker groups are analyzed independently."""
    data = {
        "workers": [
            {"id": "w1", "group": "group-a", "total.in": 1000, "cpu.usage": 20, "mem.usage": 20},
            {"id": "w2", "group": "group-a", "total.in": 1050, "cpu.usage": 21, "mem.usage": 19},
            {"id": "w3", "group": "group-b", "total.in": 5000, "cpu.usage": 80, "mem.usage": 15},
            {"id": "w4", "group": "group-b", "total.in": 100, "cpu.usage": 10, "mem.usage": 85},
        ]
    }
    client = mock_api_client(data)
    result = await analyzer.analyze(client)

    # Expecting 2 findings for the highly imbalanced group-b
    assert len(result.findings) == 2

    group_b_findings = [
        f for f in result.findings if f.metadata.get("worker_group_id") == "group-b"
    ]
    assert len(group_b_findings) == 2

    group_a_findings = [
        f for f in result.findings if f.metadata.get("worker_group_id") == "group-a"
    ]
    assert len(group_a_findings) == 0
