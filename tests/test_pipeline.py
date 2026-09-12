import unittest
from pathlib import Path

from trade_shock.census import load_fixture
from trade_shock.harmonize import load_core_ranges
from trade_shock.panel import build_panel
from trade_shock.validate import validate_panel


ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def test_fixture_build_is_valid_and_aggregates_rp(self):
        rows = []
        for month in ("2025-02", "2025-03", "2025-04", "2025-06", "2025-07"):
            rows.extend(load_fixture(ROOT / "tests" / "fixtures" / "census" / f"{month}-7208101500.json"))
        panel = build_panel(rows, load_core_ranges(ROOT / "config" / "core_steel_hs6_ranges.csv"))
        report = validate_panel(panel, ["2025-02", "2025-03", "2025-04", "2025-06", "2025-07"], ["7208101500"])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(len(panel), 5)
        self.assertEqual(panel[0]["source_row_count"], 2)
        self.assertEqual(panel[0]["import_value_usd"], 10500000)

    def test_rp_summary_is_not_double_counted(self):
        def row(rp, value):
            return {
                "I_COMMODITY": "7208101500",
                "I_COMMODITY_LDESC": "pilot",
                "CTY_CODE": "1220",
                "CTY_NAME": "CANADA",
                "YEAR": "2025",
                "MONTH": "01",
                "UNIT_QY1": "KG",
                "CON_VAL_MO": str(value),
                "CON_QY1_MO": str(value),
                "DUT_VAL_MO": "0",
                "CAL_DUT_MO": "0",
                "RP": rp,
                "LAST_UPDATE": "0",
            }

        rows = [row("10", 60), row("19", 40), row("-", 100)]
        panel = build_panel(rows, load_core_ranges(ROOT / "config" / "core_steel_hs6_ranges.csv"))
        self.assertEqual(panel[0]["import_value_usd"], 100)
        self.assertEqual(panel[0]["source_row_count"], 3)


if __name__ == "__main__":
    unittest.main()
