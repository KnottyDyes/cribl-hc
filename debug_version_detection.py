#!/usr/bin/env python3
import asyncio
import json
import sys

sys.path.insert(0, "src")

from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.cli.commands.config import load_credentials


async def debug_version_detection():
    """Debug version detection API response."""

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

    print(f"Debugging version detection: {url}")

    try:
        async with CriblAPIClient(url, token) as client:
            print("\n=== Testing API Connection ===")
            connection_test = await client.test_connection()
            print(f"Connection successful: {connection_test.success}")
            print(f"Response time: {connection_test.response_time_ms}ms")
            print(f"Detected version: {connection_test.cribl_version}")
            print(f"Product: {getattr(connection_test, 'product', 'unknown')}")

            print("\n=== Raw API Response from /system/info ===")
            try:
                response = await client.get("/api/v1/system/info")
                if response.status_code == 200:
                    data = response.json()
                    print(json.dumps(data, indent=2))

                    items = data.get("items", [])
                    print(f"\nItems count: {len(items)}")
                    if items:
                        first_item = items[0]
                        print(f"First item keys: {list(first_item.keys())}")
                        build_info = first_item.get("BUILD", {})
                        print(f"BUILD info: {build_info}")
                        if "version" in build_info:
                            print(f"BUILD.version: {build_info['version']}")

                    if "version" in data:
                        print(f"Direct version field: {data['version']}")

                else:
                    print(f"Error: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Error fetching system info: {e}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(debug_version_detection())
