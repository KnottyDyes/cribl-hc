#!/usr/bin/env python3
"""
Test the Lake API endpoint provided by the user.

User provided:
https://sandboxdev-serene-lovelace-dd6mau4.cribl.cloud/api/v1/products/lake/lakes/default/datasets?includeMetrics=true&storageLocationId=cribl_lake

This reveals Lake uses a different endpoint pattern:
/api/v1/products/lake/lakes/{lake_name}/datasets
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cribl_hc.utils.crypto import CredentialEncryptor
import httpx


async def test_lake_endpoints():
    """Test Lake endpoints using the discovered pattern."""

    # Load credentials
    cred_dir = Path.home() / ".cribl-hc"
    key_file = cred_dir / ".key"
    cred_file = cred_dir / "credentials.enc"

    with open(key_file, 'rb') as f:
        master_key = f.read()

    with open(cred_file, 'rb') as f:
        encrypted_data = f.read()

    encryptor = CredentialEncryptor(master_key=master_key)
    decrypted_json = encryptor.decrypt(encrypted_data)
    credentials = json.loads(decrypted_json)

    sandbox_cred = credentials['sandbox']
    base_url = sandbox_cred.get('base_url') or sandbox_cred.get('url')
    api_token = sandbox_cred.get('bearer_token') or sandbox_cred.get('token')

    print(f"🏞️  Testing Lake API endpoints for: {base_url}\n")

    client = httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        },
        timeout=30.0,
        follow_redirects=True
    )

    # Lake name from user's URL
    lake_name = "default"

    # Test endpoints based on user's provided URL pattern
    endpoints = [
        # User-provided endpoint
        ("datasets_with_metrics", f"/api/v1/products/lake/lakes/{lake_name}/datasets?includeMetrics=true&storageLocationId=cribl_lake"),

        # Variations
        ("datasets", f"/api/v1/products/lake/lakes/{lake_name}/datasets"),
        ("lake_info", f"/api/v1/products/lake/lakes/{lake_name}"),
        ("all_lakes", f"/api/v1/products/lake/lakes"),

        # Dataset management
        ("dataset_stats", f"/api/v1/products/lake/lakes/{lake_name}/datasets/stats"),

        # Lakehouses
        ("lakehouses", f"/api/v1/products/lake/lakes/{lake_name}/lakehouses"),

        # Health & metrics
        ("lake_health", f"/api/v1/products/lake/lakes/{lake_name}/health"),
        ("lake_metrics", f"/api/v1/products/lake/lakes/{lake_name}/metrics"),
        ("lake_status", f"/api/v1/products/lake/lakes/{lake_name}/status"),

        # Storage
        ("storage_locations", f"/api/v1/products/lake/storage/locations"),
        ("storage_usage", f"/api/v1/products/lake/lakes/{lake_name}/storage/usage"),
    ]

    results = {}

    for name, path in endpoints:
        url = f"{base_url}{path}"
        print(f"📋 Testing {name}...")

        try:
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                results[name] = {
                    "endpoint": path,
                    "status": "success",
                    "data": data
                }

                # Print summary
                if isinstance(data, dict):
                    print(f"   ✅ Keys: {list(data.keys())}")
                    if 'items' in data:
                        print(f"   ✅ Items count: {len(data['items'])}")
                        if data['items']:
                            print(f"   ✅ Sample item keys: {list(data['items'][0].keys())}")
                elif isinstance(data, list):
                    print(f"   ✅ List with {len(data)} items")
                    if data:
                        print(f"   ✅ Sample item keys: {list(data[0].keys())}")
            else:
                print(f"   ⚠️  Status {response.status_code}")
                results[name] = {
                    "endpoint": path,
                    "status": f"error_{response.status_code}"
                }

        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
            results[name] = {
                "endpoint": path,
                "status": "error",
                "error": str(e)
            }

        print()

    await client.aclose()

    # Save results
    output_file = Path("scripts") / "lake_endpoints_inspection.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print("=" * 70)
    print(f"💾 Full results saved to: {output_file}")
    print("=" * 70)

    # Print summary
    successful = [k for k, v in results.items() if v.get("status") == "success"]
    print(f"\n✅ Successful endpoints ({len(successful)}):")
    for endpoint_name in successful:
        print(f"   - {endpoint_name}: {results[endpoint_name]['endpoint']}")


if __name__ == "__main__":
    asyncio.run(test_lake_endpoints())
