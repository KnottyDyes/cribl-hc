"""
Test helper utilities for creating valid model instances.
"""

from datetime import datetime
from cribl_hc.models.finding import Finding
from cribl_hc.models.recommendation import Recommendation, ImpactEstimate
from cribl_hc.models.analysis import AnalysisRun


def create_test_finding(
    id: str = "test-finding-1",
    title: str = "Test Finding",
    description: str = "Test finding description",
    severity: str = "low",
    category: str = "health",
    confidence_level: str = "medium",
    **kwargs
) -> Finding:
    """
    Create a valid Finding for testing.

    Automatically adds required fields based on severity.
    """
    finding_data = {
        "id": id,
        "title": title,
        "description": description,
        "severity": severity,
        "category": category,
        "confidence_level": confidence_level,
    }

    # Add remediation_steps for critical/high/medium severity
    if severity in ["critical", "high", "medium"]:
        finding_data["remediation_steps"] = kwargs.get(
            "remediation_steps", [f"Fix {severity} severity issue"]
        )

    # Add estimated_impact for critical/high severity
    if severity in ["critical", "high"]:
        finding_data["estimated_impact"] = kwargs.get(
            "estimated_impact", f"{severity.capitalize()} impact on system"
        )

    # Allow overrides
    finding_data.update(kwargs)

    return Finding(**finding_data)


def create_test_recommendation(
    id: str = "test-rec-1",
    title: str = "Test Recommendation",
    description: str = "Test recommendation description",
    priority: str = "p2",
    rec_type: str = "optimization",
    **kwargs
) -> Recommendation:
    """
    Create a valid Recommendation for testing.

    Automatically adds required fields.
    """
    rec_data = {
        "id": id,
        "type": rec_type,
        "title": title,
        "description": description,
        "priority": priority,
        "rationale": kwargs.get("rationale", "Test rationale"),
        "implementation_steps": kwargs.get(
            "implementation_steps", ["Step 1: Implement change"]
        ),
        "implementation_effort": kwargs.get("implementation_effort", "low"),
    }

    # Add impact_estimate (required)
    if "impact_estimate" not in kwargs:
        # For p0/p1, need at least one metric
        if priority in ["p0", "p1"]:
            rec_data["impact_estimate"] = ImpactEstimate(cost_savings_annual=1000.0)
        else:
            rec_data["impact_estimate"] = ImpactEstimate()
    else:
        rec_data["impact_estimate"] = kwargs["impact_estimate"]

    # Allow overrides
    for key, value in kwargs.items():
        if key not in ["implementation_steps", "rationale", "implementation_effort", "impact_estimate"]:
            rec_data[key] = value

    return Recommendation(**rec_data)


def create_test_analysis_run(
    deployment_id: str = "test-deployment",
    objectives_analyzed: list = None,
    status: str = "completed",
    **kwargs
) -> AnalysisRun:
    """
    Create a valid AnalysisRun for testing.

    Automatically adds required fields.
    """
    if objectives_analyzed is None:
        objectives_analyzed = ["health"]

    run_data = {
        "deployment_id": deployment_id,
        "objectives_analyzed": objectives_analyzed,
        "status": status,
        "findings": kwargs.get("findings", []),
        "recommendations": kwargs.get("recommendations", []),
        "api_calls_used": kwargs.get("api_calls_used", 0),
    }

    # Add optional fields if provided
    if "start_time" in kwargs:
        run_data["start_time"] = kwargs["start_time"]
    if "end_time" in kwargs or "completed_at" in kwargs:
        run_data["completed_at"] = kwargs.get("completed_at", kwargs.get("end_time"))
    if "duration_seconds" in kwargs:
        run_data["duration_seconds"] = kwargs["duration_seconds"]

    # Allow other overrides
    for key, value in kwargs.items():
        if key not in ["findings", "recommendations", "api_calls_used", "start_time", "end_time", "completed_at", "duration_seconds"]:
            run_data[key] = value

    return AnalysisRun(**run_data)
