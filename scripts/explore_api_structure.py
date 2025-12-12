#!/usr/bin/env python3
"""
Explore Cribl Cloud API structure more thoroughly.
"""

import asyncio
import sys
import httpx
import json


async def explore_api(base_url: str, token: str):
    """Explore Cribl Cloud API endpoints."""

    base_url = base_url.rstrip("/")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # Get system settings to understand structure
        print("📋 Fetching system settings...\n")
        try:
            response = await client.get(f"{base_url}/api/v1/system/settings/conf")
            if response.status_code == 200:
                data = response.json()
                print(f"System settings keys: {list(data.keys())}\n")

                # Look for group-related info
                if "groups" in data:
                    print(f"Groups found: {data['groups']}\n")

        except Exception as e:
            print(f"Error: {e}\n")

        # Try different worker group patterns
        print("🔍 Testing various worker group patterns...\n")

        # Common group names
        test_groups = ["default", "defaultGroup", "workers", "main", "fleet"]

        for group in test_groups:
            endpoint = f"/api/v1/m/{group}/pipelines"
            try:
                response = await client.get(f"{base_url}{endpoint}")
                if response.status_code == 200:
                    items = response.json().get("items", [])
                    print(f"✓ Found! Group '{group}' has {len(items)} pipelines")
                    print(f"   Endpoint: {endpoint}\n")
                    return group
                elif response.status_code != 404:
                    print(f"  Group '{group}': HTTP {response.status_code}")
            except Exception as e:
                pass

        # Try to find worker groups by listing all groups
        print("\n🔍 Looking for worker groups list...\n")

        potential_endpoints = [
            "/api/v1/worker-groups",
            "/api/v1/groups",
            "/api/v1/m",
            "/api/v1/master/groups",
            "/api/v1/system/groups",
        ]

        for endpoint in potential_endpoints:
            try:
                response = await client.get(f"{base_url}{endpoint}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✓ {endpoint}")
                    print(f"  Response: {json.dumps(data, indent=2)[:500]}...\n")
            except Exception as e:
                pass

        # List all possible v1 endpoints
        print("\n📖 Exploring /api/v1 structure...\n")

        v1_tests = [
            "/api/v1",
            "/api/v1/",
        ]

        for endpoint in v1_tests:
            try:
                response = await client.get(f"{base_url}{endpoint}")
                print(f"{endpoint}: HTTP {response.status_code}")
                if response.status_code == 200:
                    print(f"  {response.text[:200]}...")
            except Exception as e:
                pass


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python explore_api_structure.py <URL> <TOKEN>")
        sys.exit(1)

    url = sys.argv[1]
    token = sys.argv[2]

    asyncio.run(explore_api(url, token))
