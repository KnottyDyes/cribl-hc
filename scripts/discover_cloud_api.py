#!/usr/bin/env python3
"""
Discover Cribl Cloud API structure.

This script helps identify the correct API endpoints for a Cribl Cloud deployment.
"""

import asyncio
import sys
import httpx
import json


async def discover_cribl_cloud_api(base_url: str, token: str):
    """Discover available Cribl Cloud API endpoints."""

    base_url = base_url.rstrip("/")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    print(f"🔍 Discovering Cribl Cloud API structure for: {base_url}\n")

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # Try to get worker groups
        print("1️⃣  Testing worker groups endpoint...")
        try:
            response = await client.get(f"{base_url}/api/v1/m")
            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Success! Found worker groups:")

                if isinstance(data, dict) and "items" in data:
                    groups = data["items"]
                    for group in groups:
                        print(f"      - {group.get('id', 'unknown')}")

                    # Test first worker group
                    if groups:
                        first_group = groups[0].get("id", "default")
                        print(f"\n2️⃣  Testing endpoints for worker group '{first_group}'...\n")

                        endpoints = [
                            f"/api/v1/m/{first_group}/pipelines",
                            f"/api/v1/m/{first_group}/routes",
                            f"/api/v1/m/{first_group}/inputs",
                            f"/api/v1/m/{first_group}/outputs",
                        ]

                        for endpoint in endpoints:
                            try:
                                resp = await client.get(f"{base_url}{endpoint}")
                                resource = endpoint.split("/")[-1]

                                if resp.status_code == 200:
                                    items = resp.json().get("items", [])
                                    print(f"   ✓ {resource:12} - {len(items)} items")
                                else:
                                    print(f"   ✗ {resource:12} - HTTP {resp.status_code}")
                            except Exception as e:
                                print(f"   ✗ {resource:12} - Error: {e}")

                        return {"worker_groups": [g.get("id") for g in groups]}
                else:
                    print(f"   Response: {json.dumps(data, indent=2)}")
            else:
                print(f"   ✗ Failed: {response.text}")

        except Exception as e:
            print(f"   ✗ Error: {e}")

        # Try common alternatives
        print("\n3️⃣  Trying alternative endpoints...")

        alternatives = [
            "/api/v1/system/settings/conf",
            "/api/v1/master/pipelines",  # Self-hosted pattern
            "/api/v1/version",
        ]

        for endpoint in alternatives:
            try:
                response = await client.get(f"{base_url}{endpoint}")
                status = "✓" if response.status_code == 200 else "✗"
                print(f"   {status} {endpoint:40} - HTTP {response.status_code}")
            except Exception as e:
                print(f"   ✗ {endpoint:40} - Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python discover_cloud_api.py <URL> <TOKEN>")
        print("\nExample:")
        print("  python discover_cloud_api.py https://sandboxdev-org.cribl.cloud eyJhbG...")
        sys.exit(1)

    url = sys.argv[1]
    token = sys.argv[2]

    asyncio.run(discover_cribl_cloud_api(url, token))
