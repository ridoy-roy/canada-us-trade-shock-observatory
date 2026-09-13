from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trade_shock.census import CensusClient, parse_api_payload  # noqa: E402
from trade_shock.chart import write_pilot_chart  # noqa: E402
from trade_shock.cli import _local_api_key  # noqa: E402
from trade_shock.harmonize import load_core_ranges  # noqa: E402
from trade_shock.hs6_panel import (  # noqa: E402
    build_hs6_panel,
    summarize_monthly,
    summarize_product_changes,
    validate_release,
)
from trade_shock.io_utils import write_dict_rows_csv, write_text_lf  # noqa: E402
from trade_shock.release import write_monthly_chart, write_product_decline_chart, write_release_report  # noqa: E402
from trade_shock.provenance import (  # noqa: E402
    load_release_manifest,
    resolve_manifest_pilot_sources,
    resolve_manifest_sources,
    write_release_manifest,
)
from trade_shock.panel import build_panel  # noqa: E402
from trade_shock.validate import validate_panel  # noqa: E402
from trade_shock.universe import (  # noqa: E402
    ensure_commodity_concordance,
    parse_commodity_concordance,
    write_concordance_metadata,
)


MONTHS = [f"{year}-{month:02d}" for year in (2024, 2025) for month in range(1, 13)]
PREFIXES = ("720", "721", "722", "730")
PILOT_HTS10 = "7208101500"


