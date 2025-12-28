#!/usr/bin/env python3
"""
API Endpoint Discovery Script for Cribl Lake and Search

This script connects to a Cribl sandbox instance and discovers available
API endpoints, documenting the structure for Lake and Search analyzers.

Usage:
    python3 scripts/discover_api_endpoints.py <base_url> <api_token>

Example:
    python3 scripts/discover_api_endpoints.py https://sandbox.cribl.cloud my-api-token
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


class APIDiscovery:
    """Discover and document Cribl API endpoints."""

    def __init__(self, base_url: str, api_token: str):
        """
        Initialize API discovery.

        Args:
            base_url: Base URL of Cribl instance (e.g., https://sandbox.cribl.cloud)
            api_token: API authentication token
        """
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

        # Step 1: Identify product type
        await self.identify_product()

        # Step 2: Test common endpoints
        await self.test_common_endpoints()

        # Step 3: Test Lake-specific endpoints
        if self.results["product_type"] in ["lake", "unknown"]:
            await self.test_lake_endpoints()

        # Step 4: Test Search-specific endpoints
        if self.results["product_type"] in ["search", "unknown"]:
            await self.test_search_endpoints()

        # Step 5: Try to get API reference
        await self.get_api_reference()

        await self.client.aclose()

        # Save results
        self.save_results()
        self.print_summary()

    async def identify_product(self):
        """Identify the product type (Stream, Edge, Lake, Search)."""
        print("📦 Identifying product type...")

        # Try version endpoint
        version_data = await self.test_endpoint("GET", "/api/v1/version")
        if version_data:
            product = version_data.get("product", "unknown")
            self.results["product_type"] = product.lower()
            print(f"   ✅ Product: {product}")
            print(f"   ✅ Version: {version_data.get('version', 'unknown')}\n")
        else:
            self.results["product_type"] = "unknown"
            print("   ⚠️  Could not identify product type\n")

    async def test_common_endpoints(self):
        """Test common endpoints across all products."""
        print("🔧 Testing common endpoints...")

        common_endpoints = [
            # System endpoints
            ("GET", "/api/v1/system/status", "System status"),
            ("GET", "/api/v1/system/settings", "System settings"),
            ("GET", "/api/v1/system/info", "System info"),
            ("GET", "/api/v1/health", "Health check"),

            # Version and info
            ("GET", "/api/v1/version", "Version info"),
            ("GET", "/api/v1/about", "About"),

            # Authentication
            ("GET", "/api/v1/auth/status", "Auth status"),
            ("GET", "/api/v1/users", "Users list"),

            # Metrics
            ("GET", "/api/v1/metrics", "Metrics"),
            ("GET", "/api/v1/metrics/system", "System metrics"),
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
        """Test Lake-specific endpoints."""
        print("🏞️  Testing Lake-specific endpoints...")

        lake_endpoints = [
            # Datasets
            ("GET", "/api/v1/datasets", "List datasets"),
            ("GET", "/api/v1/lake/datasets", "Lake datasets"),
            ("GET", "/api/v1/m/{workerGroup}/datasets", "Worker group datasets"),

            # Dataset operations
            ("GET", "/api/v1/datasets/stats", "Dataset statistics"),
            ("GET", "/api/v1/datasets/usage", "Dataset usage"),

            # Lakehouses
            ("GET", "/api/v1/lakehouses", "List lakehouses"),
            ("GET", "/api/v1/lake/lakehouses", "Lake lakehouses"),

            # Storage
            ("GET", "/api/v1/storage", "Storage info"),
            ("GET", "/api/v1/storage/locations", "Storage locations"),
            ("GET", "/api/v1/storage/usage", "Storage usage"),

            # Retention
            ("GET", "/api/v1/retention", "Retention policies"),
            ("GET", "/api/v1/datasets/retention", "Dataset retention"),

            # Monitoring
            ("GET", "/api/v1/lake/metrics", "Lake metrics"),
            ("GET", "/api/v1/lake/health", "Lake health"),
            ("GET", "/api/v1/lake/status", "Lake status"),
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
        """Test Search-specific endpoints."""
        print("🔎 Testing Search-specific endpoints...")

        search_endpoints = [
            # Search jobs
            ("GET", "/api/v1/search/jobs", "Search jobs"),
            ("GET", "/api/v1/jobs", "Jobs list"),

            # Datasets
            ("GET", "/api/v1/search/datasets", "Search datasets"),
            ("GET", "/api/v1/search/providers", "Dataset providers"),

            # Queries
            ("GET", "/api/v1/search/saved", "Saved searches"),
            ("GET", "/api/v1/search/scheduled", "Scheduled searches"),

            # Performance
            ("GET", "/api/v1/search/metrics", "Search metrics"),
            ("GET", "/api/v1/search/stats", "Search statistics"),
            ("GET", "/api/v1/search/usage", "Search usage"),

            # Workspaces
            ("GET", "/api/v1/workspaces", "Workspaces"),
            ("GET", "/api/v1/search/workspaces", "Search workspaces"),

            # Monitoring
            ("GET", "/api/v1/search/health", "Search health"),
            ("GET", "/api/v1/search/status", "Search status"),
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

    async def get_api_reference(self):
        """Try to fetch API reference documentation."""
        print("📚 Attempting to fetch API reference...")

        reference_paths = [
            "/api/v1/docs",
            "/api/v1/openapi",
            "/api/v1/swagger",
            "/docs/api",
            "/api-reference",
        ]

        for path in reference_paths:
            data = await self.test_endpoint("GET", path, f"API reference at {path}")
            if data:
                self.results["api_reference"] = {
                    "path": path,
                    "available": True,
                    "data": data if len(str(data)) < 1000 else "... truncated ..."
                }
                print(f"   ✅ Found API reference at: {path}")
                break

        print()

    async def test_endpoint(
        self,
        method: str,
        path: str,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Test a single API endpoint.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            description: Human-readable description

        Returns:
            Response data if successful, None otherwise
        """
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
                    print(f"   ⚠️  {desc}: {path} (non-JSON response)")
                    return {"_raw": response.text[:200]}
            elif response.status_code == 404:
                # Endpoint doesn't exist - don't spam output
                return None
            elif response.status_code == 401:
                print(f"   🔒 {desc}: {path} (authentication required)")
                self.results["errors"].append({
                    "endpoint": path,
                    "error": "Authentication required",
                    "status_code": 401
                })
                return None
            elif response.status_code == 403:
                print(f"   🚫 {desc}: {path} (forbidden)")
                self.results["errors"].append({
                    "endpoint": path,
                    "error": "Forbidden",
                    "status_code": 403
                })
                return None
            else:
                print(f"   ⚠️  {desc}: {path} (status {response.status_code})")
                return None

        except httpx.TimeoutException:
            print(f"   ⏱️  {desc}: {path} (timeout)")
            return None
        except Exception as e:
            # Suppress connection errors for non-existent endpoints
            if "404" not in str(e):
                print(f"   ❌ {desc}: {path} - {str(e)[:100]}")
            return None

    def save_results(self):
        """Save discovery results to JSON file."""
        filename = f"api_discovery_{self.results['product_type']}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = f"scripts/{filename}"

        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"💾 Results saved to: {filepath}\n")

    def print_summary(self):
        """Print discovery summary."""
        print("=" * 70)
        print("📊 DISCOVERY SUMMARY")
        print("=" * 70)
        print(f"Product Type: {self.results['product_type']}")
        print(f"Common Endpoints Found: {len(self.results['endpoints'])}")
        print(f"Lake Endpoints Found: {len(self.results['lake_endpoints'])}")
        print(f"Search Endpoints Found: {len(self.results['search_endpoints'])}")
        print(f"Errors Encountered: {len(self.results['errors'])}")
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

        if self.results['errors']:
            print("\n⚠️  Authentication/Permission Issues:")
            for error in self.results['errors'][:5]:  # Show first 5
                print(f"   {error['endpoint']}: {error['error']}")


async def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/discover_api_endpoints.py <base_url> <api_token>")
        print()
        print("Example:")
        print("  python3 scripts/discover_api_endpoints.py https://sandbox.cribl.cloud my-api-token")
        sys.exit(1)

    base_url = sys.argv[1]
    api_token = sys.argv[2]

    discovery = APIDiscovery(base_url, api_token)
    await discovery.discover()


if __name__ == "__main__":
    asyncio.run(main())
