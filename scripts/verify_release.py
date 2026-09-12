"""Verify the published release against its SHA-256 manifest."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trade_shock.provenance import load_release_manifest, verify_release_manifest  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify release files and source provenance")
    parser.add_argument(
        "--include-sources",
        action="store_true",
        help="Also verify locally archived raw inputs (not distributed in Git)",
    )
    args = parser.parse_args(argv)
    manifest = load_release_manifest(ROOT / "data" / "processed" / "release_manifest.json")
    result = verify_release_manifest(ROOT, manifest, include_sources=args.include_sources)
    print(json.dumps({"status": "passed", **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
