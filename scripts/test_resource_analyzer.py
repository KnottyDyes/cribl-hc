#!/usr/bin/env python3
"""
Test ResourceAnalyzer against a real Cribl deployment.

This script connects to a real Cribl API and runs the ResourceAnalyzer
to test resource utilization monitoring against live data.

Usage:
    python scripts/test_resource_analyzer.py --url https://your-cribl.example.com --token YOUR_TOKEN

Example:
    python scripts/test_resource_analyzer.py \
        --url https://cribl.mycompany.com \
        --token eyJhbGc...your-token-here
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add src to path so we can import cribl_hc
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cribl_hc.analyzers.resource import ResourceAnalyzer
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
    print(f"  TOTAL:    {len(findings)}")
    return critical, high, medium, low


def print_finding(finding, index, total):
    """Print a single finding."""
    print(f"\n[{index}/{total}] {finding.severity.upper()}: {finding.title}")
    print(f"    ID: {finding.id}")
    print(f"    Description: {finding.description}")

    if finding.affected_components:
        print(f"    Affected: {', '.join(finding.affected_components[:3])}")

    if finding.estimated_impact:
        print(f"    Impact: {finding.estimated_impact}")

    if finding.remediation_steps:
        print(f"    Remediation:")
        for i, step in enumerate(finding.remediation_steps[:2], 1):
            print(f"      {i}. {step}")
        if len(finding.remediation_steps) > 2:
            print(f"      ... ({len(finding.remediation_steps) - 2} more steps)")

    if finding.metadata:
        print(f"    Metadata: {json.dumps(finding.metadata, indent=6)}")


def print_recommendation(rec, index, total):
    """Print a single recommendation."""
    print(f"\n[{index}/{total}] {rec.priority.upper()}: {rec.title}")
    print(f"    ID: {rec.id}")
    print(f"    Type: {rec.type}")
    print(f"    Description: {rec.description}")
    print(f"    Rationale: {rec.rationale}")

    if rec.implementation_steps:
        print(f"    Implementation:")
        for i, step in enumerate(rec.implementation_steps[:3], 1):
            print(f"      {i}. {step}")
        if len(rec.implementation_steps) > 3:
            print(f"      ... ({len(rec.implementation_steps) - 3} more steps)")

    if rec.impact_estimate:
        print(f"    Impact:")
        if rec.impact_estimate.performance_improvement:
            print(f"      Performance: {rec.impact_estimate.performance_improvement}")
        if rec.impact_estimate.cost_impact:
            print(f"      Cost: {rec.impact_estimate.cost_impact}")
        if rec.impact_estimate.time_to_implement:
            print(f"      Time: {rec.impact_estimate.time_to_implement}")


async def test_connection(url: str, token: str) -> bool:
    """Test connection to Cribl API."""
    print_section("Connection Test")

    try:
        async with CriblAPIClient(base_url=url, auth_token=token) as client:
            result = await client.test_connection()

            if result.success:
                print(f"✓ Connection successful!")
                print(f"  URL: {result.api_url}")
                print(f"  Response time: {result.response_time_ms:.0f}ms")
                print(f"  Cribl Version: {result.cribl_version}")
                return True
            else:
                print(f"✗ Connection failed!")
                print(f"  Error: {result.error}")
                return False

    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False


async def run_resource_analyzer(url: str, token: str, verbose: bool = False):
    """Run ResourceAnalyzer against real deployment."""
    print_section("Resource Utilization Analysis")

    try:
        async with CriblAPIClient(base_url=url, auth_token=token) as client:
            # Create and run analyzer
            analyzer = ResourceAnalyzer()

            print(f"Analyzer: {analyzer.__class__.__name__}")
            print(f"Objective: {analyzer.objective_name}")
            print(f"Estimated API calls: {analyzer.get_estimated_api_calls()}")
            print(f"Required permissions: {', '.join(analyzer.get_required_permissions())}")

            print(f"\nRunning analysis...")
            result = await analyzer.analyze(client)

            print(f"\n✓ Analysis completed!")
            print(f"  Success: {result.success}")
            print(f"  Objective: {result.objective}")

            # Print metadata
            print_section("Resource Metrics Summary")
            print(f"Worker count: {result.metadata.get('worker_count', 0)}")
            print(f"Total CPUs: {result.metadata.get('total_cpus', 0)}")
            print(f"Total Memory: {result.metadata.get('total_memory_gb', 0):.1f} GB")
            print(f"Avg CPU Utilization: {result.metadata.get('avg_cpu_utilization', 0):.1f}%")
            print(
                f"Avg Memory Utilization: {result.metadata.get('avg_memory_utilization', 0):.1f}%"
            )
            print(
                f"\nResource Health Score: {result.metadata.get('resource_health_score', 0):.1f}/100"
            )

            # Print findings summary
            print_section("Findings")
            critical, high, medium, low = print_findings_summary(result.findings)

            # Print detailed findings
            if verbose or len(result.findings) <= 10:
                # Print CRITICAL findings
                if critical:
                    print("\n" + "=" * 80)
                    print("CRITICAL FINDINGS:")
                    print("=" * 80)
                    for i, finding in enumerate(critical, 1):
                        print_finding(finding, i, len(critical))

                # Print HIGH findings
                if high:
                    print("\n" + "=" * 80)
                    print("HIGH FINDINGS:")
                    print("=" * 80)
                    for i, finding in enumerate(high, 1):
                        print_finding(finding, i, len(high))

                # Print MEDIUM findings (first 5 only)
                if medium:
                    print("\n" + "=" * 80)
                    print("MEDIUM FINDINGS (first 5):")
                    print("=" * 80)
                    for i, finding in enumerate(medium[:5], 1):
                        print_finding(finding, i, min(5, len(medium)))
                    if len(medium) > 5:
                        print(f"\n... and {len(medium) - 5} more medium findings")
            else:
                print(f"\nRun with --verbose to see all {len(result.findings)} findings")

            # Print recommendations
            if result.recommendations:
                print_section("Capacity Recommendations")
                print(f"Total recommendations: {len(result.recommendations)}")

                for i, rec in enumerate(result.recommendations, 1):
                    print_recommendation(rec, i, len(result.recommendations))
            else:
                print("\nNo capacity recommendations - resources are healthy!")

            # Print API usage
            print_section("API Usage")
            print(f"API calls used: {client.get_api_calls_used()}")
            print(f"API calls remaining: {client.get_api_calls_remaining()}")

            return result

    except Exception as e:
        print(f"\n✗ Analysis failed: {e}")
        import traceback

        traceback.print_exc()
        return None


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test ResourceAnalyzer against real Cribl deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with Cribl Cloud:
  python scripts/test_resource_analyzer.py \\
      --url https://main-myorg.cribl.cloud \\
      --token eyJhbGc...

  # Test with self-hosted Cribl:
  python scripts/test_resource_analyzer.py \\
      --url https://cribl.example.com:9000 \\
      --token your-api-token

  # Skip connection test:
  python scripts/test_resource_analyzer.py \\
      --url https://cribl.example.com \\
      --token your-token \\
      --no-connection-test

  # Verbose output:
  python scripts/test_resource_analyzer.py \\
      --url https://cribl.example.com \\
      --token your-token \\
      --verbose
        """,
    )

    parser.add_argument(
        "--url", required=True, help="Cribl API URL (e.g., https://cribl.example.com)"
    )

    parser.add_argument("--token", required=True, help="Cribl API bearer token")

    parser.add_argument(
        "--no-connection-test",
        action="store_true",
        help="Skip initial connection test",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output for all findings",
    )

    args = parser.parse_args()

    print("\n")
    print("=" * 80)
    print("  CRIBL RESOURCE ANALYZER - REAL DEPLOYMENT TEST")
    print("=" * 80)
    print(f"\nTarget URL: {args.url}")
    print(f"Token: {args.token[:20]}...{args.token[-10:]}")
    print("\n")

    # Test connection first (unless skipped)
    if not args.no_connection_test:
        connection_ok = await test_connection(args.url, args.token)
        if not connection_ok:
            print("\n✗ Connection test failed. Exiting.")
            sys.exit(1)
        print("\n")

    # Run ResourceAnalyzer
    result = await run_resource_analyzer(args.url, args.token, verbose=args.verbose)

    if result:
        print("\n")
        print_separator("=")
        print("  TEST COMPLETED SUCCESSFULLY")
        print_separator("=")
        print(f"\nResource Health Score: {result.metadata.get('resource_health_score', 0):.1f}/100")
        print(f"Total findings: {len(result.findings)}")
        print(f"Total recommendations: {len(result.recommendations)}")
        print("\n")
        sys.exit(0)
    else:
        print("\n")
        print_separator("=")
        print("  TEST FAILED")
        print_separator("=")
        print("\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
