"""
Unit tests for BackpressureAnalyzer.

Tests destination backpressure detection, persistent queue monitoring,
HTTP retry pattern analysis, and queue exhaustion prediction.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from cribl_hc.analyzers.backpressure import BackpressureAnalyzer


class TestBackpressureAnalyzer:
    """Tests for BackpressureAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create BackpressureAnalyzer instance."""
        return BackpressureAnalyzer()

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = AsyncMock()
        client.get_outputs = AsyncMock(return_value=[])
        client.get_metrics = AsyncMock(return_value={})
        return client

    def test_objective_name(self, analyzer):
        """Test analyzer objective name."""
        assert analyzer.objective_name == "backpressure"

    def test_get_description(self, analyzer):
        """Test analyzer description."""
        desc = analyzer.get_description()
        assert "backpressure" in desc.lower()
        assert "queue" in desc.lower()

    def test_get_estimated_api_calls(self, analyzer):
        """Test estimated API calls."""
        assert analyzer.get_estimated_api_calls() == 2

    def test_get_required_permissions(self, analyzer):
        """Test required permissions."""
        perms = analyzer.get_required_permissions()
        assert "read:outputs" in perms
        assert "read:metrics" in perms

    @pytest.mark.asyncio
    async def test_analyze_no_outputs(self, analyzer, mock_client):
        """Test analysis with no outputs configured."""
        mock_client.get_outputs.return_value = []
        mock_client.get_metrics.return_value = {}

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_outputs"] == 0
        assert len(result.findings) == 1
        assert result.findings[0].id == "backpressure-no-outputs"

    @pytest.mark.asyncio
    async def test_analyze_healthy_outputs(self, analyzer, mock_client):
        """Test analysis with healthy outputs."""
        mock_client.get_outputs.return_value = [
            {"id": "splunk-dest", "type": "splunk_hec", "pqEnabled": False},
            {"id": "s3-dest", "type": "s3", "pqEnabled": False}
        ]
        mock_client.get_metrics.return_value = {
            "outputs": {
                "splunk-dest": {
                    "out": {"events": 10000, "bytes": 1000000},
                    "blocked": {"events": 0}
                },
                "s3-dest": {
                    "out": {"events": 5000, "bytes": 500000},
                    "blocked": {"events": 0}
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["total_outputs"] == 2
        assert result.metadata["outputs_with_backpressure"] == 0
        assert result.metadata["overall_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_analyze_detects_backpressure_warning(self, analyzer, mock_client):
        """Test analyzer detects warning-level backpressure."""
        mock_client.get_outputs.return_value = [
            {"id": "slow-dest", "type": "http", "pqEnabled": False}
        ]
        mock_client.get_metrics.return_value = {
            "outputs": {
                "slow-dest": {
                    "out": {"events": 8500, "bytes": 850000},
                    "blocked": {"events": 1500}  # 15% blocked
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["outputs_with_backpressure"] == 1

        backpressure_findings = [f for f in result.findings if "backpressure-output" in f.id]
        assert len(backpressure_findings) == 1
        assert backpressure_findings[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_analyze_detects_critical_backpressure(self, analyzer, mock_client):
        """Test analyzer detects critical backpressure (>25%)."""
        mock_client.get_outputs.return_value = [
            {"id": "failing-dest", "type": "splunk_hec", "pqEnabled": False}
        ]
        mock_client.get_metrics.return_value = {
            "outputs": {
                "failing-dest": {
                    "out": {"events": 7000, "bytes": 700000},
                    "blocked": {"events": 3000}  # 30% blocked
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["outputs_critical_backpressure"] == 1

        findings = [f for f in result.findings if "backpressure-output" in f.id]
        assert len(findings) == 1
        assert findings[0].severity == "high"

        # Should also have a recommendation
        recs = [r for r in result.recommendations if "rec-backpressure" in r.id]
        assert len(recs) == 1
        assert recs[0].priority == "p1"

    @pytest.mark.asyncio
    async def test_analyze_pq_warning(self, analyzer, mock_client):
        """Test analyzer detects PQ filling at warning level."""
        mock_client.get_outputs.return_value = [
            {
                "id": "dest-with-pq",
                "type": "http",
                "pqEnabled": True,
                "pq": {"maxSize": "10GB"}
            }
        ]
        mock_client.get_metrics.return_value = {
            "outputs": {},
            "pq": {
                "dest-with-pq": {
                    "size_bytes": 7 * 1024 ** 3,  # 7GB = 70%
                    "max_size_bytes": 10 * 1024 ** 3,
                    "events": 1000000
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["pq_warnings"] == 1

        pq_findings = [f for f in result.findings if "backpressure-pq" in f.id]
        assert len(pq_findings) == 1
        assert pq_findings[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_analyze_pq_critical(self, analyzer, mock_client):
        """Test analyzer detects PQ filling at critical level (>90%)."""
        mock_client.get_outputs.return_value = [
            {
                "id": "critical-pq",
                "type": "http",
                "pqEnabled": True,
                "pq": {"maxSize": "10GB"}
            }
        ]
        mock_client.get_metrics.return_value = {
            "outputs": {},
            "pq": {
                "critical-pq": {
                    "size_bytes": 9.5 * 1024 ** 3,  # 9.5GB = 95%
                    "max_size_bytes": 10 * 1024 ** 3,
                    "events": 2000000
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["pq_critical"] == 1

        pq_findings = [f for f in result.findings if "backpressure-pq" in f.id]
        assert len(pq_findings) == 1
        assert pq_findings[0].severity == "high"

        # Should have urgent recommendation
        recs = [r for r in result.recommendations if "rec-pq-drain" in r.id]
        assert len(recs) == 1
        assert recs[0].priority == "p0"

    @pytest.mark.asyncio
    async def test_analyze_http_retries_warning(self, analyzer, mock_client):
        """Test analyzer detects HTTP retry patterns at warning level."""
        mock_client.get_outputs.return_value = [
            {"id": "http-dest", "type": "http", "pqEnabled": False}
        ]
        mock_client.get_metrics.return_value = {
            "outputs": {
                "http-dest": {
                    "out": {"events": 10000, "bytes": 1000000},
                    "blocked": {"events": 0},
                    "errors": {"5xx": 600, "total": 650},  # 6% error rate
                    "retries": 500
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["http_outputs_with_retries"] == 1

        retry_findings = [f for f in result.findings if "http-retries" in f.id]
        assert len(retry_findings) == 1
        assert retry_findings[0].severity == "medium"

    @pytest.mark.asyncio
    async def test_analyze_http_retries_critical(self, analyzer, mock_client):
        """Test analyzer detects critical HTTP retry rates (>15%)."""
        mock_client.get_outputs.return_value = [
            {"id": "failing-http", "type": "splunk_hec", "pqEnabled": False}
        ]
        mock_client.get_metrics.return_value = {
            "outputs": {
                "failing-http": {
                    "out": {"events": 10000, "bytes": 1000000},
                    "blocked": {"events": 0},
                    "errors": {"5xx": 2000, "total": 2100},  # 20% error rate
                    "retries": 1800
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True

        retry_findings = [f for f in result.findings if "http-retries" in f.id]
        assert len(retry_findings) == 1
        assert retry_findings[0].severity == "high"

    @pytest.mark.asyncio
    async def test_analyze_queue_exhaustion_prediction(self, analyzer, mock_client):
        """Test analyzer predicts queue exhaustion."""
        mock_client.get_outputs.return_value = [
            {
                "id": "filling-pq",
                "type": "http",
                "pqEnabled": True,
                "pq": {"maxSize": "10GB"}
            }
        ]
        mock_client.get_metrics.return_value = {
            "outputs": {},
            "pq": {
                "filling-pq": {
                    "size_bytes": 5 * 1024 ** 3,  # 5GB
                    "max_size_bytes": 10 * 1024 ** 3,
                    "events": 1000000,
                    "growth_rate_bps": 500000,  # 500KB/s growth
                    "drain_rate_bps": 100000    # 100KB/s drain = 400KB/s net growth
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["exhaustion_predictions"] >= 1

        exhaustion_findings = [f for f in result.findings if "exhaustion" in f.id]
        assert len(exhaustion_findings) >= 1

    @pytest.mark.asyncio
    async def test_analyze_multiple_issues(self, analyzer, mock_client):
        """Test analyzer handles multiple simultaneous issues."""
        mock_client.get_outputs.return_value = [
            {"id": "dest-1", "type": "http", "pqEnabled": False},
            {
                "id": "dest-2",
                "type": "splunk_hec",
                "pqEnabled": True,
                "pq": {"maxSize": "5GB"}
            }
        ]
        mock_client.get_metrics.return_value = {
            "outputs": {
                "dest-1": {
                    "out": {"events": 7000, "bytes": 700000},
                    "blocked": {"events": 3000},  # 30% blocked - critical
                    "errors": {"5xx": 100, "total": 100}
                },
                "dest-2": {
                    "out": {"events": 10000, "bytes": 1000000},
                    "blocked": {"events": 0}
                }
            },
            "pq": {
                "dest-2": {
                    "size_bytes": 4.8 * 1024 ** 3,  # 96% - critical
                    "max_size_bytes": 5 * 1024 ** 3,
                    "events": 500000
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["outputs_critical_backpressure"] == 1
        assert result.metadata["pq_critical"] == 1
        assert result.metadata["overall_status"] == "critical"
        assert len(result.findings) >= 2

    @pytest.mark.asyncio
    async def test_analyze_handles_api_error(self, analyzer, mock_client):
        """Test analyzer handles API errors gracefully."""
        mock_client.get_outputs.side_effect = Exception("API connection failed")

        result = await analyzer.analyze(mock_client)

        assert result.success is False
        assert "error" in result.metadata

        error_findings = [f for f in result.findings if "error" in f.id]
        assert len(error_findings) == 1
        assert error_findings[0].severity == "critical"

    def test_parse_size_to_bytes(self, analyzer):
        """Test size parsing utility."""
        assert analyzer._parse_size_to_bytes(1024) == 1024
        assert analyzer._parse_size_to_bytes("10GB") == 10 * 1024 ** 3
        assert analyzer._parse_size_to_bytes("5gb") == 5 * 1024 ** 3
        assert analyzer._parse_size_to_bytes("100MB") == 100 * 1024 ** 2
        assert analyzer._parse_size_to_bytes("1TB") == 1024 ** 4
        assert analyzer._parse_size_to_bytes("invalid") == 0

    @pytest.mark.asyncio
    async def test_analyze_with_destinations_metric_key(self, analyzer, mock_client):
        """Test analyzer handles 'destinations' metric key (alternative format)."""
        mock_client.get_outputs.return_value = [
            {"id": "alt-dest", "type": "s3", "pqEnabled": False}
        ]
        mock_client.get_metrics.return_value = {
            "destinations": {  # Alternative key name
                "alt-dest": {
                    "out": {"events": 5000, "bytes": 500000},
                    "blocked": {"events": 1000}  # 20% blocked
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["outputs_with_backpressure"] == 1

    @pytest.mark.asyncio
    async def test_analyze_non_http_outputs_skip_retry_analysis(self, analyzer, mock_client):
        """Test that non-HTTP outputs skip retry analysis."""
        mock_client.get_outputs.return_value = [
            {"id": "s3-dest", "type": "s3", "pqEnabled": False},
            {"id": "kafka-dest", "type": "kafka", "pqEnabled": False}
        ]
        mock_client.get_metrics.return_value = {
            "outputs": {
                "s3-dest": {
                    "out": {"events": 10000},
                    "blocked": {"events": 0},
                    "errors": {"5xx": 500}  # Would be 5% if analyzed
                },
                "kafka-dest": {
                    "out": {"events": 10000},
                    "blocked": {"events": 0},
                    "errors": {"5xx": 500}
                }
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        assert result.metadata["http_outputs_with_retries"] == 0

        # No HTTP retry findings for non-HTTP outputs
        retry_findings = [f for f in result.findings if "http-retries" in f.id]
        assert len(retry_findings) == 0

    @pytest.mark.asyncio
    async def test_backpressure_health_score_calculation(self, analyzer, mock_client):
        """Test backpressure health score is calculated correctly."""
        mock_client.get_outputs.return_value = [
            {"id": "healthy-1", "type": "http", "pqEnabled": False},
            {"id": "healthy-2", "type": "s3", "pqEnabled": False},
            {"id": "unhealthy", "type": "splunk_hec", "pqEnabled": False}
        ]
        mock_client.get_metrics.return_value = {
            "outputs": {
                "healthy-1": {"out": {"events": 10000}, "blocked": {"events": 0}},
                "healthy-2": {"out": {"events": 10000}, "blocked": {"events": 0}},
                "unhealthy": {"out": {"events": 7000}, "blocked": {"events": 3000}}  # 30%
            }
        }

        result = await analyzer.analyze(mock_client)

        assert result.success is True
        # 1 out of 3 outputs has issues = 66.67% healthy
        assert result.metadata["backpressure_health_score"] <= 70
        assert result.metadata["backpressure_health_score"] >= 60
