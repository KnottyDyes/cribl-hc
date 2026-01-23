from collections import OrderedDict, defaultdict
from typing import List

from cribl_hc.models.analysis import (
    CategorySummary,
    ComplianceStatus,
    ExecutiveSummary,
    RiskScore,
)
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation


def calculate_risk_score(findings: List[Finding]) -> RiskScore:
    if not findings:
        return RiskScore(score=0, status="healthy", label="Healthy")

    severity_weights = {
        "critical": 40,
        "high": 20,
        "medium": 5,
        "low": 1,
        "info": 0,
    }

    total_score = sum(severity_weights.get(f.severity, 0) for f in findings)
    normalized_score = min(100, total_score)

    if normalized_score >= 80:
        status = "critical"
        label = "Critical Risk"
    elif normalized_score >= 40:
        status = "warning"
        label = "Moderate Risk"
    else:
        status = "healthy"
        label = "Low Risk"

    return RiskScore(score=normalized_score, status=status, label=label)


def extract_compliance_status(findings: List[Finding]) -> List[ComplianceStatus]:
    compliance_frameworks = {}

    for finding in findings:
        framework = finding.metadata.get("compliance_framework")
        if framework:
            if framework not in compliance_frameworks:
                compliance_frameworks[framework] = {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "total": 0,
                }

            compliance_frameworks[framework]["total"] += 1
            if finding.severity == "critical":
                compliance_frameworks[framework]["critical"] += 1
            elif finding.severity == "high":
                compliance_frameworks[framework]["high"] += 1
            elif finding.severity == "medium":
                compliance_frameworks[framework]["medium"] += 1

    result = []
    for framework, counts in compliance_frameworks.items():
        if counts["critical"] > 0:
            status = "non_compliant"
        elif counts["high"] > 0 or counts["medium"] > 2:
            status = "at_risk"
        else:
            status = "compliant"

        result.append(
            ComplianceStatus(
                framework=framework,
                status=status,
                critical_violations=counts["critical"],
                total_violations=counts["total"],
            )
        )

    return result


def get_category_breakdown(findings: List[Finding]) -> List[CategorySummary]:
    category_counts = defaultdict(
        lambda: {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
            "total": 0,
        }
    )

    for finding in findings:
        category_counts[finding.category][finding.severity] += 1
        category_counts[finding.category]["total"] += 1

    result = []
    for category, counts in sorted(category_counts.items()):
        result.append(
            CategorySummary(
                category=category,
                critical_count=counts["critical"],
                high_count=counts["high"],
                medium_count=counts["medium"],
                low_count=counts["low"],
                info_count=counts["info"],
                total_count=counts["total"],
            )
        )

    return result


def identify_top_risks(findings: List[Finding], limit: int = 5) -> List[str]:
    critical_and_high = [f for f in findings if f.severity in ["critical", "high"]]

    critical_and_high.sort(key=lambda f: (0 if f.severity == "critical" else 1, f.category))

    top_risks = []
    seen_categories = set()

    for finding in critical_and_high:
        if finding.category not in seen_categories:
            top_risks.append(f"{finding.category}: {finding.title}")
            seen_categories.add(finding.category)

            if len(top_risks) >= limit:
                break

    return top_risks


def generate_executive_summary(
    findings: List[Finding],
    recommendations: List[Recommendation],
) -> ExecutiveSummary:
    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
    }

    for finding in findings:
        severity_counts[finding.severity] += 1

    return ExecutiveSummary(
        overall_risk=calculate_risk_score(findings),
        total_findings=len(findings),
        critical_count=severity_counts["critical"],
        high_count=severity_counts["high"],
        medium_count=severity_counts["medium"],
        low_count=severity_counts["low"],
        info_count=severity_counts["info"],
        compliance_status=extract_compliance_status(findings),
        category_breakdown=get_category_breakdown(findings),
        top_risks=identify_top_risks(findings),
        recommendations_count=len(recommendations),
    )
