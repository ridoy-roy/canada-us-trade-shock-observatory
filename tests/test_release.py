import tempfile
import unittest
import zipfile
from pathlib import Path

from trade_shock.hs6_panel import build_hs6_panel, summarize_monthly, summarize_product_changes, validate_release
from trade_shock.harmonize import load_core_ranges
from trade_shock.universe import parse_commodity_concordance


ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.ranges = load_core_ranges(ROOT / "config" / "core_steel_hs6_ranges.csv")

    def row(self, year="2025", month="05", code="720810", value="100", qty="200", duty="25"):
        return {
            "I_COMMODITY": code, "I_COMMODITY_LDESC": "steel", "CTY_CODE": "1220",
            "CTY_NAME": "CANADA", "YEAR": year, "MONTH": month, "UNIT_QY1": "KG",
            "CON_VAL_MO": value, "CON_QY1_MO": qty, "DUT_VAL_MO": value,
            "CAL_DUT_MO": duty, "RP": "-", "LAST_UPDATE": "0",
        }

    def test_hs6_panel_and_summary(self):
        panel = build_hs6_panel([self.row()], self.ranges)
        summary = summarize_monthly(panel)
        report = validate_release(panel, summary, ["2025-05"])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(summary[0]["quantity_kg"], 200)

    def test_suppressed_hs6_quantity_is_null(self):
        source = self.row()
        source["UNIT_QY1"] = "-"
        source["CON_QY1_MO"] = "0"
        panel = build_hs6_panel([source], self.ranges)
        summary = summarize_monthly(panel)
        self.assertIsNone(panel[0]["quantity_1"])
        self.assertIsNone(summary[0]["quantity_kg"])

    def test_product_change_ranking(self):
        panel = build_hs6_panel([
            self.row(year="2024", code="720810", value="300"),
            self.row(year="2025", code="720810", value="100"),
            self.row(year="2024", code="720825", value="200"),
            self.row(year="2025", code="720825", value="150"),
        ], self.ranges)
        ranked = summarize_product_changes(panel, limit=2)
        self.assertEqual(ranked[0]["hs6"], "720810")
        self.assertEqual(ranked[0]["product_name"], "Steel")
        self.assertEqual(ranked[0]["change_usd"], -200)
        self.assertAlmostEqual(ranked[0]["share_of_total_decline_pct"], 80.0)

    def test_concordance_import_record(self):
        record = "2" + "7208101500" + "  " + "PILOT".ljust(150) + " " + "SHORT".ljust(50) + " " + "KG " + " " + "   " + " " + "67321" + " " + "14100" + "     " + "331110" + "1" + "00"
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "concordance.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("CONCORD.TXT", record)
            rows = parse_commodity_concordance(archive, self.ranges)
        self.assertEqual(rows[0]["hts10"], "7208101500")
        self.assertEqual(rows[0]["quantity_unit_1"], "KG")


if __name__ == "__main__":
    unittest.main()
