#!/usr/bin/env python3
"""
Test ConfigAnalyzer against a real Cribl deployment.

This script connects to a real Cribl API and runs the ConfigAnalyzer
to test it against live data.

Usage:
    python scripts/test_real_deployment.py --url https://your-cribl.example.com --token YOUR_TOKEN

Example:
    python scripts/test_real_deployment.py \\
        --url https://cribl.mycompany.com \\
        --token eyJhbGc...your-token-here
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add src to path so we can import cribl_hc
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cribl_hc.analyzers.config import ConfigAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


def print_separator(char="=", length=80):
    """Print a separator line."""
    print(char * length)


def print_section(title):
    """Print a section header."""
    print_separator()
    print(f"  {title}")
    print_separator()


def print_findings_summary(findings):
    """Print a summary of findings by severity."""
    critical = [f for f in findings if f.severity == "critical"]
    high = [f for f in findings if f.severity == "high"]
    medium = [f for f in findings if f.severity == "medium"]
    low = [f for f in findings if f.severity == "low"]

    print(f"\nFindings Summary:")
    print(f"  Critical: {len(critical)}")
    print(f"  High:     {len(high)}")
    print(f"  Medium:   {len(medium)}")
    print(f"  Low:      {len(low)}")
    print(f"  Total:    {len(findings)}")


def print_finding_details(finding, index):
    """Print detailed information about a finding."""
    print(f"\n[{index + 1}] {finding.title}")
    print(f"    Severity: {finding.severity.upper()}")
    print(f"    Category: {finding.category}")
    print(f"    Affected: {', '.join(finding.affected_components)}")
    print(f"    Impact: {finding.estimated_impact}")
    if finding.remediation_steps:
        print(f"    Remediation:")
        for step in finding.remediation_steps[:3]:  # Show first 3 steps
            print(f"      - {step}")
        if len(finding.remediation_steps) > 3:
            print(f"      ... ({len(finding.remediation_steps) - 3} more steps)")


def print_recommendation_details(rec, index):
    """Print detailed information about a recommendation."""
    print(f"\n[{index + 1}] {rec.title}")
    print(f"    Priority: {rec.priority.upper()}")
    print(f"    Type: {rec.type}")
    print(f"    Description: {rec.description}")
    print(f"    Effort: {rec.implementation_effort}")
    if rec.impact_estimate:
        if rec.impact_estimate.time_to_implement:
            print(f"    Time to implement: {rec.impact_estimate.time_to_implement}")
        if rec.impact_estimate.performance_improvement:
            print(f"    Improvement: {rec.impact_estimate.performance_improvement}")


async def test_connection(url: str, token: str) -> bool:
    """Test connection to Cribl API."""
    print_section("Testing Connection")
    print(f"Connecting to: {url}")

    try:
        async with CriblAPIClient(base_url=url, auth_token=token) as client:
            result = await client.test_connection()

            if result.success:
                print(f"✓ Connection successful!")
                print(f"  Cribl Version: {result.cribl_version}")
                print(f"  Response Time: {result.response_time_ms:.0f}ms")
                return True
            else:
                print(f"✗ Connection failed: {result.message}")
                print(f"  Error: {result.error}")
                return False
    except Exception as e:
        print(f"✗ Connection error: {str(e)}")
        return False


async def run_config_analysis(url: str, token: str, verbose: bool = False):
    """Run ConfigAnalyzer against the real deployment."""
    print_section("Running Configuration Analysis")

    try:
        async with CriblAPIClient(base_url=url, auth_token=token) as client:
            analyzer = ConfigAnalyzer()

            print(f"Analyzer: {analyzer.objective_name}")
            print(f"Estimated API calls: {analyzer.get_estimated_api_calls()}")
            print(f"\nAnalyzing...")

            result = await analyzer.analyze(client)

            print_section("Analysis Results")

            # Print success status
            if result.success:
                print("✓ Analysis completed successfully")
            else:
                print("⚠ Analysis completed with issues")
                if result.error:
                    print(f"  Error: {result.error}")

            # Print metadata
            print(f"\nMetadata:")
            print(f"  Compliance Score: {result.metadata.get('compliance_score', 'N/A')}/100")
            print(f"  Pipelines Analyzed: {result.metadata.get('pipelines_analyzed', 0)}")
            print(f"  Routes Analyzed: {result.metadata.get('routes_analyzed', 0)}")
            print(f"  Inputs Analyzed: {result.metadata.get('inputs_analyzed', 0)}")
            print(f"  Outputs Analyzed: {result.metadata.get('outputs_analyzed', 0)}")

            # Print findings summary
            print_findings_summary(result.findings)

            # Print detailed findings
            if result.findings:
                print_section("Findings Details")

                # Group by severity
                critical = [f for f in result.findings if f.severity == "critical"]
                high = [f for f in result.findings if f.severity == "high"]
                medium = [f for f in result.findings if f.severity == "medium"]
                low = [f for f in result.findings if f.severity == "low"]

                if critical:
                    print("\nCRITICAL Findings:")
                    for i, finding in enumerate(critical):
                        print_finding_details(finding, i)

                if high:
                    print("\nHIGH Findings:")
                    for i, finding in enumerate(high):
                        print_finding_details(finding, i)

                if medium and verbose:
                    print("\nMEDIUM Findings:")
                    for i, finding in enumerate(medium):
                        print_finding_details(finding, i)

                if low and verbose:
                    print("\nLOW Findings:")
                    for i, finding in enumerate(low):
                        print_finding_details(finding, i)
            else:
                print("\n✓ No findings - configuration looks good!")

            # Print recommendations
            if result.recommendations:
                print_section("Recommendations")
                for i, rec in enumerate(result.recommendations):
                    print_recommendation_details(rec, i)

            # Print full JSON if verbose
            if verbose:
                print_section("Full Analysis Result (JSON)")
                result_dict = {
                    "objective": result.objective,
                    "success": result.success,
                    "metadata": result.metadata,
                    "findings_count": len(result.findings),
                    "recommendations_count": len(result.recommendations),
                    "findings": [
                        {
                            "id": f.id,
                            "severity": f.severity,
                            "title": f.title,
                            "description": f.description,
                            "affected_components": f.affected_components,
                        }
                        for f in result.findings
                    ],
                    "recommendations": [
                        {
                            "id": r.id,
                            "priority": r.priority,
                            "type": r.type,
                            "title": r.title,
                            "description": r.description,
                        }
                        for r in result.recommendations
                    ],
                }
                print(json.dumps(result_dict, indent=2))

            return result

    except Exception as e:
        print(f"\n✗ Analysis failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test ConfigAnalyzer against a real Cribl deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test against Cribl Cloud
  python scripts/test_real_deployment.py \\
    --url https://myorg.cribl.cloud \\
    --token eyJhbGc...

  # Test against self-hosted deployment with verbose output
  python scripts/test_real_deployment.py \\
    --url https://cribl.example.com \\
    --token YOUR_TOKEN \\
    --verbose

  # Skip connection test and go straight to analysis
  python scripts/test_real_deployment.py \\
    --url https://cribl.example.com \\
    --token YOUR_TOKEN \\
    --no-connection-test
        """,
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Cribl API base URL (e.g., https://cribl.example.com or https://myorg.cribl.cloud)",
    )
    parser.add_argument(
        "--token",
        required=True,
        help="Bearer token for API authentication",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output including all findings and full JSON",
    )
    parser.add_argument(
        "--no-connection-test",
        action="store_true",
        help="Skip connection test and go straight to analysis",
    )

    args = parser.parse_args()

    # Print header
    print_separator("=", 80)
    print("  ConfigAnalyzer Real Deployment Test")
    print_separator("=", 80)
    print(f"URL: {args.url}")
    print(f"Token: {args.token[:20]}..." if len(args.token) > 20 else f"Token: {args.token}")
    print()

    # Test connection first (unless skipped)
    if not args.no_connection_test:
        connection_ok = await test_connection(args.url, args.token)
        if not connection_ok:
            print("\n✗ Connection test failed. Please check your URL and token.")
            print("  Use --no-connection-test to skip this check and try analysis anyway.")
            return 1
        print()

    # Run analysis
    result = await run_config_analysis(args.url, args.token, verbose=args.verbose)

    if result is None:
        return 1

    # Print summary
    print_section("Summary")
    if result.success:
        compliance_score = result.metadata.get("compliance_score", 0)
        print(f"✓ Analysis completed successfully")
        print(f"  Compliance Score: {compliance_score}/100")

        if compliance_score == 100:
            print("\n  🎉 Perfect score! No issues found.")
        elif compliance_score >= 90:
            print("\n  ✓ Excellent! Minor improvements possible.")
        elif compliance_score >= 75:
            print("\n  ⚠ Good, but some issues should be addressed.")
        elif compliance_score >= 50:
            print("\n  ⚠ Multiple issues found. Review recommended.")
        else:
            print("\n  ⚠ Critical issues found. Immediate action recommended.")

        print(f"\n  Total Findings: {len(result.findings)}")
        print(f"  Recommendations: {len(result.recommendations)}")
    else:
        print(f"✗ Analysis failed")

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
