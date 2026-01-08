#!/usr/bin/env python3
"""
Test FleetAnalyzer with your real deployment data.
"""

import asyncio
import sys

sys.path.insert(0, "src")

from cribl_hc.analyzers.fleet import FleetAnalyzer
from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.cli.commands.config import load_credentials


async def test_fleet_analyzer_real():
    """Test FleetAnalyzer with real deployment data."""

    try:
        credentials = load_credentials()
        if "EDC" not in credentials:
            print("❌ EDC deployment not found")
            return

        cred = credentials["EDC"]
        url = cred["url"]
        token = cred["token"]

        print("🧪 Testing FleetAnalyzer with real EDC data...")
        print(f"🔗 URL: {url}")
        print("=" * 60)

        async with CriblAPIClient(url, token) as client:
            analyzer = FleetAnalyzer()
            result = await analyzer.analyze(client)

            print(f"✅ Analysis success: {result.success}")
            print(f"📊 Total findings: {len(result.findings)}")

            # Check metadata
            if "worker_groups_by_type" in result.metadata:
                type_breakdown = result.metadata["worker_groups_by_type"]
                print(f"📈 Worker group type breakdown: {type_breakdown}")

            # Look for hybrid findings
            hybrid_findings = [f for f in result.findings if "hybrid" in f.id.lower()]
            print(f"🔍 Hybrid findings: {len(hybrid_findings)}")

            for finding in hybrid_findings:
                print(f"   📝 {finding.title}")
                print(f"      {finding.description}")
                print(f"      Severity: {finding.severity}")
                print(f"      Metadata: {finding.metadata}")

            # Show all findings for context
            print(f"\n📋 All findings ({len(result.findings)}):")
            for i, finding in enumerate(result.findings, 1):
                print(f"   {i}. [{finding.severity.upper()}] {finding.title}")
                print(f"      ID: {finding.id}")

            if len(hybrid_findings) > 0:
                print("\n🎉 SUCCESS: Hybrid worker groups detected in real deployment!")
            else:
                print("\n❓ No hybrid findings generated")
                print("   Possible reasons:")
                print("   - FleetAnalyzer might not be called in your normal flow")
                print("   - Different objective being used")
                print("   - Error in the analysis")

                if result.error:
                    print(f"   - Error occurred: {result.error}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_fleet_analyzer_real())
