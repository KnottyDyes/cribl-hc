#!/usr/bin/env python3
import asyncio
import sys

sys.path.insert(0, "src")

from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.analyzers.health import HealthAnalyzer
from cribl_hc.cli.commands.config import load_credentials


async def debug_health_findings():
    """Debug HealthAnalyzer findings to understand worker group context."""

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

    print(f"Debugging HealthAnalyzer findings: {url}")

    analyzer = HealthAnalyzer()

    try:
        async with CriblAPIClient(url, token) as client:
            result = await analyzer.analyze(client)

            print(f"\n=== HEALTH ANALYSIS RESULT ===")
            print(f"Success: {result.success}")
            print(f"Findings count: {len(result.findings)}")

            for i, finding in enumerate(result.findings):
                print(f"\nFinding {i + 1}: {finding.id}")
                print(f"  Title: {finding.title}")
                print(f"  Description: {finding.description}")
                print(f"  Category: {finding.category}")
                print(f"  Severity: {finding.severity}")
                print(f"  Worker Group: {finding.worker_group}")
                print(f"  Affected Components: {finding.affected_components}")
                print(f"  Metadata: {finding.metadata}")

                if "worker_id" in finding.metadata:
                    print(f"    → Specific to worker: {finding.metadata['worker_id']}")
                if "group" in finding.metadata:
                    print(f"    → From group: {finding.metadata['group']}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(debug_health_findings())
