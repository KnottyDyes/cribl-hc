#!/usr/bin/env python3
import asyncio
import sys
import json

sys.path.insert(0, "src")

from cribl_hc.core.api_client import CriblAPIClient
from cribl_hc.cli.commands.config import load_credentials


async def debug_worker_details():
    """Debug worker details to understand group assignments."""

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

    print(f"Debugging worker group assignments: {url}")

    try:
        async with CriblAPIClient(url, token) as client:
            workers = await client.get_workers()

            print(f"\n=== WORKER DETAILS ===")
            print(f"Total workers: {len(workers)}")

            for i, worker in enumerate(workers):
                worker_id = worker.get("id", "unknown")
                hostname = worker.get("hostname", "unknown")
                group = worker.get("group", "default")
                status = worker.get("status", "unknown")

                print(f"\nWorker {i + 1}:")
                print(f"  ID: {worker_id}")
                print(f"  Hostname: {hostname}")
                print(f"  Group: {group}")
                print(f"  Status: {status}")

            groups = {}
            for worker in workers:
                group = worker.get("group", "default")
                if group not in groups:
                    groups[group] = []
                groups[group].append(worker.get("hostname", "unknown"))

            print(f"\n=== GROUP SUMMARY ===")
            for group_name, hostnames in groups.items():
                print(f"Group '{group_name}': {len(hostnames)} workers")
                for hostname in hostnames:
                    print(f"  - {hostname}")

    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(debug_worker_details())
