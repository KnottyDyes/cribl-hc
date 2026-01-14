"""
Unit tests for PipelineBottleneckAnalyzer.

Tests all 4 check types:
1. Silent failure detection
2. Drop rate variance detection
3. Processing time anomaly detection
4. Throughput cliff detection
"""

from unittest.mock import AsyncMock

import pytest

from cribl_hc.analyzers.pipeline_bottleneck import PipelineBottleneckAnalyzer


class TestPipelineBottleneckAnalyzer:
    """Tests for PipelineBottleneckAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create PipelineBottleneckAnalyzer instance."""
        return PipelineBottleneckAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = AsyncMock()
        client.get_pipelines = AsyncMock(return_value={})
        client.get_metrics = AsyncMock(return_value={})
        client.is_cloud = False
        return client

    # ===== Basic Analyzer Properties =====

    def test_objective_name(self, analyzer):
        """Test analyzer objective name."""
        assert analyzer.objective_name == "pipeline_bottleneck"

    def test_supported_products(self, analyzer):
        """Test supported products."""
        assert analyzer.supported_products == ["stream", "edge"]

    def test_get_description(self, analyzer):
        """Test analyzer description."""
        desc = analyzer.get_description()
        assert "bottleneck" in desc.lower()
        assert "data loss" in desc.lower()

    def test_get_estimated_api_calls(self, analyzer):
        """Test estimated API calls."""
        assert analyzer.get_estimated_api_calls() == 2

    def test_get_required_permissions(self, analyzer):
        """Test required permissions."""
        perms = analyzer.get_required_permissions()
        assert "read:pipelines" in perms
        assert "read:metrics" in perms

    # ===== Check 1: Silent Failure Detection =====

    @pytest.mark.asyncio
    async def test_silent_failure_critical(self, analyzer, mock_client):
        """Test critical silent failure detection (in > 0, out = 0)."""
        mock_client.get_pipelines.return_value = {
            "pipe-silent": {
                "id": "pipe-silent",
                "disabled": False,
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-silent": {
                    "in": {"events": 5000},
                    "out": {"events": 0},
                    "drop": {"events": 0},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == "critical"
        assert "silent failure" in finding.title.lower()
        assert finding.metadata["in_events"] == 5000
        assert finding.metadata["out_events"] == 0
        assert finding.metadata["drop_rate"] == 1.0  # 100% drop

    @pytest.mark.asyncio
    async def test_silent_failure_disabled_skipped(self, analyzer, mock_client):
        """Test that silent failure check skips disabled pipelines."""
        mock_client.get_pipelines.return_value = {
            "pipe-disabled": {
                "id": "pipe-disabled",
                "disabled": True,  # Explicitly disabled
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-disabled": {
                    "in": {"events": 1000},
                    "out": {"events": 0},
                    "drop": {"events": 0},
                    "error": {"events": 0},
                    "processingTime": 25.0,
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        # Should not flag disabled pipeline as silent failure
        critical_findings = result.get_critical_findings()
        assert len(critical_findings) == 0

    @pytest.mark.asyncio
    async def test_silent_failure_normal_pipeline(self, analyzer, mock_client):
        """Test normal pipeline passes silent failure check."""
        mock_client.get_pipelines.return_value = {
            "pipe-normal": {
                "id": "pipe-normal",
                "disabled": False,
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-normal": {
                    "in": {"events": 10000},
                    "out": {"events": 9500},
                    "drop": {"events": 500},
                    "error": {"events": 0},
                    "processingTime": 75.0,
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        # Normal pipeline should not generate silent failure finding
        critical_findings = result.get_critical_findings()
        assert len(critical_findings) == 0

    # ===== Check 2: Drop Rate Variance =====

    @pytest.mark.asyncio
    async def test_drop_rate_matches_expected(self, analyzer, mock_client):
        """Test drop rate matching expected doesn't trigger finding."""
        mock_client.get_pipelines.return_value = {
            "pipe-filter": {
                "id": "pipe-filter",
                "disabled": False,
                "expectedDropRate": 10.0,  # 10% expected
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-filter": {
                    "in": {"events": 1000},
                    "out": {"events": 900},
                    "drop": {"events": 100},  # 10% drop
                    "error": {"events": 0},
                    "processingTime": 50.0,
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        # Should not flag findings for expected drop rate
        high_findings = [f for f in result.findings if "drop_variance" in f.id]
        assert len(high_findings) == 0

    @pytest.mark.asyncio
    async def test_drop_rate_significantly_exceeds_expected_high(self, analyzer, mock_client):
        """Test HIGH severity when drop rate exceeds expected by >20%."""
        mock_client.get_pipelines.return_value = {
            "pipe-heavy-drop": {
                "id": "pipe-heavy-drop",
                "disabled": False,
                "expectedDropRate": 5.0,  # 5% expected
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-heavy-drop": {
                    "in": {"events": 1000},
                    "out": {"events": 780},
                    "drop": {"events": 220},  # 22% actual (variance: 340%)
                    "error": {"events": 0},
                    "processingTime": 50.0,
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        # Should find HIGH severity drop rate variance
        high_findings = [f for f in result.findings if "drop_variance" in f.id]
        assert len(high_findings) == 1
        assert high_findings[0].severity == "high"
        assert high_findings[0].metadata["actual_drop_rate_percent"] == 22.0

    @pytest.mark.asyncio
    async def test_drop_rate_slightly_exceeds_expected_medium(self, analyzer, mock_client):
        """Test MEDIUM severity when drop rate slightly exceeds expected by <20%."""
        mock_client.get_pipelines.return_value = {
            "pipe-slight-drop": {
                "id": "pipe-slight-drop",
                "disabled": False,
                "expectedDropRate": 5.0,
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-slight-drop": {
                    "in": {"events": 1000},
                    "out": {"events": 940},
                    "drop": {"events": 60},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        medium_findings = [
            f for f in result.findings if f.severity == "medium" and "drop_variance" in f.id
        ]
        assert len(medium_findings) == 1
        assert medium_findings[0].metadata["actual_drop_rate_percent"] == 6.0

    @pytest.mark.asyncio
    async def test_drop_rate_zero_input_skipped(self, analyzer, mock_client):
        """Test drop rate check skipped when no input events."""
        mock_client.get_pipelines.return_value = {
            "pipe-no-input": {
                "id": "pipe-no-input",
                "disabled": False,
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-no-input": {
                    "in": {"events": 0},
                    "out": {"events": 0},
                    "drop": {"events": 0},
                    "error": {"events": 0},
                    "processingTime": 0.0,
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        # No drop variance findings (check skipped on zero input)
        drop_variance_findings = [f for f in result.findings if "drop_variance" in f.id]
        assert len(drop_variance_findings) == 0

    # ===== Check 3: Processing Time Anomalies =====

    @pytest.mark.asyncio
    async def test_processing_time_normal(self, analyzer, mock_client):
        """Test normal processing time doesn't trigger finding."""
        mock_client.get_pipelines.return_value = {
            "pipe-fast": {
                "id": "pipe-fast",
                "disabled": False,
                "baselineProcessingTimeMs": 100.0,
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-fast": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 105.0,  # 5% increase (< 50% threshold)
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        # No processing time anomaly findings
        time_anomaly_findings = [f for f in result.findings if "time_anomaly" in f.id]
        assert len(time_anomaly_findings) == 0

    @pytest.mark.asyncio
    async def test_processing_time_50percent_increase(self, analyzer, mock_client):
        """Test MEDIUM severity when processing time 50% over baseline."""
        mock_client.get_pipelines.return_value = {
            "pipe-slow": {
                "id": "pipe-slow",
                "disabled": False,
                "baselineProcessingTimeMs": 100.0,
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-slow": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 150.0,  # 50% increase
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        # Should find MEDIUM severity processing time anomaly
        time_anomaly_findings = [
            f for f in result.findings if f.severity == "medium" and "time_anomaly" in f.id
        ]
        assert len(time_anomaly_findings) == 1
        assert time_anomaly_findings[0].metadata["increase_percent"] == 50.0

    @pytest.mark.asyncio
    async def test_processing_time_2x_increase(self, analyzer, mock_client):
        """Test MEDIUM severity when processing time 2x baseline."""
        mock_client.get_pipelines.return_value = {
            "pipe-very-slow": {
                "id": "pipe-very-slow",
                "disabled": False,
                "baselineProcessingTimeMs": 100.0,
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-very-slow": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 200.0,  # 100% increase (2x)
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        # Should find MEDIUM severity processing time anomaly
        time_anomaly_findings = [f for f in result.findings if "time_anomaly" in f.id]
        assert len(time_anomaly_findings) == 1
        assert time_anomaly_findings[0].metadata["increase_percent"] == 100.0

    @pytest.mark.asyncio
    async def test_processing_time_zero_skipped(self, analyzer, mock_client):
        """Test processing time check skipped when no processing time data."""
        mock_client.get_pipelines.return_value = {
            "pipe-no-time": {
                "id": "pipe-no-time",
                "disabled": False,
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-no-time": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 0.0,  # No processing time data
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        # No processing time anomaly findings (check skipped)
        time_anomaly_findings = [f for f in result.findings if "time_anomaly" in f.id]
        assert len(time_anomaly_findings) == 0

    # ===== Check 4: Throughput Cliff Detection =====

    @pytest.mark.asyncio
    async def test_throughput_balanced(self, analyzer, mock_client):
        """Test balanced throughput distribution doesn't trigger finding."""
        mock_client.get_pipelines.return_value = {
            "pipe1": {"id": "pipe1", "disabled": False},
            "pipe2": {"id": "pipe2", "disabled": False},
            "pipe3": {"id": "pipe3", "disabled": False},
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe1": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
                "pipe2": {
                    "in": {"events": 1100},
                    "out": {"events": 1050},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
                "pipe3": {
                    "in": {"events": 950},
                    "out": {"events": 900},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
            }
        }

        result = await analyzer.analyze(mock_client)

        # No throughput cliff findings (balanced load)
        cliff_findings = [f for f in result.findings if "throughput_cliff" in f.id]
        assert len(cliff_findings) == 0

    @pytest.mark.asyncio
    async def test_throughput_cliff_3x_mean(self, analyzer, mock_client):
        """Test throughput cliff detection at 3x mean."""
        mock_client.get_pipelines.return_value = {
            "pipe-1": {"id": "pipe-1", "disabled": False},
            "pipe-2": {"id": "pipe-2", "disabled": False},
            "pipe-3": {"id": "pipe-3", "disabled": False},
            "pipe-hot": {"id": "pipe-hot", "disabled": False},
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-1": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
                "pipe-2": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
                "pipe-3": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
                "pipe-hot": {
                    "in": {"events": 10000},
                    "out": {"events": 9500},
                    "drop": {"events": 500},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
            }
        }

        result = await analyzer.analyze(mock_client)

        cliff_findings = [f for f in result.findings if "throughput_cliff" in f.id]
        assert len(cliff_findings) == 1
        assert cliff_findings[0].severity == "medium"
        assert "pipe-hot" in cliff_findings[0].title

    @pytest.mark.asyncio
    async def test_throughput_cliff_extreme_10x(self, analyzer, mock_client):
        """Test extreme throughput cliff at 10x mean with more pipelines."""
        mock_client.get_pipelines.return_value = {
            "pipe-1": {"id": "pipe-1", "disabled": False},
            "pipe-2": {"id": "pipe-2", "disabled": False},
            "pipe-3": {"id": "pipe-3", "disabled": False},
            "pipe-4": {"id": "pipe-4", "disabled": False},
            "pipe-5": {"id": "pipe-5", "disabled": False},
            "pipe-massive": {"id": "pipe-massive", "disabled": False},
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-1": {
                    "in": {"events": 500},
                    "out": {"events": 475},
                    "drop": {"events": 25},
                    "error": {"events": 0},
                    "processingTime": 25.0,
                },
                "pipe-2": {
                    "in": {"events": 500},
                    "out": {"events": 475},
                    "drop": {"events": 25},
                    "error": {"events": 0},
                    "processingTime": 25.0,
                },
                "pipe-3": {
                    "in": {"events": 500},
                    "out": {"events": 475},
                    "drop": {"events": 25},
                    "error": {"events": 0},
                    "processingTime": 25.0,
                },
                "pipe-4": {
                    "in": {"events": 500},
                    "out": {"events": 475},
                    "drop": {"events": 25},
                    "error": {"events": 0},
                    "processingTime": 25.0,
                },
                "pipe-5": {
                    "in": {"events": 500},
                    "out": {"events": 475},
                    "drop": {"events": 25},
                    "error": {"events": 0},
                    "processingTime": 25.0,
                },
                "pipe-massive": {
                    "in": {"events": 10000},
                    "out": {"events": 9500},
                    "drop": {"events": 500},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
            }
        }

        result = await analyzer.analyze(mock_client)

        cliff_findings = [f for f in result.findings if "throughput_cliff" in f.id]
        assert len(cliff_findings) == 1
        z_score = cliff_findings[0].metadata["z_score"]
        assert z_score >= analyzer.THROUGHPUT_CLIFF_STDEV_THRESHOLD

    # ===== API Integration Tests =====

    @pytest.mark.asyncio
    async def test_analyze_no_pipelines(self, analyzer, mock_client):
        """Test analysis with no pipelines configured."""
        mock_client.get_pipelines.return_value = {}
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        assert "no pipelines" in result.findings[0].title.lower()

    @pytest.mark.asyncio
    async def test_analyze_metrics_unavailable(self, analyzer, mock_client):
        """Test analysis with metrics unavailable (cloud deployment)."""
        mock_client.get_pipelines.return_value = {"pipe1": {"id": "pipe1", "disabled": False}}
        mock_client.get_metrics.return_value = {}
        mock_client.is_cloud = True

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert len(result.findings) == 1
        assert "metrics unavailable" in result.findings[0].title.lower()
        assert result.findings[0].metadata["deployment_type"] == "cloud"

    @pytest.mark.asyncio
    async def test_analyze_full_scenario(self, analyzer, mock_client):
        """Test full analysis scenario with multiple issues."""
        mock_client.get_pipelines.return_value = {
            "pipe-silent": {
                "id": "pipe-silent",
                "disabled": False,
            },
            "pipe-bad-drop": {
                "id": "pipe-bad-drop",
                "disabled": False,
                "expectedDropRate": 5.0,
            },
            "pipe-slow": {
                "id": "pipe-slow",
                "disabled": False,
                "baselineProcessingTimeMs": 50.0,
            },
            "pipe-1": {"id": "pipe-1", "disabled": False},
            "pipe-2": {"id": "pipe-2", "disabled": False},
            "pipe-hot": {"id": "pipe-hot", "disabled": False},
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-silent": {
                    "in": {"events": 5000},
                    "out": {"events": 0},
                    "drop": {"events": 0},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
                "pipe-bad-drop": {
                    "in": {"events": 1000},
                    "out": {"events": 780},
                    "drop": {"events": 220},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
                "pipe-slow": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 100.0,
                },
                "pipe-1": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
                "pipe-2": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
                "pipe-hot": {
                    "in": {"events": 10000},
                    "out": {"events": 9500},
                    "drop": {"events": 500},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True

        critical_findings = result.get_critical_findings()
        assert len(critical_findings) == 1
        assert "silent failure" in critical_findings[0].title.lower()

        high_findings = result.get_high_findings()
        assert len(high_findings) == 1
        assert "drop rate" in high_findings[0].title.lower()

        medium_findings = [f for f in result.findings if f.severity == "medium"]
        assert len(medium_findings) >= 1

        cliff_findings = [f for f in result.findings if "throughput_cliff" in f.id]
        assert len(cliff_findings) == 1

    @pytest.mark.asyncio
    async def test_analyze_error_handling(self, analyzer, mock_client):
        """Test error handling during analysis."""
        mock_client.get_pipelines.side_effect = Exception("API error")

        result = await analyzer.analyze(mock_client)

        assert result.success is False
        assert "API error" in result.error

    # ===== Helper Method Tests =====

    def test_get_expected_drop_rate_from_config(self, analyzer):
        """Test extracting expected drop rate from config."""
        config = {"expectedDropRate": 8.5}
        rate = analyzer._get_expected_drop_rate(config)
        assert rate == 8.5

    def test_get_expected_drop_rate_default(self, analyzer):
        """Test default expected drop rate when not configured."""
        config = {}
        rate = analyzer._get_expected_drop_rate(config)
        assert rate == analyzer.DEFAULT_EXPECTED_DROP_RATE

    def test_get_baseline_processing_time_from_config(self, analyzer):
        """Test extracting baseline processing time from config."""
        config = {"baselineProcessingTimeMs": 200.0}
        baseline = analyzer._get_baseline_processing_time(config)
        assert baseline == 200.0

    def test_get_baseline_processing_time_default(self, analyzer):
        """Test default baseline processing time when not configured."""
        config = {}
        baseline = analyzer._get_baseline_processing_time(config)
        assert baseline == analyzer.DEFAULT_BASELINE_PROCESSING_TIME_MS

    # ===== Result Metadata Tests =====

    @pytest.mark.asyncio
    async def test_result_metadata_populated(self, analyzer, mock_client):
        """Test that result metadata is properly populated."""
        mock_client.get_pipelines.return_value = {
            "pipe1": {"id": "pipe1", "disabled": False},
            "pipe2": {"id": "pipe2", "disabled": False},
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe1": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
                "pipe2": {
                    "in": {"events": 1000},
                    "out": {"events": 950},
                    "drop": {"events": 50},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                },
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.metadata["total_pipelines"] == 2
        assert result.metadata["pipelines_analyzed"] == 2
        assert "analysis_timestamp" in result.metadata
        assert "overall_status" in result.metadata

    @pytest.mark.asyncio
    async def test_recommendations_generated_for_findings(self, analyzer, mock_client):
        """Test that recommendations are generated for findings."""
        mock_client.get_pipelines.return_value = {
            "pipe-silent": {
                "id": "pipe-silent",
                "disabled": False,
            }
        }
        mock_client.get_metrics.return_value = {
            "pipelines": {
                "pipe-silent": {
                    "in": {"events": 5000},
                    "out": {"events": 0},
                    "drop": {"events": 0},
                    "error": {"events": 0},
                    "processingTime": 50.0,
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        # Should have at least one recommendation for the silent failure finding
        assert len(result.recommendations) >= 1
        rec = result.recommendations[0]
        assert rec.priority == "p0"  # Emergency priority
        assert "silent failure" in rec.title.lower()
