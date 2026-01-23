"""
Unit tests for executive summary generation.
"""

from datetime import datetime

from cribl_hc.core.executive_summary import (
    calculate_risk_score,
    extract_compliance_status,
    get_category_breakdown,
    identify_top_risks,
    generate_executive_summary,
)
from cribl_hc.models.analysis import (
    CategorySummary,
    ComplianceStatus,
    ExecutiveSummary,
    RiskScore,
)
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate


def create_finding(
    id: str,
    category: str,
    severity: str,
    title: str,
    description: str,
    confidence_level: str = "high",
    metadata: dict | None = None,
) -> Finding:
    """Helper function to create Finding instances with required fields."""
    kwargs = {
        "id": id,
        "category": category,
        "severity": severity,
        "title": title,
        "description": description,
        "confidence_level": confidence_level,
        "metadata": metadata or {},
    }

    # Add required fields for critical, high, and medium severity
    if severity in ["critical", "high", "medium"]:
        kwargs["remediation_steps"] = [f"Fix {severity} {category} issue"]

    if severity in ["critical", "high"]:
        kwargs["estimated_impact"] = f"{severity.title()} impact on {category}"

    return Finding(**kwargs)


class TestCalculateRiskScore:
    """Test risk score calculation."""

    def test_empty_findings_returns_healthy(self):
        """Test that empty findings list returns healthy score."""
        result = calculate_risk_score([])

        assert result.score == 0
        assert result.status == "healthy"
        assert result.label == "Healthy"

    def test_critical_findings_high_score(self):
        """Test that critical findings result in high risk score."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="critical",
                title="Critical Security Issue",
                description="A critical security vulnerability",
            ),
            create_finding(
                id="f2",
                category="performance",
                severity="critical",
                title="Critical Performance Issue",
                description="A critical performance problem",
            ),
        ]

        result = calculate_risk_score(findings)

        assert result.score == 80  # 2 * 40 = 80
        assert result.status == "critical"
        assert result.label == "Critical Risk"

    def test_high_findings_moderate_score(self):
        """Test that high severity findings result in moderate risk score."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="high",
                title="High Security Issue",
                description="A high security vulnerability",
            ),
            create_finding(
                id="f2",
                category="performance",
                severity="high",
                title="High Performance Issue",
                description="A high performance problem",
            ),
        ]

        result = calculate_risk_score(findings)

        assert result.score == 40  # 2 * 20 = 40
        assert result.status == "warning"
        assert result.label == "Moderate Risk"

    def test_mixed_severity_findings(self):
        """Test risk score calculation with mixed severity findings."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="critical",
                title="Critical Issue",
                description="Critical problem",
            ),
            create_finding(
                id="f2",
                category="performance",
                severity="high",
                title="High Issue",
                description="High problem",
            ),
            create_finding(
                id="f3",
                category="config",
                severity="medium",
                title="Medium Issue",
                description="Medium problem",
                confidence_level="medium",
            ),
            create_finding(
                id="f4",
                category="info",
                severity="low",
                title="Low Issue",
                description="Low problem",
                confidence_level="low",
            ),
        ]

        result = calculate_risk_score(findings)

        # 40 (critical) + 20 (high) + 5 (medium) + 1 (low) = 66
        assert result.score == 66
        assert result.status == "warning"
        assert result.label == "Moderate Risk"

    def test_low_severity_findings(self):
        """Test that low severity findings result in low risk score."""
        findings = [
            create_finding(
                id="f1",
                category="info",
                severity="low",
                title="Low Issue",
                description="Low problem",
                confidence_level="low",
            ),
            create_finding(
                id="f2",
                category="config",
                severity="medium",
                title="Medium Issue",
                description="Medium problem",
                confidence_level="medium",
            ),
        ]

        result = calculate_risk_score(findings)

        assert result.score == 6  # 1 (low) + 5 (medium) = 6
        assert result.status == "healthy"
        assert result.label == "Low Risk"

    def test_score_capped_at_100(self):
        """Test that risk score is capped at 100."""
        findings = [
            create_finding(
                id=f"f{i}",
                category="security",
                severity="critical",
                title=f"Critical Issue {i}",
                description=f"Critical problem {i}",
            )
            for i in range(10)  # 10 critical findings = 400 points
        ]

        result = calculate_risk_score(findings)

        assert result.score == 100  # Capped at 100
        assert result.status == "critical"
        assert result.label == "Critical Risk"

    def test_info_severity_zero_weight(self):
        """Test that info severity findings have zero weight."""
        findings = [
            create_finding(
                id="f1",
                category="info",
                severity="info",
                title="Info Issue",
                description="Informational finding",
            ),
        ]

        result = calculate_risk_score(findings)

        assert result.score == 0
        assert result.status == "healthy"
        assert result.label == "Low Risk"


class TestExtractComplianceStatus:
    """Test compliance status extraction."""

    def test_empty_findings_returns_empty_list(self):
        """Test that empty findings list returns empty compliance status."""
        result = extract_compliance_status([])

        assert result == []

    def test_findings_without_compliance_framework(self):
        """Test findings without compliance framework metadata."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="critical",
                title="Security Issue",
                description="A security problem",
            ),
        ]

        result = extract_compliance_status(findings)

        assert result == []

    def test_critical_violations_non_compliant(self):
        """Test that critical violations result in non-compliant status."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="critical",
                title="HIPAA Violation",
                description="Critical HIPAA violation",
                metadata={"compliance_framework": "HIPAA"},
            ),
        ]

        result = extract_compliance_status(findings)

        assert len(result) == 1
        assert result[0].framework == "HIPAA"
        assert result[0].status == "non_compliant"
        assert result[0].critical_violations == 1
        assert result[0].total_violations == 1

    def test_high_violations_at_risk(self):
        """Test that high violations result in at-risk status."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="high",
                title="SOC2 Issue",
                description="High SOC2 issue",
                metadata={"compliance_framework": "SOC2"},
            ),
        ]

        result = extract_compliance_status(findings)

        assert len(result) == 1
        assert result[0].framework == "SOC2"
        assert result[0].status == "at_risk"
        assert result[0].critical_violations == 0
        assert result[0].total_violations == 1

    def test_multiple_medium_violations_at_risk(self):
        """Test that multiple medium violations result in at-risk status."""
        findings = [
            create_finding(
                id=f"f{i}",
                category="security",
                severity="medium",
                title=f"GDPR Issue {i}",
                description=f"Medium GDPR issue {i}",
                confidence_level="medium",
                metadata={"compliance_framework": "GDPR"},
            )
            for i in range(3)  # 3 medium violations
        ]

        result = extract_compliance_status(findings)

        assert len(result) == 1
        assert result[0].framework == "GDPR"
        assert result[0].status == "at_risk"
        assert result[0].critical_violations == 0
        assert result[0].total_violations == 3

    def test_few_medium_violations_compliant(self):
        """Test that few medium violations result in compliant status."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="medium",
                title="PCI DSS Issue",
                description="Medium PCI DSS issue",
                confidence_level="medium",
                metadata={"compliance_framework": "PCI DSS"},
            ),
        ]

        result = extract_compliance_status(findings)

        assert len(result) == 1
        assert result[0].framework == "PCI DSS"
        assert result[0].status == "compliant"
        assert result[0].critical_violations == 0
        assert result[0].total_violations == 1

    def test_multiple_frameworks(self):
        """Test compliance status for multiple frameworks."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="critical",
                title="HIPAA Critical",
                description="Critical HIPAA violation",
                metadata={"compliance_framework": "HIPAA"},
            ),
            create_finding(
                id="f2",
                category="security",
                severity="high",
                title="SOC2 High",
                description="High SOC2 issue",
                metadata={"compliance_framework": "SOC2"},
            ),
            create_finding(
                id="f3",
                category="security",
                severity="medium",
                title="GDPR Medium",
                description="Medium GDPR issue",
                confidence_level="medium",
                metadata={"compliance_framework": "GDPR"},
            ),
        ]

        result = extract_compliance_status(findings)

        assert len(result) == 3

        # Find each framework in results
        hipaa = next(r for r in result if r.framework == "HIPAA")
        soc2 = next(r for r in result if r.framework == "SOC2")
        gdpr = next(r for r in result if r.framework == "GDPR")

        assert hipaa.status == "non_compliant"
        assert hipaa.critical_violations == 1

        assert soc2.status == "at_risk"
        assert soc2.critical_violations == 0

        assert gdpr.status == "compliant"
        assert gdpr.critical_violations == 0


