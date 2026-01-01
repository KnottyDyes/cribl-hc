#!/usr/bin/env python3
"""
Inspect Search API endpoints to get full sample data for model building.

This script loads sandbox credentials and fetches sample data from the
discovered Search endpoints to understand their structure.

Usage:
    python3 scripts/inspect_search_endpoints.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cribl_hc.utils.crypto import CredentialEncryptor
import httpx


async def inspect_endpoints():
    """Load credentials and inspect Search endpoints."""

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

    print(f"🔍 Inspecting Search API endpoints for: {base_url}\n")

    client = httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        },
        timeout=30.0,
        follow_redirects=True
    )

    # Define endpoints to inspect based on discovery
    workspace = "default_search"
    endpoints = [
        ("jobs", f"/api/v1/m/{workspace}/search/jobs"),
        ("datasets", f"/api/v1/m/{workspace}/search/datasets"),
        ("dashboards", f"/api/v1/m/{workspace}/search/dashboards"),
        ("saved", f"/api/v1/m/{workspace}/search/saved"),
        ("metrics", f"/api/v1/m/{workspace}/search/metrics"),
        ("stats", f"/api/v1/m/{workspace}/search/stats"),
        ("health", f"/api/v1/m/{workspace}/search/health"),
        ("providers", f"/api/v1/m/{workspace}/search/providers"),
    ]

    results = {}

    for name, path in endpoints:
        url = f"{base_url}{path}"
        print(f"📋 Fetching {name}...")

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
                else:
                    print(f"   ✅ Type: {type(data)}")
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
    output_file = Path("scripts") / "search_endpoints_inspection.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print("=" * 70)
    print(f"💾 Full results saved to: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(inspect_endpoints())
