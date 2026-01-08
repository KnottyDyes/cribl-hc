#!/usr/bin/env python3
"""
Debug script to check if Edge Fleets are contaminating worker group analysis.
"""

import asyncio
import json
import sys

sys.path.insert(0, "src")

from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.cli.commands.config import load_credentials


async def debug_edge_contamination():
    """Check if Edge Fleets are causing issues with worker analysis."""

    try:
        credentials = load_credentials()
        if "EDC" not in credentials:
            print("❌ EDC deployment not found")
            return

        cred = credentials["EDC"]
        url = cred["url"]
        token = cred["token"]

        print("🔍 Checking Edge Fleet contamination in worker analysis...")
        print(f"🔗 URL: {url}")
        print("=" * 70)

        async with CriblAPIClient(url, token) as client:
            # Get all groups from master/groups endpoint
            all_groups = await client.get_worker_groups()

            # Separate by type
            worker_groups = [
                g
                for g in all_groups
                if not g.get("isFleet", False) and not g.get("isSearch", False)
            ]
            edge_fleets = [g for g in all_groups if g.get("isFleet", False)]
            search_groups = [g for g in all_groups if g.get("isSearch", False)]

            print(f"📊 Group Breakdown:")
            print(f"   Worker Groups: {len(worker_groups)}")
            print(f"   Edge Fleets: {len(edge_fleets)}")
            print(f"   Search Groups: {len(search_groups)}")
            print()

            # Check worker data sources
            print("🔍 Checking worker data sources:")

            # Stream workers
            try:
                stream_workers = await client.get("/api/v1/master/workers")
                stream_workers.raise_for_status()
                workers = stream_workers.json().get("items", [])
                print(f"   Stream workers (/api/v1/master/workers): {len(workers)}")
                if workers:
                    worker_groups_in_data = set(w.get("group", "default") for w in workers)
                    print(f"   Worker groups with actual workers: {worker_groups_in_data}")
            except Exception as e:
                print(f"   Stream workers: ERROR - {e}")

            # Edge nodes
            try:
                edge_response = await client.get("/api/v1/edge/nodes")
                edge_response.raise_for_status()
                edge_nodes = edge_response.json().get("items", [])
                print(f"   Edge nodes (/api/v1/edge/nodes): {len(edge_nodes)}")
                if edge_nodes:
                    fleet_groups_in_data = set(n.get("fleet", "default") for n in edge_nodes)
                    print(f"   Fleet groups with actual nodes: {fleet_groups_in_data}")
            except Exception as e:
                print(f"   Edge nodes: ERROR - {e}")

            print()

            # Analysis of contamination
            print("🚨 Contamination Analysis:")

            # Check if Edge Fleets have workerCount
            for fleet in edge_fleets:
                fleet_id = fleet.get("id", "unknown")
                worker_count = fleet.get("workerCount", "NOT_SET")
                print(f"   Fleet '{fleet_id}' workerCount: {worker_count}")

                if worker_count not in ["NOT_SET", None, 0]:
                    print(
                        f"   ⚠️  Fleet '{fleet_id}' has workerCount={worker_count} - this might be incorrect!"
                    )

            # Check if we're analyzing Edge Fleets as worker groups
            print()
            print("🔍 Current FleetAnalyzer Impact:")
            print("   Edge Fleets in master/groups: YES")
            print("   Edge Fleets included in worker analysis: YES")
            print("   Using correct API endpoints: NO (should use /api/v1/edge/nodes for fleets)")
            print()

            print("💡 Recommendations:")
            print("1. Exclude Edge Fleets from Stream worker group analysis")
            print("2. Create separate Edge Fleet health analyzer")
            print("3. Use /api/v1/edge/nodes for Edge Fleet worker data")
            print("4. Don't analyze Edge Fleets for config drift (different model)")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_edge_contamination())
