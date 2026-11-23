"""Общая нормализация и исходы (harness.rules): одни и те же правила у систем и у оценщика."""

import unittest

from harness.metrics import m4, m5
from harness.rules import amount_outcome, deadline_outcome, norm_amount, norm_deadline


class NormalizationTest(unittest.TestCase):
    def test_amount_spelling_does_not_matter(self):
        a = norm_amount({"value": "1200", "currency": "€", "period": "per month", "full_coverage": None})
        self.assertEqual((a["value"], a["currency"], a["period"]), (1200.0, "EUR", "month"))
        gt = {"amount": {"value": 1200, "currency": "EUR", "period": "month", "full_coverage": None}}
        self.assertTrue(m5({"amount": {"value": 1200, "currency": "€", "period": "monthly"}}, gt)["correct"])

    def test_full_coverage_is_tristate(self):
        self.assertIsNone(norm_amount({"value": None, "full_coverage": "yes"})["full_coverage"])
        self.assertEqual(amount_outcome({"value": None, "full_coverage": False}), "not_stated")
        self.assertEqual(amount_outcome({"value": None, "full_coverage": True}), "full_coverage_only")
        self.assertEqual(amount_outcome(None), "not_stated")

    def test_granularity_follows_format(self):
        self.assertEqual(norm_deadline({"date": " 2027-01 ", "granularity": "day"})["granularity"], "month")
        self.assertEqual(norm_deadline({"date": "--01-15"})["scope"], "global")

    def test_unknown_cycle_is_not_absence(self):
        self.assertEqual(deadline_outcome([]), "not_stated")
        self.assertEqual(deadline_outcome([{"date": "--01-15", "cycle": None}]), "cycle_unknown")
        gt = {"application_deadlines": [{"date": "--01-15", "granularity": "day_no_year", "cycle": None, "scope": "global"}],
              "cycle_status": "not_found"}
        pred = {"application_deadlines": [{"date": "2027-01-15", "granularity": "day", "cycle": "2027/28", "scope": "global"}]}
        self.assertEqual(m4(pred, gt)["danger"], "year_guessed")
        self.assertEqual(m4(pred, {"application_deadlines": [], "cycle_status": "not_found"})["danger"], "invented")


if __name__ == "__main__":
    unittest.main()
