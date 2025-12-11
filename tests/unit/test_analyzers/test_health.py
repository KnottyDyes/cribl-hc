"""
Unit tests for HealthAnalyzer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cribl_hc.analyzers.health import HealthAnalyzer
from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation


class TestHealthAnalyzer:
    """Test suite for HealthAnalyzer."""

    def test_objective_name(self):
        """Test that objective name is 'health'."""
        analyzer = HealthAnalyzer()
        assert analyzer.objective_name == "health"

    def test_description(self):
        """Test analyzer description."""
        analyzer = HealthAnalyzer()
        description = analyzer.get_description()
        assert "health" in description.lower()
        assert "worker" in description.lower()

    def test_estimated_api_calls(self):
        """Test estimated API call count."""
        analyzer = HealthAnalyzer()
        assert analyzer.get_estimated_api_calls() == 3

    def test_required_permissions(self):
        """Test required permissions list."""
        analyzer = HealthAnalyzer()
        permissions = analyzer.get_required_permissions()
        assert "read:workers" in permissions
        assert "read:system" in permissions
        assert "read:metrics" in permissions

    @pytest.mark.asyncio
    async def test_analyze_all_healthy_workers(self):
        """Test analysis with all healthy workers."""
        # Create mock client
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Mock healthy workers
        mock_client.get_workers.return_value = [
            {
                "id": "worker-1",
                "metrics": {
                    "cpu_usage": 50.0,
                    "memory_usage": 60.0,
                    "disk_usage": 40.0,
                },
            },
            {
                "id": "worker-2",
                "metrics": {
                    "cpu_usage": 45.0,
                    "memory_usage": 55.0,
                    "disk_usage": 35.0,
                },
            },
        ]

        mock_client.get_system_status.return_value = {
            "version": "4.5.0",
            "health": "healthy",
        }

        # Run analysis
        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify result
        assert result.success is True
        assert result.objective == "health"
        assert result.metadata["worker_count"] == 2
        assert result.metadata["unhealthy_workers"] == 0
        assert result.metadata["health_score"] == 100.0
        assert result.metadata["health_status"] == "healthy"

        # Should have 1 finding (overall health summary)
        assert len(result.findings) == 1
        assert result.findings[0].category == "system"
        assert result.findings[0].severity == "info"

    @pytest.mark.asyncio
    async def test_analyze_unhealthy_workers_high_cpu(self):
        """Test analysis with workers having high CPU."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Mock workers with high CPU
        mock_client.get_workers.return_value = [
            {
                "id": "worker-1",
                "metrics": {
                    "cpu_usage": 95.0,  # Critical
                    "memory_usage": 60.0,
                    "disk_usage": 40.0,
                },
            },
        ]

        mock_client.get_system_status.return_value = {"version": "4.5.0"}

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["unhealthy_workers"] == 1

        # Should have 2 findings: unhealthy worker + overall health
        assert len(result.findings) >= 2

        # Find worker health finding
        worker_finding = next(
            (f for f in result.findings if f.affected_component == "worker-1"),
            None,
        )
        assert worker_finding is not None
        assert worker_finding.severity == "high"
        assert "CPU" in worker_finding.description

        # Should have recommendations
        assert len(result.recommendations) == 1
        rec = result.recommendations[0]
        assert rec.affected_component == "worker-1"
        assert len(rec.remediation_steps) > 0

    @pytest.mark.asyncio
    async def test_analyze_critical_worker_multiple_issues(self):
        """Test analysis with worker having multiple critical issues."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Mock worker with multiple issues
        mock_client.get_workers.return_value = [
            {
                "id": "worker-1",
                "metrics": {
                    "cpu_usage": 95.0,  # Critical
                    "memory_usage": 92.0,  # Critical
                    "disk_usage": 88.0,  # High
                },
            },
        ]

        mock_client.get_system_status.return_value = {"version": "4.5.0"}

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True

        # Find worker finding
        worker_finding = next(
            (f for f in result.findings if f.affected_component == "worker-1"),
            None,
        )

        # Should be critical severity due to multiple issues
        assert worker_finding.severity == "critical"
        assert len(worker_finding.evidence["issues"]) == 3

        # Should have comprehensive remediation
        assert len(result.recommendations) == 1
        assert len(result.recommendations[0].remediation_steps) >= 3

    @pytest.mark.asyncio
    async def test_analyze_mixed_worker_health(self):
        """Test analysis with mix of healthy and unhealthy workers."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-1",
                "metrics": {
                    "cpu_usage": 50.0,
                    "memory_usage": 60.0,
                    "disk_usage": 40.0,
                },
            },
            {
                "id": "worker-2",
                "metrics": {
                    "cpu_usage": 95.0,  # Unhealthy
                    "memory_usage": 60.0,
                    "disk_usage": 40.0,
                },
            },
            {
                "id": "worker-3",
                "metrics": {
                    "cpu_usage": 50.0,
                    "memory_usage": 92.0,  # Unhealthy
                    "disk_usage": 40.0,
                },
            },
        ]

        mock_client.get_system_status.return_value = {"version": "4.5.0"}

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["worker_count"] == 3
        assert result.metadata["unhealthy_workers"] == 2

        # Health score should be degraded
        health_score = result.metadata["health_score"]
        assert 50.0 < health_score < 90.0

        # Should have recommendations for both unhealthy workers
        assert len(result.recommendations) == 2

    @pytest.mark.asyncio
    async def test_analyze_no_workers(self):
        """Test analysis with no workers."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        mock_client.get_workers.return_value = []
        mock_client.get_system_status.return_value = {"version": "4.5.0"}

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["worker_count"] == 0
        assert result.metadata["health_score"] == 0.0

    @pytest.mark.asyncio
    async def test_analyze_api_error(self):
        """Test analysis when API call fails."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Simulate API error
        mock_client.get_workers.side_effect = Exception("API connection failed")

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should return failed result
        assert result.success is False
        assert result.error is not None
        assert "API connection failed" in result.error

        # Should have error finding
        assert len(result.findings) == 1
        assert result.findings[0].severity == "high"
        assert result.findings[0].category == "system"

    @pytest.mark.asyncio
    async def test_health_score_calculation(self):
        """Test health score calculation algorithm."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        # 10 workers: 8 healthy, 2 unhealthy (1 critical)
        workers = []

        # 8 healthy workers
        for i in range(8):
            workers.append({
                "id": f"worker-{i}",
                "metrics": {
                    "cpu_usage": 50.0,
                    "memory_usage": 60.0,
                    "disk_usage": 40.0,
                },
            })

        # 1 unhealthy worker (single issue)
        workers.append({
            "id": "worker-8",
            "metrics": {
                "cpu_usage": 95.0,
                "memory_usage": 60.0,
                "disk_usage": 40.0,
            },
        })

        # 1 critical worker (multiple issues)
        workers.append({
            "id": "worker-9",
            "metrics": {
                "cpu_usage": 95.0,
                "memory_usage": 92.0,
                "disk_usage": 40.0,
            },
        })

        mock_client.get_workers.return_value = workers
        mock_client.get_system_status.return_value = {"version": "4.5.0"}

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        # With 80% healthy workers but 1 critical:
        # - Base score: 80
        # - Critical penalty: 10
        # - Expected: ~70
        health_score = result.metadata["health_score"]
        assert 65.0 <= health_score <= 80.0

    def test_count_worker_issues(self):
        """Test worker issue counting."""
        analyzer = HealthAnalyzer()

        # Worker with no issues
        worker1 = {
            "metrics": {
                "cpu_usage": 50.0,
                "memory_usage": 60.0,
                "disk_usage": 40.0,
            }
        }
        assert analyzer._count_worker_issues(worker1) == 0

        # Worker with 1 issue
        worker2 = {
            "metrics": {
                "cpu_usage": 95.0,
                "memory_usage": 60.0,
                "disk_usage": 40.0,
            }
        }
        assert analyzer._count_worker_issues(worker2) == 1

        # Worker with 3 issues
        worker3 = {
            "metrics": {
                "cpu_usage": 95.0,
                "memory_usage": 92.0,
                "disk_usage": 91.0,
            }
        }
        assert analyzer._count_worker_issues(worker3) == 3

    def test_get_health_status(self):
        """Test health status categorization."""
        analyzer = HealthAnalyzer()

        assert analyzer._get_health_status(95.0) == "healthy"
        assert analyzer._get_health_status(90.0) == "healthy"
        assert analyzer._get_health_status(75.0) == "degraded"
        assert analyzer._get_health_status(70.0) == "degraded"
        assert analyzer._get_health_status(55.0) == "unhealthy"
        assert analyzer._get_health_status(50.0) == "unhealthy"
        assert analyzer._get_health_status(30.0) == "critical"
        assert analyzer._get_health_status(0.0) == "critical"

    @pytest.mark.asyncio
    async def test_remediation_steps_cpu(self):
        """Test CPU-specific remediation steps."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-1",
                "metrics": {
                    "cpu_usage": 95.0,
                    "memory_usage": 60.0,
                    "disk_usage": 40.0,
                },
            }
        ]

        mock_client.get_system_status.return_value = {"version": "4.5.0"}

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        rec = result.recommendations[0]
        steps = "\n".join(rec.remediation_steps).lower()

        assert "cpu" in steps or "pipeline" in steps
        assert len(rec.references) > 0
        assert "docs.cribl.io" in rec.references[0]

    @pytest.mark.asyncio
    async def test_remediation_steps_memory(self):
        """Test memory-specific remediation steps."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-1",
                "metrics": {
                    "cpu_usage": 50.0,
                    "memory_usage": 95.0,
                    "disk_usage": 40.0,
                },
            }
        ]

        mock_client.get_system_status.return_value = {"version": "4.5.0"}

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        rec = result.recommendations[0]
        steps = "\n".join(rec.remediation_steps).lower()

        assert "memory" in steps

    @pytest.mark.asyncio
    async def test_remediation_steps_disk(self):
        """Test disk-specific remediation steps."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-1",
                "metrics": {
                    "cpu_usage": 50.0,
                    "memory_usage": 60.0,
                    "disk_usage": 95.0,
                },
            }
        ]

        mock_client.get_system_status.return_value = {"version": "4.5.0"}

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        rec = result.recommendations[0]
        steps = "\n".join(rec.remediation_steps).lower()

        assert "disk" in steps or "persistent queue" in steps

    @pytest.mark.asyncio
    async def test_overall_health_finding_severity(self):
        """Test overall health finding has correct severity."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        # Test healthy status
        mock_client.get_workers.return_value = [
            {"id": "w1", "metrics": {"cpu_usage": 50, "memory_usage": 60, "disk_usage": 40}}
        ]
        mock_client.get_system_status.return_value = {"version": "4.5.0"}

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        overall_finding = next(
            (f for f in result.findings if f.affected_component == "overall_health"),
            None,
        )
        assert overall_finding.severity == "info"

    @pytest.mark.asyncio
    async def test_metadata_includes_version(self):
        """Test that Cribl version is captured in metadata."""
        mock_client = AsyncMock(spec=CriblAPIClient)

        mock_client.get_workers.return_value = []
        mock_client.get_system_status.return_value = {"version": "4.5.2-beta"}

        analyzer = HealthAnalyzer()
        result = await analyzer.analyze(mock_client)

        assert result.metadata["cribl_version"] == "4.5.2-beta"
