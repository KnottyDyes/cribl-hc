#!/usr/bin/env python3
"""
Wrapper script to discover API endpoints using stored sandbox credentials.

This script loads the 'sandbox' credentials from encrypted storage and runs
the API discovery tool against the sandbox instance.

Usage:
    python3 scripts/discover_sandbox_api.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cribl_hc.utils.crypto import CredentialEncryptor


def load_sandbox_credentials():
    """
    Load sandbox credentials from encrypted storage.

    Returns:
        Tuple of (base_url, api_token) or (None, None) if not found
    """
    cred_dir = Path.home() / ".cribl-hc"
    key_file = cred_dir / ".key"
    cred_file = cred_dir / "credentials.enc"

    if not key_file.exists():
        print("❌ Encryption key not found at: ~/.cribl-hc/.key")
        return None, None

    if not cred_file.exists():
        print("❌ Credentials file not found at: ~/.cribl-hc/credentials.enc")
        return None, None

    # Load encryption key
    with open(key_file, 'rb') as f:
        master_key = f.read()

    # Load encrypted credentials
    with open(cred_file, 'rb') as f:
        encrypted_data = f.read()

    # Decrypt
    encryptor = CredentialEncryptor(master_key=master_key)
    try:
        decrypted_json = encryptor.decrypt(encrypted_data)
        credentials = json.loads(decrypted_json)
    except Exception as e:
        print(f"❌ Failed to decrypt credentials: {e}")
        return None, None

    # Debug: print credential structure
    print(f"📋 Credential structure type: {type(credentials)}")

    # Handle both dict and list structures
    if isinstance(credentials, dict):
        # Dictionary structure - check if 'sandbox' is a key
        if 'sandbox' in credentials:
            sandbox_cred = credentials['sandbox']
        else:
            print("❌ No 'sandbox' key found in credentials")
            print(f"\nAvailable keys: {list(credentials.keys())}")
            return None, None
    elif isinstance(credentials, list):
        # List structure
        sandbox_cred = None
        for cred in credentials:
            if isinstance(cred, dict):
                if cred.get('name') == 'sandbox' or cred.get('deployment_name') == 'sandbox':
                    sandbox_cred = cred
                    break

        if not sandbox_cred:
            print("❌ No 'sandbox' credentials found in storage")
            print("\nAvailable credentials:")
            for cred in credentials:
                if isinstance(cred, dict):
                    print(f"  - {cred.get('name', cred.get('deployment_name', 'unnamed'))}")
            return None, None
    else:
        print(f"❌ Unexpected credentials format: {type(credentials)}")
        return None, None

    # Extract base_url and token (handle different field names)
    base_url = sandbox_cred.get('base_url') or sandbox_cred.get('url')
    api_token = sandbox_cred.get('bearer_token') or sandbox_cred.get('token') or sandbox_cred.get('api_token')

    if not base_url or not api_token:
        print("❌ Sandbox credentials missing base_url or bearer_token")
        return None, None

    print(f"✅ Loaded sandbox credentials")
    print(f"   URL: {base_url}")
    print(f"   Token: {'*' * 20}{api_token[-8:]}\n")

    return base_url, api_token


async def run_discovery(base_url: str, api_token: str):
    """Run the API discovery."""
    # Import the discovery module
    import httpx
    from datetime import datetime

    class APIDiscovery:
        """Discover and document Cribl API endpoints."""

        def __init__(self, base_url: str, api_token: str):
            self.base_url = base_url.rstrip('/')
            self.api_token = api_token
            self.client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0,
                follow_redirects=True
            )
            self.results = {
                "discovery_time": datetime.utcnow().isoformat(),
                "base_url": base_url,
                "product_type": None,
                "endpoints": {},
                "lake_endpoints": {},
                "search_endpoints": {},
                "errors": []
            }

        async def discover(self):
            """Run full API discovery."""
            print(f"🔍 Discovering API endpoints for: {self.base_url}\n")

            await self.identify_product()
            await self.test_common_endpoints()

            # Discover workspaces first
            workspaces = await self.discover_workspaces()

            # Always test Lake and Search endpoints since Cribl.Cloud
            # can include multiple products in one instance
            await self.test_lake_endpoints()
            await self.test_search_endpoints()

            # Test workspace-scoped endpoints
            if workspaces:
                await self.test_workspace_scoped_endpoints(workspaces)

            await self.get_api_reference()
            await self.client.aclose()

            self.save_results()
            self.print_summary()

        async def identify_product(self):
            """Identify the product type."""
            print("📦 Identifying product type...")
            version_data = await self.test_endpoint("GET", "/api/v1/version")
            if version_data:
                product = version_data.get("product", "unknown")
                self.results["product_type"] = product.lower()
                print(f"   ✅ Product: {product}")
                print(f"   ✅ Version: {version_data.get('version', 'unknown')}\n")
            else:
                self.results["product_type"] = "unknown"
                print("   ⚠️  Could not identify product type\n")

        async def discover_workspaces(self):
            """Discover available workspaces."""
            print("🏢 Discovering workspaces...")
            workspaces = []

            # Try multiple workspace endpoint patterns
            workspace_endpoints = [
                "/api/v1/m",
                "/api/v1/master/groups",
                "/api/v1/system/groups",
            ]

            for endpoint in workspace_endpoints:
                data = await self.test_endpoint("GET", endpoint, "List workspaces")
                if data:
                    if isinstance(data, dict):
                        # Handle different response formats
                        items = data.get("items", [])
                        if items:
                            workspaces.extend([item.get("id") or item.get("name") for item in items if isinstance(item, dict)])
                    elif isinstance(data, list):
                        workspaces.extend([item.get("id") or item.get("name") for item in data if isinstance(item, dict)])

            # Based on the provided URL, also try common workspace names
            common_workspaces = ["default_search", "default", "system", "main"]

            if not workspaces:
                print("   ⚠️  No workspaces discovered via API, testing common names...")
                workspaces = common_workspaces
            else:
                print(f"   ✅ Discovered workspaces: {workspaces}")
                # Also add common ones that might not be in the list
                workspaces.extend([w for w in common_workspaces if w not in workspaces])

            print(f"   📋 Will test workspaces: {workspaces}\n")
            return workspaces

        async def test_common_endpoints(self):
            """Test common endpoints."""
            print("🔧 Testing common endpoints...")
            common_endpoints = [
                ("GET", "/api/v1/system/status", "System status"),
                ("GET", "/api/v1/system/settings", "System settings"),
                ("GET", "/api/v1/health", "Health check"),
                ("GET", "/api/v1/version", "Version info"),
                ("GET", "/api/v1/metrics", "Metrics"),
            ]

            for method, path, description in common_endpoints:
                data = await self.test_endpoint(method, path, description)
                if data:
                    self.results["endpoints"][path] = {
                        "method": method,
                        "description": description,
                        "available": True,
                        "sample_keys": list(data.keys()) if isinstance(data, dict) else None
                    }
            print()

        async def test_lake_endpoints(self):
            """Test Lake endpoints."""
            print("🏞️  Testing Lake-specific endpoints...")
            lake_endpoints = [
                # Dataset management
                ("GET", "/api/v1/datasets", "List datasets"),
                ("GET", "/api/v1/lake/datasets", "Lake datasets"),
                ("GET", "/api/v1/m/system/datasets", "System datasets"),

                # Lakehouse
                ("GET", "/api/v1/lakehouses", "List lakehouses"),
                ("GET", "/api/v1/lake/lakehouses", "Lake lakehouses"),

                # Storage
                ("GET", "/api/v1/storage", "Storage info"),
                ("GET", "/api/v1/storage/locations", "Storage locations"),
                ("GET", "/api/v1/lake/storage", "Lake storage"),

                # Monitoring
                ("GET", "/api/v1/lake/metrics", "Lake metrics"),
                ("GET", "/api/v1/lake/health", "Lake health"),
                ("GET", "/api/v1/lake/status", "Lake status"),

                # Retention
                ("GET", "/api/v1/lake/retention", "Retention policies"),
            ]

            for method, path, description in lake_endpoints:
                data = await self.test_endpoint(method, path, description)
                if data:
                    self.results["lake_endpoints"][path] = {
                        "method": method,
                        "description": description,
                        "available": True,
                        "sample_keys": list(data.keys()) if isinstance(data, dict) else None,
                        "sample_data": data if len(str(data)) < 500 else "... truncated ..."
                    }
            print()

        async def test_search_endpoints(self):
            """Test Search endpoints."""
            print("🔎 Testing Search-specific endpoints...")
            search_endpoints = [
                # Search jobs
                ("GET", "/api/v1/search/jobs", "Search jobs"),
                ("POST", "/api/v1/search/jobs", "Create search job"),
                ("GET", "/api/v1/jobs", "Jobs list"),

                # Datasets
                ("GET", "/api/v1/search/datasets", "Search datasets"),
                ("GET", "/api/v1/search/providers", "Dataset providers"),

                # Queries
                ("GET", "/api/v1/search/saved", "Saved searches"),
                ("GET", "/api/v1/search/scheduled", "Scheduled searches"),

                # Monitoring
                ("GET", "/api/v1/search/metrics", "Search metrics"),
                ("GET", "/api/v1/search/stats", "Search statistics"),
                ("GET", "/api/v1/search/health", "Search health"),
                ("GET", "/api/v1/search/status", "Search status"),

                # Workspaces
                ("GET", "/api/v1/workspaces", "Workspaces"),
                ("GET", "/api/v1/search/workspaces", "Search workspaces"),
            ]

            for method, path, description in search_endpoints:
                data = await self.test_endpoint(method, path, description)
                if data:
                    self.results["search_endpoints"][path] = {
                        "method": method,
                        "description": description,
                        "available": True,
                        "sample_keys": list(data.keys()) if isinstance(data, dict) else None,
                        "sample_data": data if len(str(data)) < 500 else "... truncated ..."
                    }
            print()

        async def test_workspace_scoped_endpoints(self, workspaces):
            """Test workspace-scoped endpoints for Search and Lake."""
            print("🔬 Testing workspace-scoped endpoints...")

            # Initialize workspace results
            if "workspace_endpoints" not in self.results:
                self.results["workspace_endpoints"] = {}

            for workspace in workspaces:
                print(f"\n   📂 Testing workspace: {workspace}")
                workspace_results = {
                    "search": {},
                    "lake": {}
                }

                # Search endpoints (based on user's provided URL pattern)
                search_patterns = [
                    ("GET", f"/api/v1/m/{workspace}/search/jobs", "Search jobs"),
                    ("GET", f"/api/v1/m/{workspace}/search/datasets", "Search datasets"),
                    ("GET", f"/api/v1/m/{workspace}/search/dashboards", "Dashboards"),
                    ("GET", f"/api/v1/m/{workspace}/search/saved", "Saved searches"),
                    ("GET", f"/api/v1/m/{workspace}/search/scheduled", "Scheduled searches"),
                    ("GET", f"/api/v1/m/{workspace}/search/metrics", "Search metrics"),
                    ("GET", f"/api/v1/m/{workspace}/search/stats", "Search stats"),
                    ("GET", f"/api/v1/m/{workspace}/search/health", "Search health"),
                    ("GET", f"/api/v1/m/{workspace}/search/providers", "Dataset providers"),
                    ("GET", f"/api/v1/m/{workspace}/search/workspaces", "Workspaces"),
                ]

                # Lake endpoints
                lake_patterns = [
                    ("GET", f"/api/v1/m/{workspace}/lake/datasets", "Lake datasets"),
                    ("GET", f"/api/v1/m/{workspace}/lake/lakehouses", "Lakehouses"),
                    ("GET", f"/api/v1/m/{workspace}/lake/storage", "Lake storage"),
                    ("GET", f"/api/v1/m/{workspace}/lake/health", "Lake health"),
                    ("GET", f"/api/v1/m/{workspace}/lake/metrics", "Lake metrics"),
                    ("GET", f"/api/v1/m/{workspace}/datasets", "Datasets"),
                    ("GET", f"/api/v1/m/{workspace}/lakehouses", "Lakehouses"),
                ]

                # Test Search endpoints
                for method, path, description in search_patterns:
                    data = await self.test_endpoint(method, path, f"{workspace} - {description}")
                    if data:
                        workspace_results["search"][path] = {
                            "method": method,
                            "description": description,
                            "available": True,
                            "sample_keys": list(data.keys()) if isinstance(data, dict) else None,
                            "sample_data": data if len(str(data)) < 500 else "... truncated ..."
                        }

                # Test Lake endpoints
                for method, path, description in lake_patterns:
                    data = await self.test_endpoint(method, path, f"{workspace} - {description}")
                    if data:
                        workspace_results["lake"][path] = {
                            "method": method,
                            "description": description,
                            "available": True,
                            "sample_keys": list(data.keys()) if isinstance(data, dict) else None,
                            "sample_data": data if len(str(data)) < 500 else "... truncated ..."
                        }

                # Only save workspace if we found any endpoints
                if workspace_results["search"] or workspace_results["lake"]:
                    self.results["workspace_endpoints"][workspace] = workspace_results

            print()

        async def get_api_reference(self):
            """Try to fetch API reference."""
            print("📚 Attempting to fetch API reference...")
            reference_paths = [
                "/api/v1/docs",
                "/api/v1/openapi",
                "/api/v1/swagger",
            ]

            for path in reference_paths:
                data = await self.test_endpoint("GET", path)
                if data:
                    self.results["api_reference"] = {
                        "path": path,
                        "available": True
                    }
                    print(f"   ✅ Found API reference at: {path}")
                    break
            print()

        async def test_endpoint(self, method: str, path: str, description: str = None):
            """Test a single endpoint."""
            url = f"{self.base_url}{path}"
            desc = description or path

            try:
                response = await self.client.request(method, url)

                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"   ✅ {desc}: {path}")
                        return data
                    except json.JSONDecodeError:
                        print(f"   ⚠️  {desc}: {path} (non-JSON)")
                        return {"_raw": response.text[:200]}
                elif response.status_code == 404:
                    return None
                elif response.status_code == 401:
                    print(f"   🔒 {desc}: {path} (auth required)")
                    self.results["errors"].append({
                        "endpoint": path,
                        "error": "Authentication required"
                    })
                    return None
                elif response.status_code == 403:
                    print(f"   🚫 {desc}: {path} (forbidden)")
                    return None
                else:
                    return None
            except Exception as e:
                if "404" not in str(e):
                    print(f"   ❌ {desc}: {path} - {str(e)[:50]}")
                return None

        def save_results(self):
            """Save results to file."""
            filename = f"api_discovery_sandbox_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = Path("scripts") / filename

            with open(filepath, 'w') as f:
                json.dump(self.results, f, indent=2)

            print(f"💾 Results saved to: {filepath}\n")

        def print_summary(self):
            """Print summary."""
            print("=" * 70)
            print("📊 DISCOVERY SUMMARY")
            print("=" * 70)
            print(f"Product Type: {self.results['product_type']}")
            print(f"Common Endpoints: {len(self.results['endpoints'])}")
            print(f"Lake Endpoints: {len(self.results['lake_endpoints'])}")
            print(f"Search Endpoints: {len(self.results['search_endpoints'])}")

            # Count workspace endpoints
            workspace_count = 0
            if "workspace_endpoints" in self.results:
                for workspace, endpoints in self.results["workspace_endpoints"].items():
                    workspace_count += len(endpoints.get("search", {})) + len(endpoints.get("lake", {}))
            print(f"Workspace-Scoped Endpoints: {workspace_count}")

            print(f"Errors: {len(self.results['errors'])}")
            print("=" * 70)

            if self.results['endpoints']:
                print("\n✅ Available Common Endpoints:")
                for path, info in self.results['endpoints'].items():
                    print(f"   {info['method']} {path} - {info['description']}")

            if self.results['lake_endpoints']:
                print("\n🏞️  Available Lake Endpoints:")
                for path, info in self.results['lake_endpoints'].items():
                    print(f"   {info['method']} {path} - {info['description']}")

            if self.results['search_endpoints']:
                print("\n🔎 Available Search Endpoints:")
                for path, info in self.results['search_endpoints'].items():
                    print(f"   {info['method']} {path} - {info['description']}")

            if "workspace_endpoints" in self.results and self.results["workspace_endpoints"]:
                print("\n🏢 Workspace-Scoped Endpoints:")
                for workspace, endpoints in self.results["workspace_endpoints"].items():
                    search_count = len(endpoints.get("search", {}))
                    lake_count = len(endpoints.get("lake", {}))
                    if search_count > 0 or lake_count > 0:
                        print(f"\n   📂 Workspace: {workspace}")
                        if search_count > 0:
                            print(f"      🔎 Search endpoints: {search_count}")
                            for path, info in endpoints["search"].items():
                                print(f"         {info['method']} {path}")
                        if lake_count > 0:
                            print(f"      🏞️  Lake endpoints: {lake_count}")
                            for path, info in endpoints["lake"].items():
                                print(f"         {info['method']} {path}")

    discovery = APIDiscovery(base_url, api_token)
    await discovery.discover()


async def main():
    """Main entry point."""
    print("🔐 Loading sandbox credentials from encrypted storage...\n")

    base_url, api_token = load_sandbox_credentials()

    if not base_url or not api_token:
        print("\n❌ Failed to load credentials. Exiting.")
        sys.exit(1)

    await run_discovery(base_url, api_token)


if __name__ == "__main__":
    asyncio.run(main())
