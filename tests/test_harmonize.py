import unittest
from pathlib import Path

from trade_shock.harmonize import classify_core_steel, hs6_from_hts10, load_core_ranges


ROOT = Path(__file__).resolve().parents[1]


class HarmonizationTests(unittest.TestCase):
    def setUp(self):
        self.ranges = load_core_ranges(ROOT / "config" / "core_steel_hs6_ranges.csv")

    def test_prefix(self):
        self.assertEqual(hs6_from_hts10("7208.10.1500"), "720810")

    def test_pilot_is_core_steel(self):
        result = classify_core_steel("7208101500", self.ranges)
        self.assertTrue(result["is_section232_core_steel"])

    def test_gap_is_not_core_steel(self):
        self.assertFalse(classify_core_steel("7216600000", self.ranges)["is_section232_core_steel"])


if __name__ == "__main__":
    unittest.main()

