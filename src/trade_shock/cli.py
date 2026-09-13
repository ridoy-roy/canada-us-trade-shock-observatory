"""Command-line build for the V0 pilot panel."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .census import CensusClient, CensusError, load_fixture
from .chart import write_pilot_chart
from .harmonize import load_core_ranges, normalize_hts10
from .io_utils import write_dict_rows_csv, write_text_lf
from .panel import build_panel
from .validate import ValidationError, validate_panel


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MONTHS = [f"2025-{month:02d}" for month in range(1, 13)]


def _local_api_key() -> str | None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == "CENSUS_API_KEY":
            return value.strip().strip('"').strip("'") or None
    return None


def _write_csv(rows: list[dict[str, object]], path: Path) -> None:
    write_dict_rows_csv(rows, path)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--pilot-hts10", default="7208101500")
    result.add_argument("--months", nargs="+", default=DEFAULT_MONTHS)
    result.add_argument("--source", choices=("api", "fixture"), default="api")
    result.add_argument("--api-key", help="Defaults to CENSUS_API_KEY")
    result.add_argument("--raw-root", type=Path, default=ROOT / "data" / "raw")
    result.add_argument("--output-dir", type=Path, default=ROOT / "data" / "processed")
    result.add_argument("--artifact-dir", type=Path, default=ROOT / "artifacts")
    result.add_argument("--fixture-dir", type=Path, default=ROOT / "tests" / "fixtures" / "census")
    return result


def run(args: argparse.Namespace) -> dict[str, Path]:
    hts10 = normalize_hts10(args.pilot_hts10)
    ranges = load_core_ranges(ROOT / "config" / "core_steel_hs6_ranges.csv")
    source_rows: list[dict[str, str]] = []
    snapshots: list[str] = []
    if args.source == "api":
        client = CensusClient(args.api_key or _local_api_key(), args.raw_root)
        for month in args.months:
            rows, snapshot = client.fetch_month(month, hts10)
            source_rows.extend(rows)
            try:
                snapshot_path = snapshot.data_path.relative_to(ROOT)
            except ValueError:
                snapshot_path = snapshot.data_path
            snapshots.append(snapshot_path.as_posix())
    else:
        for month in args.months:
            source_rows.extend(load_fixture(args.fixture_dir / f"{month}-{hts10}.json"))
    panel = build_panel(source_rows, ranges)
    data_status = "official_census_api" if args.source == "api" else "contract_fixture_not_observed"
    for row in panel:
        row["data_status"] = data_status
    report = validate_panel(panel, args.months, [hts10])
    report.update({"source_mode": args.source, "raw_snapshots": snapshots})
    panel_path = args.output_dir / "trade_policy_panel.csv"
    report_path = args.output_dir / "validation_report.json"
    chart_path = args.artifact_dir / f"pilot_{hts10}_monthly.svg"
    _write_csv(panel, panel_path)
    write_text_lf(report_path, json.dumps(report, indent=2) + "\n")
    write_pilot_chart(panel, chart_path, hts10)
    return {"panel": panel_path, "validation": report_path, "chart": chart_path}


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        outputs = run(args)
    except (CensusError, ValidationError, FileNotFoundError, ValueError) as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    for label, path in outputs.items():
        print(f"{label}: {path}")
    if args.source == "fixture":
        print("NOTE: outputs use contract-test fixtures, not publishable observations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
