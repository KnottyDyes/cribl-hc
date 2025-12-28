#!/usr/bin/env python3
"""
Enhanced Search API Discovery Script

This script performs a more thorough search for Cribl Search endpoints
by testing common URL patterns and variations.

Usage:
    python3 scripts/discover_search_ui_endpoints.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cribl_hc.utils.crypto import CredentialEncryptor
import httpx


async def load_and_discover():
    """Load credentials and discover Search endpoints."""

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

    print(f"🔍 Comprehensive Search Discovery for: {base_url}\n")

    client = httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        },
        timeout=30.0,
        follow_redirects=True
    )

    found_endpoints = []

    # Test many possible Search endpoint patterns
    test_patterns = [
        # Search job endpoints
        "/api/v1/search/jobs",
        "/search/api/v1/jobs",
        "/api/search/jobs",
        "/search/jobs",

        # Dataset endpoints
        "/api/v1/search/datasets",
        "/search/api/v1/datasets",
        "/api/search/datasets",
        "/search/datasets",

        # Query endpoints
        "/api/v1/search/query",
        "/search/api/v1/query",
        "/api/search/query",
        "/search/query",

        # Saved searches
        "/api/v1/search/saved",
        "/search/api/v1/saved",

        # Dashboards
        "/api/v1/search/dashboards",
        "/search/api/v1/dashboards",
        "/api/v1/dashboards",

        # Metrics/Stats
        "/api/v1/search/metrics",
        "/api/v1/search/stats",
        "/search/api/v1/metrics",

        # Workspaces
        "/api/v1/workspaces",
        "/search/api/v1/workspaces",

        # Health/Status
        "/api/v1/search/health",
        "/api/v1/search/status",
        "/search/health",

        # Jobs (already found)
        "/api/v1/jobs",

        # Virtual tables (KQL)
        "/api/v1/search/vt/datasets",
        "/api/v1/search/vt/jobs",
    ]

    print("Testing endpoint patterns...\n")

    for path in test_patterns:
        url = f"{base_url}{path}"
        try:
            response = await client.get(url)
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ FOUND: {path}")
                    print(f"   Status: {response.status_code}")
                    print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                    if isinstance(data, dict) and len(str(data)) < 300:
                        print(f"   Data: {json.dumps(data, indent=2)}")
                    print()

                    found_endpoints.append({
                        "path": path,
                        "status": response.status_code,
                        "data": data if len(str(data)) < 1000 else "... truncated ..."
                    })
                except:
                    print(f"✅ FOUND (non-JSON): {path}")
                    print(f"   Status: {response.status_code}")
                    print()
            elif response.status_code in [401, 403]:
                print(f"🔒 AUTH REQUIRED: {path} (status {response.status_code})")
            # Skip 404s silently
        except Exception as e:
            if "404" not in str(e):
                print(f"❌ ERROR: {path} - {str(e)[:80]}")

    await client.aclose()

    # Save results
    output = {
        "base_url": base_url,
        "found_endpoints": found_endpoints,
        "total_found": len(found_endpoints)
    }

    output_file = Path("scripts") / "search_discovery_detailed.json"
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print("=" * 70)
    print(f"📊 SUMMARY: Found {len(found_endpoints)} working endpoints")
    print("=" * 70)
    for endpoint in found_endpoints:
        print(f"  ✅ {endpoint['path']}")
    print()
    print(f"💾 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(load_and_discover())
