#!/usr/bin/env python3
"""
Performance validation script for cribl-hc.

Validates that the tool meets performance targets:
- Analysis completes in < 5 minutes (300 seconds)
- Uses < 100 API calls per analysis
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cribl_hc.models.analysis import AnalysisRun


def validate_performance_targets(analysis_run: AnalysisRun) -> dict:
    """
    Validate that analysis run meets performance targets.

    Args:
        analysis_run: Completed analysis run

    Returns:
        Dictionary with validation results
    """
    results = {
        "passed": True,
        "checks": [],
    }

    # Target 1: Duration < 5 minutes (300 seconds)
    duration_target = 300.0
    duration_check = {
        "name": "Analysis Duration",
        "target": f"< {duration_target}s (5 minutes)",
        "actual": f"{analysis_run.duration_seconds:.2f}s",
        "passed": analysis_run.duration_seconds < duration_target,
        "margin": duration_target - analysis_run.duration_seconds,
    }
    results["checks"].append(duration_check)

    if not duration_check["passed"]:
        results["passed"] = False

    # Target 2: API calls < 100
    api_call_target = 100
    api_call_check = {
        "name": "API Call Budget",
        "target": f"< {api_call_target} calls",
        "actual": f"{analysis_run.api_calls_used} calls",
        "passed": analysis_run.api_calls_used < api_call_target,
        "margin": api_call_target - analysis_run.api_calls_used,
    }
    results["checks"].append(api_call_check)

    if not api_call_check["passed"]:
        results["passed"] = False

    # Performance efficiency metrics
    if analysis_run.duration_seconds > 0:
        calls_per_second = analysis_run.api_calls_used / analysis_run.duration_seconds
        efficiency_check = {
            "name": "API Call Efficiency",
            "target": "N/A",
            "actual": f"{calls_per_second:.2f} calls/second",
            "passed": True,  # Informational only
            "margin": None,
        }
        results["checks"].append(efficiency_check)

    return results


def print_performance_report(results: dict):
    """Print performance validation report."""
    print("\n" + "=" * 60)
    print("PERFORMANCE VALIDATION REPORT")
    print("=" * 60 + "\n")

    for check in results["checks"]:
        status = "✓ PASS" if check["passed"] else "✗ FAIL"
        print(f"{status}  {check['name']}")
        print(f"   Target:  {check['target']}")
        print(f"   Actual:  {check['actual']}")

        if check["margin"] is not None:
            if check["passed"]:
                print(f"   Margin:  {check['margin']:.2f} (under budget)")
            else:
                print(f"   Margin:  {abs(check['margin']):.2f} (over budget)")
        print()

    print("=" * 60)
    if results["passed"]:
        print("OVERALL: ✓ ALL PERFORMANCE TARGETS MET")
    else:
        print("OVERALL: ✗ PERFORMANCE TARGETS NOT MET")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import json

    # Example: Load from JSON report
    if len(sys.argv) > 1:
        report_file = Path(sys.argv[1])
        if report_file.exists():
            with open(report_file) as f:
                data = json.load(f)
                analysis_run = AnalysisRun(**data)

            results = validate_performance_targets(analysis_run)
            print_performance_report(results)

            sys.exit(0 if results["passed"] else 1)
        else:
            print(f"Error: File not found: {report_file}")
            sys.exit(1)
    else:
        print("Usage: python validate_performance.py <report.json>")
        print("\nExample:")
        print("  cribl-hc analyze run -u URL -t TOKEN --output report.json")
        print("  python scripts/validate_performance.py report.json")
        sys.exit(1)
