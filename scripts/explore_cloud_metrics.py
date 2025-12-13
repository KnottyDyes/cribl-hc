#!/usr/bin/env python3
"""
Explore Cribl Cloud metrics endpoints to find disk/resource data.

Tests various endpoint patterns to discover what's available.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cribl_hc.core.api_client import CriblAPIClient


async def test_endpoint(client, endpoint, description):
    """Test a single endpoint and report results."""
    try:
        response = await client._client.get(endpoint)

        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ {description}")
            print(f"  Endpoint: {endpoint}")
            print(f"  Status: {response.status_code}")

            # Show structure
            if isinstance(data, dict):
                print(f"  Keys: {list(data.keys())[:10]}")

                # Look for worker-related data
                for key in ['items', 'workers', 'data', 'metrics']:
                    if key in data:
                        print(f"  Found '{key}' field")
                        if isinstance(data[key], list) and len(data[key]) > 0:
                            print(f"    First item keys: {list(data[key][0].keys())[:10]}")
                        elif isinstance(data[key], dict):
                            print(f"    Subkeys: {list(data[key].keys())[:10]}")

            return True, data
        else:
            print(f"\n✗ {description}")
            print(f"  Endpoint: {endpoint}")
            print(f"  Status: {response.status_code}")
            return False, None

    except Exception as e:
        print(f"\n✗ {description}")
        print(f"  Endpoint: {endpoint}")
        print(f"  Error: {str(e)[:100]}")
        return False, None


async def main():
    import os

    url = os.environ.get("CRIBL_URL")
    token = os.environ.get("CRIBL_TOKEN")

    if not url or not token:
        print("Please set CRIBL_URL and CRIBL_TOKEN environment variables")
        sys.exit(1)

    print("=" * 80)
    print("CRIBL CLOUD METRICS ENDPOINT DISCOVERY")
    print("=" * 80)
    print(f"\nTarget: {url}")

    async with CriblAPIClient(base_url=url, auth_token=token) as client:
        worker_group = client._worker_group or "default"

        print(f"Worker group: {worker_group}\n")

        # Test various endpoint patterns
        endpoints_to_test = [
            # System-level metrics
            ("/api/v1/metrics", "System metrics (self-hosted)"),
            ("/api/v1/system/metrics", "System metrics (alt)"),
            (f"/api/v1/m/{worker_group}/metrics", "Worker group metrics"),

            # Worker-specific metrics
            ("/api/v1/master/workers/metrics", "Worker metrics (master)"),
            (f"/api/v1/m/{worker_group}/workers/metrics", "Worker metrics (group)"),

            # System status
            ("/api/v1/system/status", "System status"),
            (f"/api/v1/m/{worker_group}/system/status", "Worker group status"),

            # Health endpoints
            ("/api/v1/health", "Health endpoint"),
            (f"/api/v1/m/{worker_group}/health", "Worker group health"),

            # Stats endpoints
            ("/api/v1/stats", "Stats endpoint"),
            (f"/api/v1/m/{worker_group}/stats", "Worker group stats"),

            # Monitoring endpoints
            ("/api/v1/monitoring/metrics", "Monitoring metrics"),
            (f"/api/v1/m/{worker_group}/monitoring/metrics", "Worker group monitoring"),
        ]

        successful_endpoints = []

        for endpoint, description in endpoints_to_test:
            success, data = await test_endpoint(client, endpoint, description)
            if success:
                successful_endpoints.append((endpoint, description, data))

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        if successful_endpoints:
            print(f"\n✓ Found {len(successful_endpoints)} working endpoint(s):\n")

            for endpoint, description, data in successful_endpoints:
                print(f"  • {endpoint}")
                print(f"    {description}")

                # Check for disk metrics
                has_disk = False
                data_str = json.dumps(data).lower()
                if 'disk' in data_str:
                    has_disk = True
                    print(f"    ⭐ Contains 'disk' data!")

                print()

            # Show full data for first successful endpoint
            if successful_endpoints:
                print("\nFull data from first successful endpoint:")
                print("=" * 80)
                endpoint, desc, data = successful_endpoints[0]
                print(json.dumps(data, indent=2)[:2000])
                if len(json.dumps(data)) > 2000:
                    print("\n... (truncated, see full output above)")
        else:
            print("\n✗ No working metrics endpoints found")
            print("\nNote: Cribl Cloud may not expose metrics via REST API.")
            print("Worker data from /api/v1/master/workers might be the only source.")

        print("\n" + "=" * 80)
        print("CHECKING WORKER DATA FOR DISK METRICS")
        print("=" * 80)

        # Check worker data structure
        workers = await client.get_workers()
        if workers:
            print(f"\nFound {len(workers)} workers")
            print("\nFirst worker structure:")
            print(json.dumps(workers[0], indent=2))

            # Check for disk in worker data
            worker_str = json.dumps(workers[0]).lower()
            if 'disk' in worker_str:
                print("\n⭐ Worker data contains 'disk' field!")
            else:
                print("\n✗ Worker data does NOT contain 'disk' field")
                print("\nAvailable fields:")
                for key in workers[0].keys():
                    print(f"  • {key}")
                    if isinstance(workers[0][key], dict):
                        print(f"    Subkeys: {list(workers[0][key].keys())[:10]}")


if __name__ == "__main__":
    asyncio.run(main())
