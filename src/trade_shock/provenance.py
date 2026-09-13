"""Release provenance, content hashes, and manifest-pinned input loading."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .io_utils import write_text_lf


MANIFEST_SCHEMA_VERSION = 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def write_release_manifest(
    root: Path,
    output: Path,
    months: list[str],
    prefixes: tuple[str, ...],
    snapshots: list[dict[str, str]],
    concordance: Path,
    generated_outputs: list[Path],
    pilot_snapshots: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Record the exact files used for a release without embedding credentials."""
    snapshot_entries = []
    for item in sorted(snapshots, key=lambda row: (row["month"], row["prefix"])):
        path = Path(item["path"])
        snapshot_entries.append(
            {
                "month": item["month"],
                "prefix": item["prefix"],
                "path": _relative(path, root),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    pilot_entries = []
    for item in sorted(pilot_snapshots or [], key=lambda row: (row["month"], row["hts10"])):
        path = Path(item["path"])
        pilot_entries.append(
            {
                "month": item["month"],
                "hts10": item["hts10"],
                "path": _relative(path, root),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    inputs = [
        root / "config" / "core_steel_hs6_ranges.csv",
        root / "config" / "policy_history.csv",
    ]
    manifest: dict[str, object] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "release": "v0",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scope": {
            "country_code": "1220",
            "months": months,
            "hs6_prefixes": list(prefixes),
            "pilot_hts10": "7208101500",
            "product_scope": "section232_core_steel",
        },
        "source_data": {
            "census_api": {
                "endpoint": "https://api.census.gov/data/timeseries/intltrade/imports/hs",
                "snapshots": snapshot_entries,
                "pilot_snapshots": pilot_entries,
            },
            "commodity_concordance": {
                "source_url": "https://www.census.gov/trade/downloads/concordance/comm_month/2025/CONCCOMM2501.ZIP",
                "path": _relative(concordance, root),
                "sha256": sha256_file(concordance),
                "bytes": concordance.stat().st_size,
            },
        },
        "configuration": [
            {"path": _relative(path, root), "sha256": sha256_file(path)} for path in inputs
        ],
        "outputs": [
            {
                "path": _relative(path, root),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in generated_outputs
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    write_text_lf(output, json.dumps(manifest, indent=2) + "\n")
    return manifest


def load_release_manifest(path: Path) -> dict[str, object]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"release manifest not found at {path}; run a fresh build first"
        ) from exc
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError("unsupported release manifest schema")
    return manifest


def verify_manifest_file(root: Path, entry: dict[str, object]) -> Path:
    path = root / str(entry["path"])
    if not path.is_file():
        raise FileNotFoundError(f"manifest-pinned source is unavailable locally: {path}")
    actual = sha256_file(path)
    if actual != entry["sha256"]:
        raise ValueError(f"manifest hash mismatch for {path}: {actual}")
    return path


def resolve_manifest_sources(
    root: Path,
    manifest: dict[str, object],
    months: list[str],
    prefixes: tuple[str, ...],
) -> tuple[Path, list[dict[str, str]]]:
    source_data = manifest["source_data"]
    concordance = verify_manifest_file(root, source_data["commodity_concordance"])
    entries = source_data["census_api"]["snapshots"]
    keyed = {(entry["month"], entry["prefix"]): entry for entry in entries}
    expected = {(month, prefix) for month in months for prefix in prefixes}
    missing = sorted(expected - set(keyed))
    if missing:
        raise ValueError(f"release manifest is missing requested Census inputs: {missing[:5]}")
    resolved = []
    for month, prefix in sorted(expected):
        entry = keyed[(month, prefix)]
        path = verify_manifest_file(root, entry)
        resolved.append({"month": month, "prefix": prefix, "path": str(path)})
    return concordance, resolved


def resolve_manifest_pilot_sources(
    root: Path,
    manifest: dict[str, object],
    months: list[str],
    hts10: str,
) -> list[dict[str, str]]:
    entries = manifest["source_data"]["census_api"].get("pilot_snapshots", [])
    keyed = {(entry["month"], entry["hts10"]): entry for entry in entries}
    expected = {(month, hts10) for month in months}
    missing = sorted(expected - set(keyed))
    if missing:
        raise ValueError(f"release manifest is missing requested pilot inputs: {missing[:5]}")
    resolved = []
    for month, code in sorted(expected):
        entry = keyed[(month, code)]
        path = verify_manifest_file(root, entry)
        resolved.append({"month": month, "hts10": code, "path": str(path)})
    return resolved


def verify_release_manifest(
    root: Path, manifest: dict[str, object], include_sources: bool = False
) -> dict[str, int]:
    """Verify committed release products and, optionally, locally archived sources."""
    checked_outputs = 0
    for entry in manifest["configuration"]:
        verify_manifest_file(root, entry)
        checked_outputs += 1
    for entry in manifest["outputs"]:
        verify_manifest_file(root, entry)
        checked_outputs += 1
    checked_sources = 0
    if include_sources:
        source_data = manifest["source_data"]
        verify_manifest_file(root, source_data["commodity_concordance"])
        checked_sources += 1
        for entry in source_data["census_api"]["snapshots"]:
            verify_manifest_file(root, entry)
            checked_sources += 1
        for entry in source_data["census_api"].get("pilot_snapshots", []):
            verify_manifest_file(root, entry)
            checked_sources += 1
    return {"verified_release_files": checked_outputs, "verified_source_files": checked_sources}
