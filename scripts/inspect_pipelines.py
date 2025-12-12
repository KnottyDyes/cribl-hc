#!/usr/bin/env python3
"""
Inspect pipeline data from real Cribl Cloud deployment.
"""

import asyncio
import sys
import json
import httpx


async def inspect_pipelines(base_url: str, token: str):
    """Fetch and inspect pipeline data."""

    base_url = base_url.rstrip("/")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # Fetch pipelines
        print("Fetching pipelines from /api/v1/m/default/pipelines...\n")

        response = await client.get(f"{base_url}/api/v1/m/default/pipelines")

        if response.status_code == 200:
            data = response.json()
            pipelines = data.get("items", [])

            print(f"Found {len(pipelines)} pipelines\n")
            print("=" * 80)

            # Inspect each pipeline structure
            for i, pipeline in enumerate(pipelines[:5], 1):  # Show first 5
                print(f"\nPipeline {i}: {pipeline.get('id', 'NO-ID')}")
                print("-" * 80)

                # Show all keys
                print(f"Keys: {list(pipeline.keys())}")

                # Check for 'functions' field
                if 'functions' in pipeline:
                    functions = pipeline['functions']
                    print(f"✓ Has 'functions' field (type: {type(functions).__name__})")
                    if isinstance(functions, list):
                        print(f"  Functions count: {len(functions)}")
                        if functions:
                            print(f"  First function: {functions[0]}")
                    else:
                        print(f"  Functions value: {functions}")
                else:
                    print(f"✗ Missing 'functions' field")

                # Show full structure (truncated)
                pipeline_json = json.dumps(pipeline, indent=2)
                if len(pipeline_json) > 500:
                    print(f"\nFull structure (truncated):")
                    print(pipeline_json[:500] + "\n... (truncated)")
                else:
                    print(f"\nFull structure:")
                    print(pipeline_json)

                print("=" * 80)

            # Show statistics
            print("\n\nPipeline Statistics:")
            print("-" * 80)

            has_functions = [p for p in pipelines if 'functions' in p]
            missing_functions = [p for p in pipelines if 'functions' not in p]

            print(f"Total pipelines: {len(pipelines)}")
            print(f"With 'functions' field: {len(has_functions)}")
            print(f"WITHOUT 'functions' field: {len(missing_functions)}")

            if missing_functions:
                print(f"\nPipelines missing 'functions':")
                for p in missing_functions[:10]:  # Show first 10
                    print(f"  - {p.get('id', 'NO-ID')}")
                    print(f"    Keys: {list(p.keys())}")

        else:
            print(f"Failed: HTTP {response.status_code}")
            print(response.text)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python inspect_pipelines.py <URL> <TOKEN>")
        sys.exit(1)

    url = sys.argv[1]
    token = sys.argv[2]

    asyncio.run(inspect_pipelines(url, token))
