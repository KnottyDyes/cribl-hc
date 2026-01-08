#!/usr/bin/env python3
"""
Debug script to inspect worker groups from your Cribl deployment.
Uses stored credentials from the cribl-hc config.
"""

import asyncio
import json
import sys

sys.path.insert(0, "src")

from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.cli.commands.config import load_credentials


def list_available_deployments():
    """List all stored deployments."""
    try:
        credentials = load_credentials()
        if not credentials:
            print("❌ No deployments configured.")
            print("   Use 'cribl-hc config set <name> --url <url> --token <token>' to add one.")
            return []

        print("📋 Available deployments:")
        for name, cred in credentials.items():
            url = cred.get("url", "Unknown")
            print(f"   - {name}: {url}")
        return list(credentials.keys())
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        return []


async def debug_worker_groups(
    deployment_name: str | None = None, url: str | None = None, token: str | None = None
):
    """Debug worker groups to understand their structure."""

    if deployment_name:
        try:
            credentials = load_credentials()
            if deployment_name not in credentials:
                print(f"❌ Deployment '{deployment_name}' not found in stored credentials.")
                return

            cred = credentials[deployment_name]
            url = cred["url"]
            token = cred["token"]
            print(f"🔍 Using stored credentials for '{deployment_name}'")
        except Exception as e:
            print(f"❌ Failed to load credentials for '{deployment_name}': {e}")
            return

    if not url or not token:
        print("❌ Missing URL or token")
        return

    print(f"🔍 Debugging worker groups for: {url}")
    print("=" * 60)

    async with CriblAPIClient(url, token) as client:
        try:
            worker_groups = await client.get_worker_groups()
            print(f"📊 Total worker groups found: {len(worker_groups)}")
            print()

            if not worker_groups:
                print("❌ No worker groups found!")
                return

            for i, group in enumerate(worker_groups, 1):
                print(f"🔧 Worker Group {i}: {group.get('name', group.get('id', 'Unknown'))}")
                print(f"   ID: {group.get('id', 'Unknown')}")
                print(f"   onPrem: {group.get('onPrem', 'NOT_SET')}")
                print(f"   provisioned: {group.get('provisioned', 'NOT_SET')}")
                print(f"   isFleet: {group.get('isFleet', 'NOT_SET')}")
                print(f"   isSearch: {group.get('isSearch', 'NOT_SET')}")
                print(f"   workerCount: {group.get('workerCount', 'NOT_SET')}")

                group_type = client.get_worker_group_type(group)
                print(f"   🏷️  Detected Type: {group_type}")

                all_keys = list(group.keys())
                print(f"   📋 All fields: {', '.join(all_keys)}")
                print()

            groups_by_type = await client.get_worker_groups_by_type()
            print("📈 Worker Groups by Type:")
            for group_type, groups in groups_by_type.items():
                count = len(groups)
                if count > 0:
                    names = [g.get("name", g.get("id", "Unknown")) for g in groups]
                    print(f"   {group_type}: {count} ({', '.join(names)})")
                else:
                    print(f"   {group_type}: {count}")
            print()

            if worker_groups:
                print("🔍 Raw JSON for first worker group:")
                print(json.dumps(worker_groups[0], indent=2))

        except Exception as e:
            print(f"❌ Error: {e}")
            raise


if __name__ == "__main__":
    if len(sys.argv) == 1:
        deployments = list_available_deployments()
        if deployments:
            print("\nUsage:")
            print("  python debug_worker_groups.py <deployment_name>")
            print("  python debug_worker_groups.py <CRIBL_URL> <API_TOKEN>")
            print(f"\nExample: python debug_worker_groups.py {deployments[0]}")
        sys.exit(1)
    elif len(sys.argv) == 2:
        deployment_name = sys.argv[1]
        try:
            asyncio.run(debug_worker_groups(deployment_name=deployment_name))
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        except Exception as e:
            print(f"\n❌ Failed: {e}")
            sys.exit(1)
    elif len(sys.argv) == 3:
        url = sys.argv[1]
        token = sys.argv[2]
        try:
            asyncio.run(debug_worker_groups(url=url, token=token))
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        except Exception as e:
            print(f"\n❌ Failed: {e}")
            sys.exit(1)
    else:
        print("Usage: python debug_worker_groups.py <deployment_name>")
        print("   OR: python debug_worker_groups.py <CRIBL_URL> <API_TOKEN>")
        sys.exit(1)

    url = sys.argv[1]
    token = sys.argv[2]

    try:
        asyncio.run(debug_worker_groups(url, token))
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        sys.exit(1)
