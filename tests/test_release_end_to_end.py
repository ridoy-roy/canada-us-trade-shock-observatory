import csv
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import scripts.build_release as build_release
from trade_shock.census import FIELDS
from trade_shock.provenance import write_release_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _concordance_record(hts10):
    return (
        "2" + hts10 + "  " + "STEEL PRODUCT".ljust(150) + " "
        + "STEEL".ljust(50) + " " + "KG " + " " + "   " + " "
        + "67321" + " " + "14100" + "     " + "331110" + "1" + "00"
    )


def _api_payload(
    year, month, code, value, duty, quantity_unit="-", quantity=0, include_detail=False
):
    row = {
        "I_COMMODITY": code,
        "I_COMMODITY_LDESC": "STEEL PRODUCT",
        "CTY_CODE": "1220",
        "CTY_NAME": "CANADA",
        "YEAR": str(year),
        "MONTH": f"{month:02d}",
        "UNIT_QY1": quantity_unit,
        "CON_VAL_MO": str(value),
        "CON_QY1_MO": str(quantity),
        "DUT_VAL_MO": str(value),
        "CAL_DUT_MO": str(duty),
        "RP": "-",
        "LAST_UPDATE": "2026-01-01",
    }
    rows = [[row[field] for field in FIELDS]]
    if include_detail:
        detail = {**row, "RP": "10"}
        rows.append([detail[field] for field in FIELDS])
    return json.dumps([list(FIELDS), *rows]).encode()


class ReleaseEndToEndTests(unittest.TestCase):
    def test_manifest_pinned_offline_build_writes_valid_release(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(PROJECT_ROOT / "config", root / "config")
            concordance = root / "data" / "raw" / "usitc_hts" / "CONCCOMM2501.ZIP"
            concordance.parent.mkdir(parents=True)
            codes = {"720": "7208100000", "721": "7210490000", "722": "7225300000", "730": "7306610000"}
            with zipfile.ZipFile(concordance, "w") as bundle:
                bundle.writestr("CONCORD.TXT", "\n".join(_concordance_record(code) for code in codes.values()))
            snapshots = []
            pilot_snapshots = []
            months = [f"{year}-{month:02d}" for year in (2024, 2025) for month in range(1, 13)]
            for period in months:
                year, month = map(int, period.split("-"))
                for prefix, hts10 in codes.items():
                    code = hts10[:6]
                    value = 1000 if year == 2024 else 700
                    duty = 0 if year == 2024 or month < 3 else 175
                    path = root / "data" / "raw" / "census_imports_hs" / period / f"hs6-{prefix}star-fixture.json"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(_api_payload(year, month, code, value, duty))
                    snapshots.append({"month": period, "prefix": prefix, "path": str(path)})
                if year == 2025:
                    pilot_path = root / "data" / "raw" / "census_imports_hs" / period / "7208101500-fixture.json"
                    pilot_path.write_bytes(
                        _api_payload(
                            year, month, "7208101500", 100, duty, "KG", 200,
                            include_detail=True,
                        )
                    )
                    pilot_snapshots.append(
                        {"month": period, "hts10": "7208101500", "path": str(pilot_path)}
                    )
            manifest_path = root / "data" / "processed" / "release_manifest.json"
            write_release_manifest(
                root, manifest_path, months, build_release.PREFIXES, snapshots,
                concordance, [], pilot_snapshots,
            )

            with patch.object(build_release, "ROOT", root):
                result = build_release.main(["--reuse-snapshots", "--manifest", str(manifest_path)])

            self.assertEqual(result, 0)
            validation = json.loads((root / "data" / "processed" / "release_validation_report.json").read_text())
            self.assertEqual(validation["status"], "passed")
            self.assertEqual(validation["raw_snapshot_count"], 108)
            with (root / "data" / "processed" / "core_steel_monthly_summary.csv").open(newline="") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 24)
            final_manifest = json.loads(manifest_path.read_text())
            self.assertEqual(len(final_manifest["source_data"]["census_api"]["snapshots"]), 96)
            self.assertEqual(len(final_manifest["source_data"]["census_api"]["pilot_snapshots"]), 12)
            self.assertGreater(len(final_manifest["outputs"]), 0)


if __name__ == "__main__":
    unittest.main()
