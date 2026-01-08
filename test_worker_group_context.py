#!/usr/bin/env python3
"""
Test to verify worker group context is properly applied to findings.
"""

import asyncio
import sys

sys.path.insert(0, "src")

from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.analyzers.fleet import FleetAnalyzer
from cribl_hc.cli.commands.config import load_credentials


async def test_worker_group_context():
    """Test that findings include proper worker group context."""

    # Load from stored credentials
    try:
        credentials = load_credentials()
        if "EDC" not in credentials:
            print("❌ EDC deployment not found in stored credentials")
            return False

        cred = credentials["EDC"]
        url = cred["url"]
        token = cred["token"]
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        return False

    print(f"Testing worker group context with: {url}")

    analyzer = FleetAnalyzer()

    try:
        print("Running FleetAnalyzer...")
        async with CriblAPIClient(url, token) as client:
            result = await analyzer.analyze(client)

            print(f"\n=== ANALYSIS RESULT ===")
            print(f"Success: {result.success}")
            print(f"Findings count: {len(result.findings)}")
            print(f"Metadata keys: {list(result.metadata.keys())}")

            if result.metadata.get("worker_groups_by_type"):
                print(f"\nWorker Groups by Type:")
                for group_type, count in result.metadata["worker_groups_by_type"].items():
                    print(f"  {group_type}: {count}")

            print(f"\n=== FINDINGS ANALYSIS ===")
            findings_with_worker_group = 0
            findings_without_worker_group = 0

            for i, finding in enumerate(result.findings):
                has_worker_group = finding.worker_group is not None
                if has_worker_group:
                    findings_with_worker_group += 1
                else:
                    findings_without_worker_group += 1

                print(f"\nFinding {i + 1}: {finding.id}")
                print(f"  Title: {finding.title}")
                print(f"  Severity: {finding.severity}")
                print(f"  Worker Group: {finding.worker_group}")
                print(f"  Metadata: {finding.metadata}")

                if "worker_group_id" in finding.metadata:
                    print(
                        f"  ✓ Has worker_group_id in metadata: {finding.metadata['worker_group_id']}"
                    )
                else:
                    print(f"  ✗ Missing worker_group_id in metadata")

            print(f"\n=== SUMMARY ===")
            print(f"Findings with worker_group: {findings_with_worker_group}")
            print(f"Findings without worker_group: {findings_without_worker_group}")

            if findings_with_worker_group > 0:
                print(f"✓ SUCCESS: Findings have worker group context")
                return True
            else:
                print(f"✗ ISSUE: No findings have worker group context")
                return False

    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_worker_group_context())
    exit(0 if success else 1)