class TestGetCategoryBreakdown:
    """Test category breakdown generation."""

    def test_empty_findings_returns_empty_list(self):
        """Test that empty findings list returns empty category breakdown."""
        result = get_category_breakdown([])

        assert result == []

    def test_single_category_breakdown(self):
        """Test category breakdown for single category."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="critical",
                title="Critical Security Issue",
                description="Critical security problem",
            ),
            create_finding(
                id="f2",
                category="security",
                severity="high",
                title="High Security Issue",
                description="High security problem",
            ),
            create_finding(
                id="f3",
                category="security",
                severity="medium",
                title="Medium Security Issue",
                description="Medium security problem",
                confidence_level="medium",
            ),
        ]

        result = get_category_breakdown(findings)

        assert len(result) == 1
        assert result[0].category == "security"
        assert result[0].critical_count == 1
        assert result[0].high_count == 1
        assert result[0].medium_count == 1
        assert result[0].low_count == 0
        assert result[0].info_count == 0
        assert result[0].total_count == 3

    def test_multiple_categories_breakdown(self):
        """Test category breakdown for multiple categories."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="critical",
                title="Critical Security Issue",
                description="Critical security problem",
            ),
            create_finding(
                id="f2",
                category="performance",
                severity="high",
                title="High Performance Issue",
                description="High performance problem",
            ),
            create_finding(
                id="f3",
                category="config",
                severity="medium",
                title="Medium Config Issue",
                description="Medium config problem",
                confidence_level="medium",
            ),
            create_finding(
                id="f4",
                category="security",
                severity="low",
                title="Low Security Issue",
                description="Low security problem",
                confidence_level="low",
            ),
        ]

        result = get_category_breakdown(findings)

        # Results should be sorted by category name
        assert len(result) == 3

        # Find each category in results
        config = next(r for r in result if r.category == "config")
        performance = next(r for r in result if r.category == "performance")
        security = next(r for r in result if r.category == "security")

        assert config.medium_count == 1
        assert config.total_count == 1

        assert performance.high_count == 1
        assert performance.total_count == 1

        assert security.critical_count == 1
        assert security.low_count == 1
        assert security.total_count == 2

    def test_all_severity_levels(self):
        """Test category breakdown with all severity levels."""
        findings = [
            create_finding(
                id="f1",
                category="test",
                severity="critical",
                title="Critical Issue",
                description="Critical problem",
            ),
            create_finding(
                id="f2",
                category="test",
                severity="high",
                title="High Issue",
                description="High problem",
            ),
            create_finding(
                id="f3",
                category="test",
                severity="medium",
                title="Medium Issue",
                description="Medium problem",
                confidence_level="medium",
            ),
            create_finding(
                id="f4",
                category="test",
                severity="low",
                title="Low Issue",
                description="Low problem",
                confidence_level="low",
            ),
            create_finding(
                id="f5",
                category="test",
                severity="info",
                title="Info Issue",
                description="Info problem",
            ),
        ]

        result = get_category_breakdown(findings)

        assert len(result) == 1
        assert result[0].category == "test"
        assert result[0].critical_count == 1
        assert result[0].high_count == 1
        assert result[0].medium_count == 1
        assert result[0].low_count == 1
        assert result[0].info_count == 1
        assert result[0].total_count == 5


