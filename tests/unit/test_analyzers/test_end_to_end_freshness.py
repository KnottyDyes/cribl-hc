import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from cribl_hc.analyzers.end_to_end_freshness import EndToEndFreshnessAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


@pytest.fixture
def analyzer():
    return EndToEndFreshnessAnalyzer()


@pytest.fixture
def mock_client():
    client = MagicMock(spec=CriblAPIClient)
    client.capture_events = AsyncMock()
    return client


class TestEndToEndFreshnessAnalyzer:
    @pytest.mark.asyncio
    async def test_detects_critical_latency(self, analyzer, mock_client):
        """Test detection of critically high end-to-end latency."""
        now = time.time()
        events = [
            {"_time": now, "input_time": now - 180},  # 3 minutes latency (Critical)
            {"_time": now, "input_time": now - 150},  # 2.5 minutes latency (Critical)
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        critical_findings = [f for f in result.findings if "e2e-freshness-critical-latency" in f.id]
        assert len(critical_findings) == 1
        assert critical_findings[0].severity == "critical"
        assert (
            "180" in critical_findings[0].description
            or "2 minutes" in critical_findings[0].description
        )

    @pytest.mark.asyncio
    async def test_detects_high_latency(self, analyzer, mock_client):
        """Test detection of high end-to-end latency."""
        now = time.time()
        events = [
            {"_time": now, "input_time": now - 45},  # 45 seconds latency (High)
            {"_time": now, "input_time": now - 40},  # 40 seconds latency (High)
            {"_time": now, "input_time": now - 10},  # 10 seconds latency (Fine)
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        high_findings = [f for f in result.findings if "e2e-freshness-high-latency" in f.id]
        assert len(high_findings) == 1
        assert high_findings[0].severity == "high"
        assert "45" in high_findings[0].description or "40" in high_findings[0].description

    @pytest.mark.asyncio
    async def test_detects_pipeline_bottlenecks(self, analyzer, mock_client):
        """Test detection of pipeline bottlenecks."""
        now = time.time()
        events = [
            # Fast pipeline
            {"_time": now, "input_time": now - 5, "cribl_pipe": "fast-pipeline"},
            {"_time": now, "input_time": now - 6, "cribl_pipe": "fast-pipeline"},
            # Slow pipeline (3x slower = bottleneck)
            {"_time": now, "input_time": now - 45, "cribl_pipe": "slow-pipeline"},
            {"_time": now, "input_time": now - 50, "cribl_pipe": "slow-pipeline"},
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        bottleneck_findings = [
            f for f in result.findings if "e2e-freshness-pipeline-bottleneck" in f.id
        ]
        assert len(bottleneck_findings) >= 1

        slow_findings = [f for f in bottleneck_findings if "slow-pipeline" in f.id]
        assert len(slow_findings) == 1
        assert slow_findings[0].severity in ["critical", "high"]

    @pytest.mark.asyncio
    async def test_handles_multiple_input_timestamp_fields(self, analyzer, mock_client):
        """Test handling of different input timestamp field names."""
        now = time.time()
        events = [
            {"_time": now, "input_time": now - 10},  # Standard field
            {"_time": now, "_input_time": now - 15},  # Alternative field
            {"_time": now, "ingest_time": now - 20},  # Another alternative
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should process all events without crashing
        assert result.success is True
        # Should have summary finding
        summary_findings = [f for f in result.findings if "e2e-freshness-summary" in f.id]
        assert len(summary_findings) == 1

    @pytest.mark.asyncio
    async def test_estimates_input_time_when_missing(self, analyzer, mock_client):
        """Test estimation of input time when explicit timestamp is missing."""
        now = time.time()
        events = [
            {"_time": now},  # No input_time - should estimate
            {"_time": now - 30},  # Older event - should estimate
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should handle missing input timestamps gracefully
        assert result.success is True
        # Should still generate summary
        summary_findings = [f for f in result.findings if "e2e-freshness-summary" in f.id]
        assert len(summary_findings) == 1

    @pytest.mark.asyncio
    async def test_healthy_end_to_end_freshness(self, analyzer, mock_client):
        """Test analysis with healthy end-to-end latency."""
        now = time.time()
        events = [
            {"_time": now, "input_time": now - 5},  # 5 seconds latency (Healthy)
            {"_time": now, "input_time": now - 8},  # 8 seconds latency (Healthy)
            {"_time": now, "input_time": now - 10},  # 10 seconds latency (Healthy)
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        summary_findings = [f for f in result.findings if "e2e-freshness-summary" in f.id]
        assert len(summary_findings) == 1

        summary = summary_findings[0]
        assert summary.severity == "info"  # Healthy
        assert "Excellent" in summary.title or "Good" in summary.title

    @pytest.mark.asyncio
    async def test_handles_insufficient_data(self, analyzer, mock_client):
        """Test handling of insufficient data for analysis."""
        # Less than MIN_SAMPLES_FOR_ANALYSIS events
        events = [{"_time": time.time(), "input_time": time.time() - 5}]  # Only 1 event
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        insufficient_findings = [
            f for f in result.findings if "e2e-freshness-insufficient-data" in f.id
        ]
        assert len(insufficient_findings) == 1
        assert insufficient_findings[0].severity == "info"

    @pytest.mark.asyncio
    async def test_handles_empty_events(self, analyzer, mock_client):
        """Test handling of empty event capture."""
        mock_client.capture_events.return_value = []

        result = await analyzer.analyze(mock_client)

        # Should handle empty results gracefully
        assert result.success is True
        # Should have summary or insufficient data finding
        assert len(result.findings) >= 1

    @pytest.mark.asyncio
    async def test_filters_unrealistic_latencies(self, analyzer, mock_client):
        """Test filtering of unrealistic latency values."""
        now = time.time()
        events = [
            {"_time": now, "input_time": now - 10},  # Normal latency
            {"_time": now, "input_time": now + 10},  # Negative latency (filtered)
            {"_time": now, "input_time": now - 7200},  # 2 hours latency (filtered)
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should only process the realistic latency event
        assert result.success is True
        metadata = result.metadata
        assert "events_with_timestamps" in metadata
        # Should have processed only 1 event with valid latency
        assert metadata["events_with_timestamps"] == 1

    @pytest.mark.asyncio
    async def test_calculates_latency_statistics(self, analyzer, mock_client):
        """Test calculation of latency statistics."""
        now = time.time()
        events = [
            {"_time": now, "input_time": now - 5},
            {"_time": now, "input_time": now - 10},
            {"_time": now, "input_time": now - 15},
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        metadata = result.metadata
        assert "avg_latency_seconds" in metadata
        assert "max_latency_seconds" in metadata
        assert "events_with_timestamps" in metadata

        # Check statistics are reasonable
        assert metadata["avg_latency_seconds"] == 10.0  # (5+10+15)/3
        assert metadata["max_latency_seconds"] == 15.0
        assert metadata["events_with_timestamps"] == 3

    @pytest.mark.asyncio
    async def test_handles_source_based_grouping(self, analyzer, mock_client):
        """Test latency analysis grouped by source."""
        now = time.time()
        events = [
            {"_time": now, "input_time": now - 5, "source": "input1"},
            {"_time": now, "input_time": now - 10, "source": "input1"},
            {"_time": now, "input_time": now - 20, "source": "input2"},  # Different source
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should process events from different sources
        assert result.success is True
        metadata = result.metadata
        assert metadata["events_with_timestamps"] == 3

        # Check that source latencies are tracked
        assert "source_latencies" in result.metadata
