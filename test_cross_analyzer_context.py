#!/usr/bin/env python3
import asyncio
import sys

sys.path.insert(0, "src")

from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.analyzers.fleet import FleetAnalyzer
from cribl_hc.analyzers.health import HealthAnalyzer
from cribl_hc.cli.commands.config import load_credentials


async def test_cross_analyzer_context():
    """Test worker group context across multiple analyzers."""

    try:
        credentials = load_credentials()
        if "EDC" not in credentials:
            print("❌ EDC deployment not found")
            return False

        cred = credentials["EDC"]
        url = cred["url"]
        token = cred["token"]
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        return False

    print(f"Testing cross-analyzer worker group context with: {url}")

    analyzers = [
        ("FleetAnalyzer", FleetAnalyzer()),
        ("HealthAnalyzer", HealthAnalyzer()),
    ]

    total_findings_with_context = 0
    total_findings_without_context = 0

    try:
        async with CriblAPIClient(url, token) as client:
            for analyzer_name, analyzer in analyzers:
                print(f"\n=== {analyzer_name} ===")
                result = await analyzer.analyze(client)

                print(f"Success: {result.success}")
                print(f"Findings: {len(result.findings)}")

                analyzer_with_context = 0
                analyzer_without_context = 0

                for finding in result.findings:
                    if finding.worker_group is not None:
                        analyzer_with_context += 1
                        total_findings_with_context += 1
                        print(f"  ✓ {finding.id} -> worker_group: {finding.worker_group}")
                    else:
                        analyzer_without_context += 1
                        total_findings_without_context += 1
                        print(f"  ✗ {finding.id} -> no worker_group")

                print(f"  With context: {analyzer_with_context}")
                print(f"  Without context: {analyzer_without_context}")

        print(f"\n=== OVERALL SUMMARY ===")
        print(f"Total findings with worker_group context: {total_findings_with_context}")
        print(f"Total findings without worker_group context: {total_findings_without_context}")

        if total_findings_with_context > 0:
            context_ratio = total_findings_with_context / (
                total_findings_with_context + total_findings_without_context
            )
            print(f"Context coverage: {context_ratio:.1%}")

            if context_ratio >= 0.8:
                print("✅ EXCELLENT: High worker group context coverage")
                return True
            elif context_ratio >= 0.5:
                print("⚠️  GOOD: Moderate worker group context coverage")
                return True
            else:
                print("❌ POOR: Low worker group context coverage")
                return False
        else:
            print("❌ ISSUE: No findings have worker group context")
            return False

    except Exception as e:
        print(f"Error during analysis: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_cross_analyzer_context())
    exit(0 if success else 1)
