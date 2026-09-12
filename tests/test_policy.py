import unittest
from datetime import date

from trade_shock.policy import monthly_policy, rate_on


class PolicyTests(unittest.TestCase):
    def test_daily_boundaries(self):
        self.assertEqual(rate_on(date(2025, 3, 11)), 0.0)
        self.assertEqual(rate_on(date(2025, 3, 12)), 0.25)
        self.assertEqual(rate_on(date(2025, 6, 3)), 0.25)
        self.assertEqual(rate_on(date(2025, 6, 4)), 0.50)

    def test_march_is_transition(self):
        result = monthly_policy(2025, 3)
        self.assertTrue(result["is_transition_month"])
        self.assertIsNone(result["section232_rate_clean_month"])
        self.assertAlmostEqual(result["section232_rate_day_weighted"], 5 / 31)

    def test_june_is_transition(self):
        result = monthly_policy(2025, 6)
        self.assertTrue(result["is_transition_month"])
        self.assertAlmostEqual(result["section232_rate_day_weighted"], 0.475)

    def test_clean_months(self):
        self.assertEqual(monthly_policy(2025, 2)["section232_rate_clean_month"], 0.0)
        self.assertEqual(monthly_policy(2025, 4)["section232_rate_clean_month"], 0.25)
        self.assertEqual(monthly_policy(2025, 7)["section232_rate_clean_month"], 0.50)


if __name__ == "__main__":
    unittest.main()

