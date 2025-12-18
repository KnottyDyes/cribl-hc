"""
Unit tests for ResourceAnalyzer.

Tests resource utilization analysis including CPU, memory, disk monitoring,
capacity planning, and imbalance detection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from cribl_hc.analyzers.resource import ResourceAnalyzer
from cribl_hc.analyzers.base import AnalyzerResult
from cribl_hc.core.api_client import CriblAPIClient


def create_mock_client(is_cloud: bool = False) -> AsyncMock:
    """
    Create a mock Cribl API client.

    Args:
        is_cloud: Whether to simulate Cribl Cloud (True) or self-hosted (False)

    Returns:
        Mocked CriblAPIClient with is_cloud property set
    """
    mock_client = AsyncMock(spec=CriblAPIClient)
    mock_client.is_cloud = is_cloud
    return mock_client


class TestResourceAnalyzer:
    """Test suite for ResourceAnalyzer."""

    def test_objective_name(self):
        """Test that analyzer has correct objective name."""
        analyzer = ResourceAnalyzer()
        assert analyzer.objective_name == "resource"

    def test_estimated_api_calls(self):
        """Test that estimated API calls is correct."""
        analyzer = ResourceAnalyzer()
        assert analyzer.get_estimated_api_calls() == 3

    def test_required_permissions(self):
        """Test that required permissions are correct."""
        analyzer = ResourceAnalyzer()
        permissions = analyzer.get_required_permissions()

        assert isinstance(permissions, list)
        assert "read:workers" in permissions
        assert "read:metrics" in permissions
        assert "read:system" in permissions

    @pytest.mark.asyncio
    async def test_analyze_healthy_resources(self):
        """Test analyzer with healthy resource utilization."""
        # Mock API client (self-hosted, so disk metrics will be checked)
        mock_client = create_mock_client(is_cloud=False)

        # Healthy worker data
        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "status": "healthy",
                "info": {
                    "hostname": "worker-01.example.com",
                    "cpus": 8,
                    "totalMemory": 34359738368,  # 32GB
                    "freeMemory": 17179869184,  # 16GB free (50% used)
                },
                "metrics": {
                    "cpu": {"perc": 0.45, "loadAverage": [2.0, 1.8, 1.5]},  # 45% CPU
                },
            },
            {
                "id": "worker-02",
                "status": "healthy",
                "info": {
                    "hostname": "worker-02.example.com",
                    "cpus": 8,
                    "totalMemory": 34359738368,
                    "freeMemory": 17179869184,
                },
                "metrics": {
                    "cpu": {"perc": 0.50, "loadAverage": [2.1, 1.9, 1.6]},  # 50% CPU
                },
            },
        ]

        # Healthy metrics
        mock_client.get_metrics.return_value = {
            "workers": {
                "worker-01": {
                    "disk": {
                        "total": 536870912000,  # 500GB
                        "used": 107374182400,  # 100GB (20% used)
                        "free": 429496729600,  # 400GB free
                    }
                },
                "worker-02": {
                    "disk": {
                        "total": 536870912000,
                        "used": 107374182400,
                        "free": 429496729600,
                    }
                },
            }
        }

        mock_client.get_system_status.return_value = {
            "health": "healthy",
            "version": "4.3.0",
        }

        # Run analyzer
        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify result
        assert result.success is True
        assert result.objective == "resource"
        assert result.metadata["worker_count"] == 2
        assert result.metadata["resource_health_score"] == 100.0

        # Should have no findings for healthy resources
        assert len(result.findings) == 0
        assert len(result.recommendations) == 0

    @pytest.mark.asyncio
    async def test_detect_high_cpu_warning(self):
        """Test detection of high CPU utilization (warning threshold)."""
        mock_client = create_mock_client(is_cloud=False)

        # Worker with 85% CPU (above 80% warning threshold)
        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {"cpus": 8, "totalMemory": 34359738368, "freeMemory": 17179869184},
                "metrics": {"cpu": {"perc": 0.85, "loadAverage": [5.0, 4.5, 4.0]}},
            }
        ]

        mock_client.get_metrics.return_value = {"workers": {}}
        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have HIGH/MEDIUM finding for CPU warning
        cpu_findings = [f for f in result.findings if "cpu" in f.id.lower()]
        assert len(cpu_findings) == 1
        assert cpu_findings[0].severity in ["medium", "high"]
        assert "85.0%" in cpu_findings[0].description
        assert result.metadata["resource_health_score"] < 100.0

    @pytest.mark.asyncio
    async def test_detect_critical_cpu(self):
        """Test detection of critical CPU utilization."""
        mock_client = create_mock_client(is_cloud=False)

        # Worker with 95% CPU (above 90% critical threshold)
        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {"cpus": 8, "totalMemory": 34359738368, "freeMemory": 17179869184},
                "metrics": {"cpu": {"perc": 0.95, "loadAverage": [10.0, 9.5, 9.0]}},
            }
        ]

        mock_client.get_metrics.return_value = {"workers": {}}
        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have HIGH finding for critical CPU
        cpu_findings = [f for f in result.findings if "cpu-critical" in f.id]
        assert len(cpu_findings) == 1
        assert cpu_findings[0].severity == "high"
        assert "95.0%" in cpu_findings[0].description
        assert "Risk of dropped events" in cpu_findings[0].estimated_impact

        # Should generate CPU capacity recommendation
        cpu_recs = [r for r in result.recommendations if "cpu" in r.id.lower()]
        assert len(cpu_recs) >= 1
        assert cpu_recs[0].priority == "p1"

    @pytest.mark.asyncio
    async def test_detect_high_load_average(self):
        """Test detection of high load average."""
        mock_client = create_mock_client(is_cloud=False)

        # Worker with load average >2x CPU count
        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {"cpus": 4, "totalMemory": 34359738368, "freeMemory": 17179869184},
                "metrics": {
                    "cpu": {
                        "perc": 0.70,  # 70% CPU (below warning)
                        "loadAverage": [10.0, 9.5, 9.0],  # Load 10 on 4 CPUs = 2.5x
                    }
                },
            }
        ]

        mock_client.get_metrics.return_value = {"workers": {}}
        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have finding for high load average
        load_findings = [f for f in result.findings if "load" in f.id.lower()]
        assert len(load_findings) == 1
        assert "Load average (10.00) exceeds 2x CPU count (4)" in load_findings[0].description

    @pytest.mark.asyncio
    async def test_detect_high_memory_warning(self):
        """Test detection of high memory utilization (warning)."""
        mock_client = create_mock_client(is_cloud=False)

        # Worker with 90% memory usage (above 85% warning)
        total_memory = 34359738368  # 32GB
        free_memory = 3435973836  # ~3.2GB free (90% used)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {
                    "cpus": 8,
                    "totalMemory": total_memory,
                    "freeMemory": free_memory,
                },
                "metrics": {"cpu": {"perc": 0.50}},
            }
        ]

        mock_client.get_metrics.return_value = {"workers": {}}
        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have HIGH finding for memory warning
        mem_findings = [f for f in result.findings if "memory" in f.id.lower()]
        assert len(mem_findings) == 1
        assert mem_findings[0].severity == "high"
        assert "90.0%" in mem_findings[0].description
        assert "risk of oom" in mem_findings[0].estimated_impact.lower()

        # Should generate memory capacity recommendation
        mem_recs = [r for r in result.recommendations if "memory" in r.id.lower()]
        assert len(mem_recs) >= 1

    @pytest.mark.asyncio
    async def test_detect_critical_memory(self):
        """Test detection of critical memory pressure."""
        mock_client = create_mock_client(is_cloud=False)

        # Worker with 96% memory usage (above 95% critical)
        total_memory = 34359738368  # 32GB
        free_memory = 1374389534  # ~1.28GB free (96% used)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {
                    "cpus": 8,
                    "totalMemory": total_memory,
                    "freeMemory": free_memory,
                },
                "metrics": {"cpu": {"perc": 0.50}},
            }
        ]

        mock_client.get_metrics.return_value = {"workers": {}}
        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have CRITICAL finding
        mem_findings = [f for f in result.findings if "memory-critical" in f.id]
        assert len(mem_findings) == 1
        assert mem_findings[0].severity == "critical"
        assert "96.0%" in mem_findings[0].description
        assert "URGENT" in mem_findings[0].remediation_steps[0]

    @pytest.mark.asyncio
    async def test_detect_high_disk_utilization(self):
        """Test detection of high disk utilization."""
        mock_client = create_mock_client(is_cloud=False)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {"cpus": 8, "totalMemory": 34359738368, "freeMemory": 17179869184},
                "metrics": {"cpu": {"perc": 0.50}},
            }
        ]

        # 85% disk usage (above 80% warning)
        mock_client.get_metrics.return_value = {
            "workers": {
                "worker-01": {
                    "disk": {
                        "total": 536870912000,  # 500GB
                        "used": 456340275200,  # 425GB (85% used)
                        "free": 80530636800,  # 75GB free
                    }
                }
            }
        }

        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have MEDIUM finding for disk warning
        disk_findings = [f for f in result.findings if "disk-warning" in f.id]
        assert len(disk_findings) == 1
        assert disk_findings[0].severity == "medium"
        assert "85.0%" in disk_findings[0].description

    @pytest.mark.asyncio
    async def test_detect_critical_disk_space(self):
        """Test detection of critical low disk space (<10GB free)."""
        mock_client = create_mock_client(is_cloud=False)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {"cpus": 8, "totalMemory": 34359738368, "freeMemory": 17179869184},
                "metrics": {"cpu": {"perc": 0.50}},
            }
        ]

        # Only 5GB free (below 10GB minimum)
        mock_client.get_metrics.return_value = {
            "workers": {
                "worker-01": {
                    "disk": {
                        "total": 107374182400,  # 100GB
                        "used": 101991989760,  # 95GB
                        "free": 5382192640,  # 5GB free
                    }
                }
            }
        }

        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have CRITICAL finding for low free space
        disk_findings = [f for f in result.findings if "disk-critical" in f.id]
        assert len(disk_findings) >= 1

        critical_free = [
            f for f in disk_findings if "has only" in f.description and "GB free" in f.description
        ]
        assert len(critical_free) == 1
        assert critical_free[0].severity == "critical"
        assert "URGENT" in critical_free[0].remediation_steps[0]

        # Should generate disk capacity recommendation
        disk_recs = [r for r in result.recommendations if "disk" in r.id.lower()]
        assert len(disk_recs) >= 1

    @pytest.mark.asyncio
    async def test_detect_resource_imbalance(self):
        """Test detection of imbalanced resource distribution."""
        mock_client = create_mock_client(is_cloud=False)

        # Workers with significantly different CPU utilization
        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {"cpus": 8, "totalMemory": 34359738368, "freeMemory": 17179869184},
                "metrics": {"cpu": {"perc": 0.20}},  # 20% CPU
            },
            {
                "id": "worker-02",
                "info": {"cpus": 8, "totalMemory": 34359738368, "freeMemory": 17179869184},
                "metrics": {"cpu": {"perc": 0.75}},  # 75% CPU
            },
            {
                "id": "worker-03",
                "info": {"cpus": 8, "totalMemory": 34359738368, "freeMemory": 17179869184},
                "metrics": {"cpu": {"perc": 0.30}},  # 30% CPU
            },
        ]

        mock_client.get_metrics.return_value = {"workers": {}}
        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should detect imbalance (stddev > 0.2)
        imbalance_findings = [f for f in result.findings if "imbalance" in f.id.lower()]
        assert len(imbalance_findings) >= 1
        assert imbalance_findings[0].severity == "medium"
        assert "varies significantly" in imbalance_findings[0].description.lower()

    @pytest.mark.asyncio
    async def test_no_imbalance_detection_single_worker(self):
        """Test that imbalance is not detected with only one worker."""
        mock_client = create_mock_client(is_cloud=False)

        # Single worker
        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {"cpus": 8, "totalMemory": 34359738368, "freeMemory": 17179869184},
                "metrics": {"cpu": {"perc": 0.50}},
            }
        ]

        mock_client.get_metrics.return_value = {"workers": {}}
        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should NOT detect imbalance with single worker
        imbalance_findings = [f for f in result.findings if "imbalance" in f.id.lower()]
        assert len(imbalance_findings) == 0

    @pytest.mark.asyncio
    async def test_calculate_resource_health_score(self):
        """Test resource health score calculation."""
        mock_client = create_mock_client(is_cloud=False)

        # Worker with multiple issues
        total_memory = 34359738368  # 32GB
        free_memory = 3435973836  # ~3.2GB free (90% used - HIGH)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {"cpus": 8, "totalMemory": total_memory, "freeMemory": free_memory},
                "metrics": {"cpu": {"perc": 0.85}},  # 85% CPU (MEDIUM)
            }
        ]

        mock_client.get_metrics.return_value = {
            "workers": {
                "worker-01": {
                    "disk": {
                        "total": 536870912000,
                        "used": 456340275200,  # 85% (MEDIUM)
                        "free": 80530636800,
                    }
                }
            }
        }

        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Score calculation: 100 - (HIGH=15) - (MEDIUM=8) - (MEDIUM=8) = 69
        # (May vary slightly based on exact findings)
        assert result.metadata["resource_health_score"] < 100.0
        assert result.metadata["resource_health_score"] >= 50.0  # Not terrible

    @pytest.mark.asyncio
    async def test_metadata_summary(self):
        """Test that metadata summary is populated correctly."""
        mock_client = create_mock_client(is_cloud=False)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {
                    "cpus": 8,
                    "totalMemory": 34359738368,  # 32GB
                    "freeMemory": 17179869184,
                },
                "metrics": {"cpu": {"perc": 0.45}},
            },
            {
                "id": "worker-02",
                "info": {"cpus": 8, "totalMemory": 34359738368, "freeMemory": 17179869184},
                "metrics": {"cpu": {"perc": 0.55}},
            },
        ]

        mock_client.get_metrics.return_value = {"workers": {}}
        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Check metadata
        assert result.metadata["worker_count"] == 2
        assert result.metadata["total_cpus"] == 16
        assert result.metadata["total_memory_gb"] == 64.0
        assert result.metadata["avg_cpu_utilization"] == 50.0  # (45+55)/2
        assert result.metadata["avg_memory_utilization"] == 50.0  # 50% used
        assert "analysis_timestamp" in result.metadata
        assert "resource_health_score" in result.metadata

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test graceful degradation when API calls fail."""
        mock_client = create_mock_client(is_cloud=False)

        # Simulate API errors - workers fetch will return empty list
        # But we'll make the analyze method itself fail
        mock_client.get_workers.return_value = []
        mock_client.get_metrics.side_effect = Exception("Metrics API connection failed")
        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should still return success (graceful degradation)
        assert result.success is True

        # With empty workers and failed metrics, should complete without findings
        # (graceful degradation means we don't fail the analysis)
        # The error would only be logged, not turned into a finding since
        # we handle errors in _fetch methods gracefully
        assert result.objective == "resource"

    @pytest.mark.asyncio
    async def test_capacity_recommendation_generation(self):
        """Test that capacity recommendations are generated for high findings."""
        mock_client = create_mock_client(is_cloud=False)

        # Workers with critical issues
        total_memory = 34359738368  # 32GB
        free_memory = 1374389534  # ~1.28GB free (96% used - CRITICAL)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {"cpus": 8, "totalMemory": total_memory, "freeMemory": free_memory},
                "metrics": {"cpu": {"perc": 0.95}},  # 95% CPU (HIGH)
            }
        ]

        # Critical disk space
        mock_client.get_metrics.return_value = {
            "workers": {
                "worker-01": {
                    "disk": {
                        "total": 107374182400,  # 100GB
                        "used": 101991989760,  # 95GB
                        "free": 5382192640,  # 5GB free (CRITICAL)
                    }
                }
            }
        }

        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should generate all three capacity recommendations
        assert len(result.recommendations) >= 3

        cpu_rec = next((r for r in result.recommendations if "cpu" in r.id.lower()), None)
        memory_rec = next(
            (r for r in result.recommendations if "memory" in r.id.lower()), None
        )
        disk_rec = next((r for r in result.recommendations if "disk" in r.id.lower()), None)

        assert cpu_rec is not None
        assert cpu_rec.type == "capacity"
        assert cpu_rec.priority == "p1"

        assert memory_rec is not None
        assert memory_rec.type == "capacity"
        assert memory_rec.priority == "p1"

        assert disk_rec is not None
        assert disk_rec.type == "capacity"
        assert disk_rec.priority == "p1"

    @pytest.mark.asyncio
    async def test_skip_zero_memory_workers(self):
        """Test that workers with totalMemory=0 are skipped."""
        mock_client = create_mock_client(is_cloud=False)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {
                    "cpus": 8,
                    "totalMemory": 0,  # Invalid/missing
                    "freeMemory": 0,
                },
                "metrics": {"cpu": {"perc": 0.50}},
            }
        ]

        mock_client.get_metrics.return_value = {"workers": {}}
        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should not crash, should skip memory analysis
        mem_findings = [f for f in result.findings if "memory" in f.id.lower()]
        assert len(mem_findings) == 0

    @pytest.mark.asyncio
    async def test_skip_zero_disk_workers(self):
        """Test that workers with total disk=0 are skipped."""
        mock_client = create_mock_client(is_cloud=False)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {"cpus": 8, "totalMemory": 34359738368, "freeMemory": 17179869184},
                "metrics": {"cpu": {"perc": 0.50}},
            }
        ]

        # Worker with no disk data
        mock_client.get_metrics.return_value = {
            "workers": {
                "worker-01": {
                    "disk": {"total": 0, "used": 0, "free": 0}  # Invalid/missing
                }
            }
        }

        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should not crash, should skip disk analysis
        disk_findings = [f for f in result.findings if "disk" in f.id.lower()]
        assert len(disk_findings) == 0

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end resource analysis workflow."""
        mock_client = create_mock_client(is_cloud=False)

        # Realistic mixed scenario
        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "status": "healthy",
                "info": {
                    "hostname": "worker-01.example.com",
                    "cpus": 8,
                    "totalMemory": 34359738368,  # 32GB
                    "freeMemory": 8589934592,  # 8GB free (75% used)
                },
                "metrics": {
                    "cpu": {"perc": 0.65, "loadAverage": [4.0, 3.8, 3.5]},  # 65% CPU - OK
                },
            },
            {
                "id": "worker-02",
                "status": "healthy",
                "info": {
                    "hostname": "worker-02.example.com",
                    "cpus": 8,
                    "totalMemory": 34359738368,
                    "freeMemory": 3435973836,  # ~3.2GB free (90% used - HIGH)
                },
                "metrics": {
                    "cpu": {"perc": 0.88, "loadAverage": [6.5, 6.2, 6.0]},  # 88% CPU - HIGH
                },
            },
        ]

        mock_client.get_metrics.return_value = {
            "workers": {
                "worker-01": {
                    "disk": {
                        "total": 536870912000,
                        "used": 107374182400,  # 20% - OK
                        "free": 429496729600,
                    }
                },
                "worker-02": {
                    "disk": {
                        "total": 536870912000,
                        "used": 483183820800,  # 90% - HIGH
                        "free": 53687091200,
                    }
                },
            }
        }

        mock_client.get_system_status.return_value = {
            "health": "healthy",
            "version": "4.3.0",
        }

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify comprehensive analysis
        assert result.success is True
        assert result.objective == "resource"
        assert result.metadata["worker_count"] == 2

        # Should have findings for worker-02
        assert len(result.findings) >= 2  # CPU + disk at minimum

        # Should have capacity recommendations
        assert len(result.recommendations) >= 1

        # Health score should be degraded
        assert result.metadata["resource_health_score"] < 100.0
        assert result.metadata["resource_health_score"] > 50.0

        # Verify affected components
        affected = set()
        for finding in result.findings:
            affected.update(finding.affected_components)

        assert "worker-worker-02" in affected or any(
            "worker-02" in comp for comp in affected
        )

    @pytest.mark.asyncio
    async def test_cribl_cloud_skips_disk_metrics(self):
        """Test that disk metrics are skipped for Cribl Cloud deployments."""
        # Mock Cribl Cloud client
        mock_client = create_mock_client(is_cloud=True)

        mock_client.get_workers.return_value = [
            {
                "id": "worker-01",
                "info": {"cpus": 8, "totalMemory": 34359738368, "freeMemory": 17179869184},
                "metrics": {"cpu": {"perc": 0.50}},
            }
        ]

        # Include disk metrics in response (but they should be ignored)
        mock_client.get_metrics.return_value = {
            "workers": {
                "worker-01": {
                    "disk": {
                        "total": 536870912000,
                        "used": 483183820800,  # 90% - would trigger finding if not Cloud
                        "free": 53687091200,
                    }
                }
            }
        }

        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should NOT have disk findings (skipped for Cloud)
        disk_findings = [f for f in result.findings if "disk" in f.id.lower()]
        assert len(disk_findings) == 0

        # Should have metadata indicating disk metrics were skipped
        assert result.metadata.get("disk_metrics_skipped") is True
        assert "Cribl Cloud" in result.metadata.get("disk_metrics_skip_reason", "")

        # Should still analyze CPU and memory
        assert result.success is True
        assert result.metadata.get("worker_count") == 1

    @pytest.mark.asyncio
    async def test_edge_deployment_analysis(self):
        """Test ResourceAnalyzer works with Edge deployments."""
        # Create mock Edge client
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = True
        mock_client.is_stream = False
        mock_client.is_cloud = False
        mock_client.product_type = "edge"

        # Mock Edge node data (similar to Stream workers)
        mock_client.get_workers.return_value = [
            {
                "id": "edge-node-01",
                "info": {
                    "hostname": "edge-node-01.example.com",
                    "cpus": 4,
                    "totalMemory": 16 * 1024**3,  # 16GB
                    "freeMemory": 8 * 1024**3,    # 8GB free (50% used)
                },
                "metrics": {
                    "cpu": {
                        "perc": 0.45,  # 45% CPU
                        "loadAverage": [2.1, 1.9, 1.8]
                    }
                }
            }
        ]

        mock_client.get_metrics.return_value = {}
        mock_client.get_system_status.return_value = {}

        # Run analysis
        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Verify Edge-specific metadata
        assert result.success is True
        assert result.metadata["product_type"] == "edge"
        assert result.metadata["worker_count"] == 1

        # Should analyze CPU and memory for Edge nodes
        assert "resource_health_score" in result.metadata
        assert "avg_cpu_utilization" in result.metadata

        # Verify API calls
        mock_client.get_workers.assert_called_once()

    @pytest.mark.asyncio
    async def test_edge_high_resource_utilization(self):
        """Test Edge node with high resource utilization triggers findings."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = True
        mock_client.is_stream = False
        mock_client.is_cloud = False
        mock_client.product_type = "edge"

        # Mock Edge node with high CPU and memory usage
        mock_client.get_workers.return_value = [
            {
                "id": "edge-node-overloaded",
                "info": {
                    "hostname": "edge-node-overloaded.example.com",
                    "cpus": 2,
                    "totalMemory": 8 * 1024**3,   # 8GB
                    "freeMemory": 0.5 * 1024**3,  # 0.5GB free (93.75% used - critical)
                },
                "metrics": {
                    "cpu": {
                        "perc": 0.92,  # 92% CPU (critical)
                        "loadAverage": [4.5, 4.2, 4.0]
                    }
                }
            }
        ]

        mock_client.get_metrics.return_value = {}
        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should have critical/high findings for CPU and memory
        cpu_findings = [f for f in result.findings if "cpu" in f.id.lower()]
        memory_findings = [f for f in result.findings if "memory" in f.id.lower()]

        assert len(cpu_findings) > 0
        assert len(memory_findings) > 0

        # At least one should be high/critical severity
        high_severity = [f for f in result.findings if f.severity in ["high", "critical"]]
        assert len(high_severity) >= 2

    @pytest.mark.asyncio
    async def test_edge_product_type_metadata(self):
        """Test Edge product type is captured in metadata."""
        mock_client = AsyncMock(spec=CriblAPIClient)
        mock_client.is_edge = True
        mock_client.is_stream = False
        mock_client.is_cloud = False
        mock_client.product_type = "edge"

        # Mock empty responses (no nodes)
        mock_client.get_workers.return_value = []
        mock_client.get_metrics.return_value = {}
        mock_client.get_system_status.return_value = {}

        analyzer = ResourceAnalyzer()
        result = await analyzer.analyze(mock_client)

        # Should succeed and capture Edge product type
        assert result.success is True
        assert result.metadata["product_type"] == "edge"
        assert result.metadata["worker_count"] == 0
