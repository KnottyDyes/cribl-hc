#!/usr/bin/env python3
"""
Simple test to verify FleetAnalyzer detects hybrid worker groups.
"""

import asyncio
import sys

sys.path.insert(0, "src")

from unittest.mock import AsyncMock
from cribl_hc.analyzers.fleet import FleetAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


async def test_fleet_analyzer():
    """Test FleetAnalyzer with hybrid worker groups."""

    print("🧪 Testing FleetAnalyzer with hybrid worker groups...")

    # Create mock client
    mock_client = AsyncMock(spec=CriblAPIClient)
    mock_client.worker_group = "default"

    # Mock worker groups - simulate one hybrid group
    mock_worker_groups = [
        {
            "id": "hybrid-test",
            "name": "Test Hybrid Group",
            "onPrem": False,
            "provisioned": False,
            "workerCount": 3,
        },
        {
            "id": "cloud-managed",
            "name": "Cloud Managed Group",
            "onPrem": False,
            "provisioned": True,
            "workerCount": 5,
        },
    ]

    # Set up mock responses
    mock_client.get_worker_groups.return_value = mock_worker_groups

    # Mock the categorization
    mock_groups_by_type = {
        "on_prem": [],
        "cloud_managed": [mock_worker_groups[1]],
        "hybrid": [mock_worker_groups[0]],
        "edge_fleet": [],
        "search_group": [],
    }
    mock_client.get_worker_groups_by_type.return_value = mock_groups_by_type

    # Mock other required methods
    mock_client.get_master_summary.return_value = {"workerCount": 8, "healthyWorkerCount": 8}
    mock_client.get_workers.return_value = []

    # Test the analyzer
    analyzer = FleetAnalyzer()
    result = await analyzer.analyze(mock_client)

    print(f"✅ Analysis success: {result.success}")
    print(f"📊 Total findings: {len(result.findings)}")

    # Look for hybrid findings
    hybrid_findings = [f for f in result.findings if "hybrid" in f.id.lower()]
    print(f"🔍 Hybrid findings: {len(hybrid_findings)}")

    for finding in hybrid_findings:
        print(f"   📝 {finding.title}")
        print(f"      {finding.description}")
        print(f"      Metadata: {finding.metadata}")

    # Check metadata
    if "worker_groups_by_type" in result.metadata:
        type_breakdown = result.metadata["worker_groups_by_type"]
        print(f"📈 Worker group type breakdown: {type_breakdown}")

    if len(hybrid_findings) > 0:
        print("🎉 SUCCESS: Hybrid worker groups detected!")
    else:
        print("❌ ISSUE: No hybrid findings generated")
        print("All findings:")
        for f in result.findings:
            print(f"   - {f.id}: {f.title}")


if __name__ == "__main__":
    asyncio.run(test_fleet_analyzer())
