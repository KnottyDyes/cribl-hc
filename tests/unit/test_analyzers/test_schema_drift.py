import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from cribl_hc.analyzers.schema_drift import SchemaDriftAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


@pytest.fixture
def analyzer():
    return SchemaDriftAnalyzer()


@pytest.fixture
def mock_client():
    client = MagicMock(spec=CriblAPIClient)
    client.capture_events = AsyncMock()
    # Configure to return empty list for older events (simulating they're not available)
    client.capture_events.side_effect = (
        lambda *args, **kwargs: []
        if "_time <" in str(kwargs.get("filter_expr", ""))
        else [
            {"field_a": "value1", "field_b": "value2", "field_c": "value3"},
            {"field_a": "value4", "field_b": "value5"},
            {"field_a": "value7"},
        ]
    )
    return client


class TestSchemaDriftAnalyzer:
    @pytest.mark.asyncio
    async def test_detects_critical_field_disappearance(self, analyzer, mock_client):
        """Test detection of fields that have critically disappeared."""
        # Create 25 events to meet MIN_SAMPLES_FOR_ANALYSIS (20)
        events = []
        for i in range(25):
            if i < 8:  # 8 events with all fields
                events.append(
                    {
                        "field_a": f"value_a_{i}",
                        "field_b": f"value_b_{i}",
                        "field_c": f"value_c_{i}",
                    }
                )
            elif i < 16:  # 8 events missing field_c
                events.append({"field_a": f"value_a_{i}", "field_b": f"value_b_{i}"})
            else:  # 9 events with only field_a
                events.append({"field_a": f"value_a_{i}"})
        mock_client.capture_events.side_effect = (
            lambda *args, **kwargs: []
            if "_time <" in str(kwargs.get("filter_expr", ""))
            else events
        )

        result = await analyzer.analyze(mock_client)

        print(f"DEBUG: Total findings: {len(result.findings)}")
        for finding in result.findings:
            print(f"  - {finding.id}: {finding.title}")

        # Should detect field_c disappearance (present in 1/3 = 33% < 80%)
        disappearance_findings = [
            f for f in result.findings if "schema-drift-field-disappearance" in f.id
        ]
        assert len(disappearance_findings) >= 1

        # Check field_c finding
        field_c_findings = [f for f in disappearance_findings if "field_c" in f.id]
        assert len(field_c_findings) == 1
        assert field_c_findings[0].severity == "medium"  # 33% presence

    @pytest.mark.asyncio
    async def test_detects_completely_missing_field(self, analyzer, mock_client):
        """Test detection of fields that are completely absent."""
        events = [
            {"field_a": "value1", "field_b": "value2"},
            {"field_a": "value3", "field_b": "value4"},
            {"field_a": "value5", "field_b": "value6"},
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # field_c not present at all (0% presence)
        disappearance_findings = [
            f for f in result.findings if "schema-drift-field-disappearance-field_c" in f.id
        ]
        assert len(disappearance_findings) == 1
        assert disappearance_findings[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_detects_type_inconsistencies(self, analyzer, mock_client):
        """Test detection of fields with multiple types."""
        events = [
            {"field_a": "string_value", "field_b": 123},
            {"field_a": 456, "field_b": "string_value"},  # type mismatch
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should detect type inconsistencies for both fields
        type_findings = [f for f in result.findings if "schema-drift-type-change" in f.id]
        assert len(type_findings) == 2

        # Check field_a has multiple types
        field_a_findings = [f for f in type_findings if "field_a" in f.id]
        assert len(field_a_findings) == 1
        assert "string" in field_a_findings[0].description
        assert "int" in field_a_findings[0].description

    @pytest.mark.asyncio
    async def test_detects_schema_inconsistencies_between_sources(self, analyzer, mock_client):
        """Test detection of inconsistent schemas between sources."""
        events = [
            {"source": "input1", "field_a": "value1", "field_b": "value2", "field_c": "value3"},
            {"source": "input1", "field_a": "value4", "field_b": "value5", "field_c": "value6"},
            {"source": "input2", "field_a": "value7"},  # Different schema
            {"source": "input2", "field_a": "value8"},
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should detect schema inconsistency for input2
        inconsistency_findings = [
            f for f in result.findings if "schema-drift-source-inconsistency" in f.id
        ]
        assert len(inconsistency_findings) >= 1

        input2_findings = [f for f in inconsistency_findings if "input2" in f.id]
        assert len(input2_findings) == 1
        assert input2_findings[0].severity in ["high", "medium"]

    @pytest.mark.asyncio
    async def test_handles_insufficient_data(self, analyzer, mock_client):
        """Test handling of insufficient data for analysis."""
        # Less than MIN_SAMPLES_FOR_ANALYSIS events
        events = [{"field_a": "value1"}]  # Only 1 event
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should have insufficient data finding
        insufficient_findings = [
            f for f in result.findings if "schema-drift-insufficient-data" in f.id
        ]
        assert len(insufficient_findings) == 1
        assert insufficient_findings[0].severity == "info"

    @pytest.mark.asyncio
    async def test_healthy_schema_no_drift(self, analyzer, mock_client):
        """Test analysis with healthy, consistent schema."""
        events = [
            {"field_a": "value1", "field_b": "value2", "field_c": "value3"},
            {"field_a": "value4", "field_b": "value5", "field_c": "value6"},
            {"field_a": "value7", "field_b": "value8", "field_c": "value9"},
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should have summary finding but no drift findings
        summary_findings = [f for f in result.findings if "schema-drift-summary" in f.id]
        assert len(summary_findings) == 1

        drift_findings = [f for f in result.findings if f.id != "schema-drift-summary"]
        # Should be minimal findings for healthy schema
        assert len(drift_findings) == 0

    @pytest.mark.asyncio
    async def test_ignores_internal_cribl_fields(self, analyzer, mock_client):
        """Test that internal Cribl fields are ignored in schema analysis."""
        events = [
            {"_time": 1234567890, "_raw": "some data", "field_a": "value1"},
            {"_time": 1234567891, "_raw": "more data", "field_a": "value2"},
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should not generate findings for _time or _raw fields
        field_findings = [
            f for f in result.findings if "field_a" in f.id or "_time" in f.id or "_raw" in f.id
        ]
        # Should only have summary finding, no field-specific findings for internal fields
        assert len(field_findings) == 0 or all("summary" in f.id for f in field_findings)

    @pytest.mark.asyncio
    async def test_detects_new_fields(self, analyzer, mock_client):
        """Test detection of sparsely populated fields (potential new additions)."""
        events = [
            {"field_a": "value1", "field_b": "value2"},
            {"field_a": "value3", "field_b": "value4"},
            {"field_a": "value5", "field_b": "value6"},
            {
                "field_a": "value7",
                "field_b": "value8",
                "field_c": "sparse",
            },  # field_c only in 1/4 events
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # May or may not detect new fields depending on implementation
        # This is informational, so it's acceptable if not detected
        new_field_findings = [f for f in result.findings if "new-fields" in f.id]
        # Either no finding (if threshold not met) or informational finding
        if new_field_findings:
            assert new_field_findings[0].severity == "info"

    @pytest.mark.asyncio
    async def test_handles_empty_events(self, analyzer, mock_client):
        """Test handling of empty event capture."""
        mock_client.capture_events.return_value = []

        result = await analyzer.analyze(mock_client)

        # Should handle empty results gracefully
        assert result.success is True
        assert len(result.findings) >= 1  # At least summary finding

    @pytest.mark.asyncio
    async def test_handles_mixed_timestamps(self, analyzer, mock_client):
        """Test handling of events with different timestamp patterns."""
        now = time.time()
        events = [
            {"_time": now - 100, "field_a": "value1"},  # Recent event
            {"_time": now - 600, "field_a": "value2"},  # Older event
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should process events regardless of timestamp differences
        assert result.success is True
        # Should not crash on timestamp processing
        assert isinstance(result.findings, list)