class TestIdentifyTopRisks:
    """Test top risks identification."""

    def test_empty_findings_returns_empty_list(self):
        """Test that empty findings list returns empty top risks."""
        result = identify_top_risks([])

        assert result == []

    def test_only_low_severity_returns_empty(self):
        """Test that only low/medium severity findings return empty top risks."""
        findings = [
            create_finding(
                id="f1",
                category="config",
                severity="medium",
                title="Medium Config Issue",
                description="Medium config problem",
                confidence_level="medium",
            ),
            create_finding(
                id="f2",
                category="performance",
                severity="low",
                title="Low Performance Issue",
                description="Low performance problem",
                confidence_level="low",
            ),
        ]

        result = identify_top_risks(findings)

        assert result == []

    def test_critical_and_high_findings(self):
        """Test top risks identification with critical and high findings."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="critical",
                title="Critical Security Issue",
                description="Critical security problem",
            ),
            create_finding(
                id="f2",
                category="performance",
                severity="high",
                title="High Performance Issue",
                description="High performance problem",
            ),
            create_finding(
                id="f3",
                category="config",
                severity="critical",
                title="Critical Config Issue",
                description="Critical config problem",
            ),
        ]

        result = identify_top_risks(findings)

        assert len(result) == 3
        # Critical findings should come first, then high
        assert "security: Critical Security Issue" in result
        assert "config: Critical Config Issue" in result
        assert "performance: High Performance Issue" in result

    def test_limit_top_risks(self):
        """Test that top risks are limited to specified number."""
        findings = [
            create_finding(
                id=f"f{i}",
                category=f"category{i}",
                severity="critical",
                title=f"Critical Issue {i}",
                description=f"Critical problem {i}",
            )
            for i in range(10)
        ]

        result = identify_top_risks(findings, limit=3)

        assert len(result) == 3

    def test_deduplicate_by_category(self):
        """Test that only one risk per category is included."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="critical",
                title="First Security Issue",
                description="First security problem",
            ),
            create_finding(
                id="f2",
                category="security",
                severity="critical",
                title="Second Security Issue",
                description="Second security problem",
            ),
            create_finding(
                id="f3",
                category="performance",
                severity="high",
                title="Performance Issue",
                description="Performance problem",
            ),
        ]

        result = identify_top_risks(findings)

        assert len(result) == 2
        # Should only include first security issue (by category deduplication)
        assert "security: First Security Issue" in result
        assert "performance: Performance Issue" in result
        assert "security: Second Security Issue" not in result

    def test_critical_before_high_priority(self):
        """Test that critical findings are prioritized over high findings."""
        findings = [
            create_finding(
                id="f1",
                category="performance",
                severity="high",
                title="High Performance Issue",
                description="High performance problem",
            ),
            create_finding(
                id="f2",
                category="security",
                severity="critical",
                title="Critical Security Issue",
                description="Critical security problem",
            ),
        ]

        result = identify_top_risks(findings)

        assert len(result) == 2
        # Critical should come first
        assert result[0] == "security: Critical Security Issue"
        assert result[1] == "performance: High Performance Issue"


