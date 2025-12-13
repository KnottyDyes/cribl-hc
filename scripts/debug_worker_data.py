#!/usr/bin/env python3
"""Debug script to inspect worker data structure from Cribl Cloud."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cribl_hc.core.api_client import CriblAPIClient


async def main():
    import os

    url = os.environ.get("CRIBL_URL")
    token = os.environ.get("CRIBL_TOKEN")

    if not url or not token:
        print("Please set CRIBL_URL and CRIBL_TOKEN environment variables")
        sys.exit(1)

    async with CriblAPIClient(base_url=url, auth_token=token) as client:
        print("Fetching workers...")
        workers = await client.get_workers()

        print(f"\nFound {len(workers)} workers\n")
        print("=" * 80)

        for i, worker in enumerate(workers, 1):
            print(f"\n[Worker {i}/{len(workers)}]")
            print(json.dumps(worker, indent=2))
            print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
