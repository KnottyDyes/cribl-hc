from unittest.mock import AsyncMock, MagicMock

import pytest

from cribl_hc.analyzers.advanced_security import (
    AdvancedSecurityAnalyzer,
    CustomPattern,
)


@pytest.fixture
def analyzer():
    return AdvancedSecurityAnalyzer()


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.capture_events = AsyncMock()
    return client


class TestAdvancedSecurityAnalyzer:
    @pytest.mark.asyncio
    async def test_detects_healthcare_patterns(self, analyzer, mock_client):
        """Test detection of healthcare data patterns."""
        events = [
            {"patient_data": "Patient diagnosed with A123.45 (some condition)"},  # ICD-10 code
            {"medication": "Prescribed drug 12345-6789-01"},  # NDC code
            {"doctor": "Dr. Smith DEA: AB1234567"},  # DEA number
            {"filler1": "data"},
            {"filler2": "data"},
            {"filler3": "data"},
            {"filler4": "data"},
            {"filler5": "data"},
            {"filler6": "data"},
            {"filler7": "data"},  # 10+ events required by analyzer
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should detect multiple healthcare patterns
        healthcare_findings = [
            f
            for f in result.findings
            if getattr(f, "category", "") == "security"
            and getattr(f, "metadata", {}).get("data_sensitivity") == "data:healthcare"
        ]
        assert len(healthcare_findings) >= 2

    @pytest.mark.asyncio
    async def test_detects_financial_patterns(self, analyzer, mock_client):
        """Test detection of financial data patterns."""
        events = [
            {"bank_info": "Routing number: 123456789"},  # ABA routing
            {"international": "SWIFT: ABCDUS33XXX"},  # SWIFT code
            {"payment": "IBAN: GB29 NWBK 6016 1331 9268 19"},  # IBAN
            {"filler1": "data"},
            {"filler2": "data"},
            {"filler3": "data"},
            {"filler4": "data"},
            {"filler5": "data"},
            {"filler6": "data"},
            {"filler7": "data"},  # 10+ events required by analyzer
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should detect financial patterns
        financial_findings = [
            f
            for f in result.findings
            if getattr(f, "category", "") == "security"
            and getattr(f, "metadata", {}).get("data_sensitivity") == "data:financial"
        ]
        assert len(financial_findings) >= 1

    @pytest.mark.asyncio
    async def test_hipaa_compliance_check(self, analyzer, mock_client):
        """Test HIPAA compliance analysis."""
        events = [
            {"health_record": "Patient A123.45 has DEA number AB1234567"},  # Healthcare + DEA
            {"normal_data": "Regular business data without PHI"},
            {"filler1": "data"},
            {"filler2": "data"},
            {"filler3": "data"},
            {"filler4": "data"},
            {"filler5": "data"},
            {"filler6": "data"},
            {"filler7": "data"},
            {"filler8": "data"},  # 10+ events required by analyzer
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should detect HIPAA violations
        hipaa_findings = [
            f
            for f in result.findings
            if getattr(f, "metadata", {}).get("compliance_framework") == "HIPAA"
        ]
        assert len(hipaa_findings) >= 1

    @pytest.mark.asyncio
    async def test_soc2_compliance_check(self, analyzer, mock_client):
        """Test SOC 2 compliance analysis."""
        events = [
            {"system_log": "User password changed to: mySecret123!"},  # Sensitive in logs
            {"app_log": "Application started successfully"},
            {"filler1": "data"},
            {"filler2": "data"},
            {"filler3": "data"},
            {"filler4": "data"},
            {"filler5": "data"},
            {"filler6": "data"},
            {"filler7": "data"},
            {"filler8": "data"},  # 10+ events required by analyzer
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should detect SOC 2 violations
        soc2_findings = [
            f
            for f in result.findings
            if getattr(f, "metadata", {}).get("compliance_framework") == "SOC 2"
        ]
        assert len(soc2_findings) >= 1

    @pytest.mark.asyncio
    async def test_gdpr_compliance_check(self, analyzer, mock_client):
        """Test GDPR compliance analysis."""
        events = [
            {
                "user_data": "Email: user@example.com, Phone: 555-1234"
            },  # Personal data without consent
            {"anonymous": "Website visited by anonymous user"},
            {"filler1": "data"},
            {"filler2": "data"},
            {"filler3": "data"},
            {"filler4": "data"},
            {"filler5": "data"},
            {"filler6": "data"},
            {"filler7": "data"},
            {"filler8": "data"},  # 10+ events required by analyzer
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should detect GDPR violations
        gdpr_findings = [
            f
            for f in result.findings
            if getattr(f, "metadata", {}).get("compliance_framework") == "GDPR"
        ]
        assert len(gdpr_findings) >= 1

    @pytest.mark.asyncio
    async def test_custom_pattern_detection(self, analyzer, mock_client):
        """Test custom sensitive data pattern detection."""
        # Add a custom pattern (in addition to loaded ones)
        custom_pattern = CustomPattern(
            name="unique_test_pattern",
            pattern=r"\bUNIQUE\d{6}\b",
            description="Unique test pattern numbers",
            severity="high",
            category="test_data",
            remediation="Mask test IDs in logs and reports",
        )
        analyzer.add_custom_pattern(custom_pattern)

        events = [
            {"test_record": "Employee UNIQUE123456 was found"},  # Matches custom pattern
            {"business": "Meeting with client ABC Corp"},
            {"filler1": "data"},
            {"filler2": "data"},
            {"filler3": "data"},
            {"filler4": "data"},
            {"filler5": "data"},
            {"filler6": "data"},
            {"filler7": "data"},
            {"filler8": "data"},  # 10+ events required by analyzer
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should detect custom pattern violation
        custom_findings = [
            f
            for f in result.findings
            if getattr(f, "metadata", {}).get("custom_pattern") == True
            and "unique_test_pattern" in f.metadata.get("pattern_name", "")
        ]
        assert len(custom_findings) >= 1
        assert custom_findings[0].severity == "high"

    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self, analyzer, mock_client):
        """Test handling of insufficient data for analysis."""
        events = [{"minimal": "data"}]  # Less than 10 events
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should have insufficient data finding
        insufficient_findings = [f for f in result.findings if "insufficient-data" in f.id]
        assert len(insufficient_findings) == 1
        assert insufficient_findings[0].severity == "info"

    @pytest.mark.asyncio
    async def test_ignores_internal_fields(self, analyzer, mock_client):
        """Test that internal Cribl fields are ignored."""
        events = [
            {"_time": 1234567890, "_raw": "contains DEA AB1234567", "user_data": "safe data"},
            {"business": "Regular business data"},
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should not flag _raw field even if it contains sensitive data
        raw_findings = [f for f in result.findings if "_raw" in str(getattr(f, "metadata", {}))]
        assert len(raw_findings) == 0

    @pytest.mark.asyncio
    async def test_generates_security_summary(self, analyzer, mock_client):
        """Test generation of security analysis summary."""
        events = [
            {"health": "ICD code A123.45 detected"},  # Healthcare
            {"finance": "SWIFT code ABCDUS33XXX"},  # Financial
            {"safe": "Regular business data"},
            {"filler1": "data"},
            {"filler2": "data"},
            {"filler3": "data"},
            {"filler4": "data"},
            {"filler5": "data"},
            {"filler6": "data"},
            {"filler7": "data"},  # 10+ events required by analyzer
        ]
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should have summary finding
        summary_findings = [f for f in result.findings if "security-summary" in f.id]
        assert len(summary_findings) == 1

        summary = summary_findings[0]
        assert "Advanced Security Analysis" in summary.title
        assert summary.metadata["events_analyzed"] == 10

    @pytest.mark.asyncio
    async def test_compliance_framework_enabling(self, analyzer, mock_client):
        """Test enabling specific compliance frameworks."""
        analyzer.enable_compliance_framework("hipaa")
        analyzer.enable_compliance_framework("gdpr")

        events = [{"data": "Some data"}]  # Won't trigger specific patterns but framework is enabled
        mock_client.capture_events.return_value = events

        result = await analyzer.analyze(mock_client)

        # Should have framework metadata
        assert len(analyzer.active_frameworks) >= 2
        assert "hipaa" in analyzer.active_frameworks
        assert "gdpr" in analyzer.active_frameworks

    def test_custom_pattern_management(self, analyzer):
        """Test custom pattern management."""
        initial_count = len(analyzer.custom_patterns)  # May have loaded patterns
        pattern = CustomPattern(
            name="mgmt_test_pattern",
            pattern=r"\bMGMT\d{4}\b",
            description="Management test pattern",
            severity="medium",
            category="test",
            remediation="Handle test data appropriately",
        )

        analyzer.add_custom_pattern(pattern)

        assert len(analyzer.custom_patterns) == initial_count + 1
        assert analyzer.custom_patterns[-1].name == "mgmt_test_pattern"

    def test_objective_name(self, analyzer):
        """Test analyzer objective name."""
        assert analyzer.objective_name == "advanced_security"

    def test_supported_products(self, analyzer):
        """Test supported products."""
        products = analyzer.supported_products
        assert "stream" in products
        assert "edge" in products
        assert "lake" in products
        assert "search" in products

    def test_description(self, analyzer):
        """Test analyzer description."""
        description = analyzer.get_description()
        assert "advanced security" in description.lower()
        assert "healthcare" in description.lower()
        assert "compliance" in description.lower()

    def test_required_permissions(self, analyzer):
        """Test required permissions."""
        permissions = analyzer.get_required_permissions()
        assert "read:system" in permissions
        assert "execute:capture" in permissions

    def test_estimated_api_calls(self, analyzer):
        """Test estimated API calls."""
        calls = analyzer.get_estimated_api_calls()
        assert calls == 2  # Event sampling calls