class TestGenerateExecutiveSummary:
    """Test executive summary generation."""

    def test_empty_findings_and_recommendations(self):
        """Test executive summary with empty findings and recommendations."""
        result = generate_executive_summary([], [])

        assert isinstance(result, ExecutiveSummary)
        assert result.overall_risk.score == 0
        assert result.overall_risk.status == "healthy"
        assert result.total_findings == 0
        assert result.critical_count == 0
        assert result.high_count == 0
        assert result.medium_count == 0
        assert result.low_count == 0
        assert result.info_count == 0
        assert result.compliance_status == []
        assert result.category_breakdown == []
        assert result.top_risks == []
        assert result.recommendations_count == 0

    def test_complete_executive_summary(self):
        """Test executive summary with complete data."""
        findings = [
            create_finding(
                id="f1",
                category="security",
                severity="critical",
                title="Critical Security Issue",
                description="Critical security problem",
                metadata={"compliance_framework": "HIPAA"},
            ),
            create_finding(
                id="f2",
                category="performance",
                severity="high",
                title="High Performance Issue",
                description="High performance problem",
            ),
            create_finding(
                id="f3",
                category="config",
                severity="medium",
                title="Medium Config Issue",
                description="Medium config problem",
                confidence_level="medium",
            ),
            create_finding(
                id="f4",
                category="info",
                severity="low",
                title="Low Info Issue",
                description="Low info problem",
                confidence_level="low",
            ),
            create_finding(
                id="f5",
                category="monitoring",
                severity="info",
                title="Info Monitoring Issue",
                description="Info monitoring problem",
            ),
        ]

        recommendations = [
            Recommendation(
                id="r1",
                type="security",
                priority="p0",
                title="Fix Security Issue",
                description="Fix the critical security issue",
                rationale="Security is important",
                implementation_steps=["Step 1", "Step 2"],
                impact_estimate=ImpactEstimate(
                    cost_savings_annual=1000.0,
                    performance_improvement="Improved security",
                    storage_reduction_gb=0.0,
                    time_to_implement="2 hours",
                ),
                implementation_effort="high",
            ),
            Recommendation(
                id="r2",
                type="performance",
                priority="p1",
                title="Optimize Performance",
                description="Optimize the performance issue",
                rationale="Performance is important",
                implementation_steps=["Step 1"],
                impact_estimate=ImpactEstimate(
                    cost_savings_annual=500.0,
                    performance_improvement="20% faster",
                    storage_reduction_gb=10.0,
                    time_to_implement="1 hour",
                ),
                implementation_effort="medium",
            ),
        ]

        result = generate_executive_summary(findings, recommendations)

        # Check basic counts
        assert result.total_findings == 5
        assert result.critical_count == 1
        assert result.high_count == 1
        assert result.medium_count == 1
        assert result.low_count == 1
        assert result.info_count == 1
        assert result.recommendations_count == 2

        # Check overall risk
        assert result.overall_risk.score > 0
        assert result.overall_risk.status in ["healthy", "warning", "critical"]

        # Check compliance status
        assert len(result.compliance_status) == 1
        assert result.compliance_status[0].framework == "HIPAA"
        assert result.compliance_status[0].status == "non_compliant"

        # Check category breakdown
        assert len(result.category_breakdown) == 5
        categories = {cb.category for cb in result.category_breakdown}
        assert categories == {"security", "performance", "config", "info", "monitoring"}

        # Check top risks
        assert len(result.top_risks) == 2  # Only critical and high
        assert "security: Critical Security Issue" in result.top_risks
        assert "performance: High Performance Issue" in result.top_risks

    def test_severity_counts_accuracy(self):
        """Test that severity counts are accurate."""
        findings = [
            # 2 critical
            create_finding(
                id="f1",
                category="security",
                severity="critical",
                title="Critical 1",
                description="Critical problem 1",
            ),
            create_finding(
                id="f2",
                category="performance",
                severity="critical",
                title="Critical 2",
                description="Critical problem 2",
            ),
            # 3 high
            create_finding(
                id="f3",
                category="config",
                severity="high",
                title="High 1",
                description="High problem 1",
            ),
            create_finding(
                id="f4",
                category="storage",
                severity="high",
                title="High 2",
                description="High problem 2",
            ),
            create_finding(
                id="f5",
                category="network",
                severity="high",
                title="High 3",
                description="High problem 3",
            ),
            # 1 medium
            create_finding(
                id="f6",
                category="monitoring",
                severity="medium",
                title="Medium 1",
                description="Medium problem 1",
                confidence_level="medium",
            ),
        ]

        result = generate_executive_summary(findings, [])

        assert result.total_findings == 6
        assert result.critical_count == 2
        assert result.high_count == 3
        assert result.medium_count == 1
        assert result.low_count == 0
        assert result.info_count == 0
