from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trade_shock.census import CensusClient, parse_api_payload  # noqa: E402
from trade_shock.cli import _local_api_key  # noqa: E402
from trade_shock.harmonize import load_core_ranges  # noqa: E402
from trade_shock.hs6_panel import (  # noqa: E402
    build_hs6_panel,
    summarize_monthly,
    summarize_product_changes,
    validate_release,
)
from trade_shock.release import write_monthly_chart, write_product_decline_chart, write_release_report  # noqa: E402
from trade_shock.universe import parse_commodity_concordance, write_concordance_metadata  # noqa: E402


MONTHS = [f"{year}-{month:02d}" for year in (2024, 2025) for month in range(1, 13)]
PREFIXES = ("720", "721", "722", "730")


def write_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the professional V0 analytical release")
    parser.add_argument("--months", nargs="+", default=MONTHS)
    parser.add_argument("--reuse-snapshots", action="store_true", help="Rebuild without network calls")
    args = parser.parse_args(argv)
    ranges = load_core_ranges(ROOT / "config" / "core_steel_hs6_ranges.csv")
    concordance = ROOT / "data" / "raw" / "usitc_hts" / "CONCCOMM2501.ZIP"
    universe = parse_commodity_concordance(concordance, ranges)
    write_concordance_metadata(concordance, concordance.with_suffix(".metadata.json"))
    write_csv(universe, ROOT / "data" / "processed" / "core_steel_product_universe_2025.csv")

    client = CensusClient(_local_api_key(), ROOT / "data" / "raw")
    rows = []
    snapshots = []
    total = len(args.months) * len(PREFIXES)
    completed = 0
    for month in args.months:
        if args.reuse_snapshots:
            for prefix in PREFIXES:
                matches = [
                    path
                    for path in (ROOT / "data" / "raw" / "census_imports_hs" / month).glob(f"hs6-{prefix}star-*.json")
                    if not path.name.endswith(".metadata.json")
                ]
                if len(matches) != 1:
                    raise ValueError(f"expected one snapshot for {month} {prefix}*, found {len(matches)}")
                rows.extend(parse_api_payload(matches[0].read_bytes()))
                snapshots.append(str(matches[0]))
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
                    snapshots.append(str(snapshot.data_path))
                    completed += 1
                    print(f"Fetched {completed}/{total}: {month} HS6 {prefix}*", flush=True)
    panel = build_hs6_panel(rows, ranges)
    summary = summarize_monthly(panel)
    product_changes = summarize_product_changes(panel)
    validation = validate_release(panel, summary, args.months)
    validation.update({
        "raw_snapshot_count": len(snapshots),
        "product_universe_hts10_count": len(universe),
        "product_universe_hs6_count": len({row["hs6"] for row in universe}),
    })
    write_csv(panel, ROOT / "data" / "processed" / "core_steel_hs6_monthly_panel.csv")
    write_csv(summary, ROOT / "data" / "processed" / "core_steel_monthly_summary.csv")
    write_csv(product_changes, ROOT / "data" / "processed" / "top_10_hs6_decline_contributors.csv")
    (ROOT / "data" / "processed" / "release_validation_report.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )
    write_monthly_chart(summary, ROOT / "artifacts" / "core_steel_2024_2025_monthly.svg")
    write_product_decline_chart(product_changes, ROOT / "artifacts" / "top_10_hs6_decline_contributors.svg")
    write_release_report(universe, panel, summary, product_changes, validation, ROOT / "reports" / "v0_release_report.md")
    print(json.dumps(validation, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