def write_csv(rows, path):
    write_dict_rows_csv(rows, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the professional V0 analytical release")
    parser.add_argument("--months", nargs="+", default=MONTHS)
    parser.add_argument(
        "--reuse-snapshots",
        action="store_true",
        help="Rebuild from exact manifest-pinned local sources without network calls",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "processed" / "release_manifest.json",
        help="Release manifest used for exact local rebuilds",
    )
    args = parser.parse_args(argv)
    ranges = load_core_ranges(ROOT / "config" / "core_steel_hs6_ranges.csv")
    pinned_snapshots = None
    pinned_pilot_snapshots = None
    pilot_months = [month for month in args.months if month.startswith("2025-")]
    if args.reuse_snapshots:
        manifest = load_release_manifest(args.manifest)
        concordance, pinned_snapshots = resolve_manifest_sources(
            ROOT, manifest, args.months, PREFIXES
        )
        pinned_pilot_snapshots = resolve_manifest_pilot_sources(
            ROOT, manifest, pilot_months, PILOT_HTS10
        )
    else:
        concordance = ensure_commodity_concordance(ROOT / "data" / "raw" / "usitc_hts")
    universe = parse_commodity_concordance(concordance, ranges)
    write_concordance_metadata(concordance, concordance.with_suffix(".metadata.json"))
    write_csv(universe, ROOT / "data" / "processed" / "core_steel_product_universe_2025.csv")

    client = CensusClient(_local_api_key(), ROOT / "data" / "raw")
    rows = []
    snapshots: list[dict[str, str]] = []
    total = len(args.months) * len(PREFIXES)
    completed = 0
    for month in args.months:
        if args.reuse_snapshots:
            for prefix in PREFIXES:
                match = next(
                    item for item in pinned_snapshots
                    if item["month"] == month and item["prefix"] == prefix
                )
                path = Path(match["path"])
                rows.extend(parse_api_payload(path.read_bytes()))
                snapshots.append(match)
                completed += 1
        else:
            with ThreadPoolExecutor(max_workers=len(PREFIXES)) as executor:
                futures = {
                    executor.submit(client.fetch_hs6_prefix, month, prefix): prefix
                    for prefix in PREFIXES
                }
                for future in as_completed(futures):
                    prefix = futures[future]
                    fetched, snapshot = future.result()
                    rows.extend(fetched)
                    snapshots.append({"month": month, "prefix": prefix, "path": str(snapshot.data_path)})
                    completed += 1
                    print(f"Fetched {completed}/{total}: {month} HS6 {prefix}*", flush=True)
    pilot_rows = []
    pilot_snapshots: list[dict[str, str]] = []
    if args.reuse_snapshots:
        for item in pinned_pilot_snapshots:
            path = Path(item["path"])
            pilot_rows.extend(parse_api_payload(path.read_bytes()))
            pilot_snapshots.append(item)
    else:
        for month in pilot_months:
            fetched, snapshot = client.fetch_month(month, PILOT_HTS10)
            pilot_rows.extend(fetched)
            pilot_snapshots.append(
                {"month": month, "hts10": PILOT_HTS10, "path": str(snapshot.data_path)}
            )
            print(f"Fetched pilot {month}: HTS10 {PILOT_HTS10}", flush=True)
    pilot_panel = build_panel(pilot_rows, ranges)
    for row in pilot_panel:
        row["data_status"] = "official_census_api"
    pilot_validation = validate_panel(pilot_panel, pilot_months, [PILOT_HTS10])
    pilot_validation.update(
        {
            "source_mode": "manifest_pinned_api_snapshot" if args.reuse_snapshots else "api",
            "raw_snapshot_count": len(pilot_snapshots),
            "raw_snapshots": [
                Path(item["path"]).resolve().relative_to(ROOT.resolve()).as_posix()
                for item in pilot_snapshots
            ],
        }
    )
    panel = build_hs6_panel(rows, ranges)
    summary = summarize_monthly(panel)
    product_changes = summarize_product_changes(panel)
    validation = validate_release(panel, summary, args.months)
    validation.update({
        "core_raw_snapshot_count": len(snapshots),
        "pilot_raw_snapshot_count": len(pilot_snapshots),
        "raw_snapshot_count": len(snapshots) + len(pilot_snapshots),
        "product_universe_hts10_count": len(universe),
        "product_universe_hs6_count": len({row["hs6"] for row in universe}),
    })
    write_csv(panel, ROOT / "data" / "processed" / "core_steel_hs6_monthly_panel.csv")
    write_csv(summary, ROOT / "data" / "processed" / "core_steel_monthly_summary.csv")
    write_csv(product_changes, ROOT / "data" / "processed" / "top_10_hs6_decline_contributors.csv")
    write_text_lf(
        ROOT / "data" / "processed" / "release_validation_report.json",
        json.dumps(validation, indent=2) + "\n",
    )
    write_csv(pilot_panel, ROOT / "data" / "processed" / "trade_policy_panel.csv")
    write_text_lf(
        ROOT / "data" / "processed" / "validation_report.json",
        json.dumps(pilot_validation, indent=2) + "\n",
    )
    write_pilot_chart(
        pilot_panel,
        ROOT / "artifacts" / f"pilot_{PILOT_HTS10}_monthly.svg",
        PILOT_HTS10,
    )
    write_monthly_chart(summary, ROOT / "artifacts" / "core_steel_2024_2025_monthly.svg")
    write_product_decline_chart(product_changes, ROOT / "artifacts" / "top_10_hs6_decline_contributors.svg")
    write_release_report(universe, panel, summary, product_changes, validation, ROOT / "reports" / "v0_release_report.md")
    generated_outputs = [
        ROOT / "data" / "processed" / "core_steel_product_universe_2025.csv",
        ROOT / "data" / "processed" / "core_steel_hs6_monthly_panel.csv",
        ROOT / "data" / "processed" / "core_steel_monthly_summary.csv",
        ROOT / "data" / "processed" / "top_10_hs6_decline_contributors.csv",
        ROOT / "data" / "processed" / "release_validation_report.json",
        ROOT / "data" / "processed" / "trade_policy_panel.csv",
        ROOT / "data" / "processed" / "validation_report.json",
        ROOT / "artifacts" / "core_steel_2024_2025_monthly.svg",
        ROOT / "artifacts" / "top_10_hs6_decline_contributors.svg",
        ROOT / "artifacts" / f"pilot_{PILOT_HTS10}_monthly.svg",
        ROOT / "reports" / "v0_release_report.md",
        ROOT / "reports" / "annual_summary.json",
    ]
    write_release_manifest(
        ROOT,
        ROOT / "data" / "processed" / "release_manifest.json",
        args.months,
        PREFIXES,
        snapshots,
        concordance,
        generated_outputs,
        pilot_snapshots,
    )
    print(json.dumps(validation, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
