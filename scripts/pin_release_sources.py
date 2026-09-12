"""Create the first manifest for an already archived set of raw release inputs."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trade_shock.provenance import write_release_manifest  # noqa: E402
from trade_shock.universe import ensure_commodity_concordance  # noqa: E402


MONTHS = [f"{year}-{month:02d}" for year in (2024, 2025) for month in range(1, 13)]
PREFIXES = ("720", "721", "722", "730")
PILOT_HTS10 = "7208101500"


def main() -> int:
    snapshots = []
    for month in MONTHS:
        for prefix in PREFIXES:
            matches = [
                path
                for path in (ROOT / "data" / "raw" / "census_imports_hs" / month).glob(
                    f"hs6-{prefix}star-*.json"
                )
                if not path.name.endswith(".metadata.json")
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"cannot safely adopt {month} {prefix}*: expected one snapshot, found {len(matches)}"
                )
            snapshots.append({"month": month, "prefix": prefix, "path": str(matches[0])})
    concordance = ensure_commodity_concordance(ROOT / "data" / "raw" / "usitc_hts")
    pilot_snapshots = []
    for month in [period for period in MONTHS if period.startswith("2025-")]:
        matches = [
            path
            for path in (ROOT / "data" / "raw" / "census_imports_hs" / month).glob(
                f"{PILOT_HTS10}-*.json"
            )
            if not path.name.endswith(".metadata.json")
        ]
        if len(matches) != 1:
            raise ValueError(
                f"cannot safely adopt {month} {PILOT_HTS10}: expected one snapshot, found {len(matches)}"
            )
        pilot_snapshots.append(
            {"month": month, "hts10": PILOT_HTS10, "path": str(matches[0])}
        )
    output = ROOT / "data" / "processed" / "release_manifest.json"
    write_release_manifest(
        ROOT, output, MONTHS, PREFIXES, snapshots, concordance, [], pilot_snapshots
    )
    print(f"Pinned {len(snapshots) + len(pilot_snapshots)} Census snapshots in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
