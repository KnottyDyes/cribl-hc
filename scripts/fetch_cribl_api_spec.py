#!/usr/bin/env python3
"""
Download the Cribl OpenAPI reference spec used for analyzer research.

Cribl publishes one combined spec per release (Stream, Edge, Lake, Search and
Core all live in the same file) at:

    https://cdn.cribl.io/dl/<version>/cribl-apidocs-<version>-<hash>.yml

The build hash is not derivable from the version, so it is discovered from the
public API Reference page, which links every published release.

The specs are several megabytes each and are deliberately not committed; they
land in ``cribl_api_reference/``, which is gitignored.

Usage:
    scripts/fetch_cribl_api_spec.py --list
    scripts/fetch_cribl_api_spec.py                 # newest release
    scripts/fetch_cribl_api_spec.py --version 4.19.2
    scripts/fetch_cribl_api_spec.py --version 4.15.1 --version 4.20.0
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

INDEX_URL = "https://docs.cribl.io/cribl-as-code/api-reference/control-plane/cribl-core/"
SPEC_URL_RE = re.compile(
    r"https://cdn\.cribl\.io/dl/(?P<version>\d+\.\d+\.\d+)/"
    r"cribl-apidocs-(?P=version)-[0-9a-f]+\.yml"
)
DEST_DIR = Path(__file__).resolve().parent.parent / "cribl_api_reference"
USER_AGENT = "cribl-hc-spec-fetcher"


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def discover_specs() -> dict[str, str]:
    """Map each published version to its spec URL, newest last."""
    page = _get(INDEX_URL).decode("utf-8", errors="replace")
    specs = {match.group("version"): match.group(0) for match in SPEC_URL_RE.finditer(page)}
    if not specs:
        raise SystemExit(
            f"No spec URLs found at {INDEX_URL}.\n"
            "The docs page layout may have changed; check the URL by hand."
        )
    return dict(sorted(specs.items(), key=lambda item: version_key(item[0])))


def download(version: str, url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / f"cribl-apidocs-{version}.yml"
    if target.exists():
        print(f"  {version}: already present at {target.relative_to(Path.cwd())}")
        return target
    print(f"  {version}: downloading {url}")
    target.write_bytes(_get(url))
    print(f"  {version}: wrote {target.stat().st_size / 1_048_576:.1f} MB to {target}")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--version",
        action="append",
        dest="versions",
        metavar="X.Y.Z",
        help="release to fetch; repeatable. Defaults to the newest published release.",
    )
    parser.add_argument("--list", action="store_true", help="list published releases and exit")
    parser.add_argument(
        "--dest", type=Path, default=DEST_DIR, help=f"output directory (default: {DEST_DIR})"
    )
    args = parser.parse_args(argv)

    specs = discover_specs()

    if args.list:
        print(f"{len(specs)} published Cribl API specs:")
        for version in specs:
            print(f"  {version}")
        return 0

    wanted = args.versions or [max(specs, key=version_key)]

    unknown = [v for v in wanted if v not in specs]
    if unknown:
        print(f"Unknown version(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"Run with --list to see the {len(specs)} published releases.", file=sys.stderr)
        return 1

    print(f"Fetching {len(wanted)} spec(s) into {args.dest}")
    for version in sorted(wanted, key=version_key):
        download(version, specs[version], args.dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
