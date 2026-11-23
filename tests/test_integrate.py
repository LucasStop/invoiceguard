"""Tests of src/integrate.py: key rules, fallback, missing matches and reconciliation of counts and totals.

Expected values were calculated by hand (see the comment of each case).

Usage: python3 -m unittest discover -s tests
"""
import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.integrate import IntegrationError, integrate


def invoice(number, day, currency, subtotal, tax="0", discount="0"):
    return {"invoice_number": number, "supplier": "S", "issue_date": day, "currency": currency,
            "subtotal": Decimal(subtotal), "tax_rate": Decimal(tax), "discount": Decimal(discount),
            "source_file": "a.csv", "source_line": 2}


def rates(*rows):
    return pd.DataFrame([{"currency": c, "rate_date": d, "rate": Decimal(r)} for c, d, r in rows],
                        columns=["currency", "rate_date", "rate"])


FRIDAY, SATURDAY, SUNDAY = date(2026, 11, 6), date(2026, 11, 7), date(2026, 11, 8)
RATES = rates(("USD", FRIDAY, "5.50"), ("EUR", FRIDAY, "6.00"))


class IntegrationTest(unittest.TestCase):
    def test_totals_and_levels_in_brl(self):
        # USD 1000.00 + 10% tax = 1100.00; x 5.50 = 6050.00 -> MANAGER REVIEW (naive 1100.00 is also MANAGER)
        # USD 90.00, no tax: x 5.50 = 495.00 -> AUTO-APPROVED
        # BRL 500.00 stays 500.00
        frame, _ = integrate([invoice("1", FRIDAY, "USD", "1000.00", "10"), invoice("2", FRIDAY, "USD", "90.00"),
                              invoice("3", FRIDAY, "BRL", "500.00")], RATES)
        self.assertEqual(list(frame["total_brl"]), [Decimal("6050.00"), Decimal("495.00"), Decimal("500.00")])
        self.assertEqual(list(frame["approval_status"]), ["MANAGER REVIEW", "AUTO-APPROVED", "AUTO-APPROVED"])

    def test_rate_changes_the_level(self):
        # USD 1900.00 x 5.50 = 10450.00 -> DIRECTOR APPROVAL, but read as BRL it would be MANAGER REVIEW
        frame, _ = integrate([invoice("1", FRIDAY, "USD", "1900.00")], RATES)
        self.assertEqual(frame.loc[0, "approval_status"], "DIRECTOR APPROVAL")
        self.assertEqual(frame.loc[0, "status_without_fx"], "MANAGER REVIEW")
        self.assertTrue(frame.loc[0, "level_changed_by_fx"])

    def test_weekend_falls_back_to_last_business_day(self):  # test 3: date without rate, visible and handled
        frame, checks = integrate([invoice("1", SATURDAY, "USD", "100.00"), invoice("2", SUNDAY, "EUR", "100.00"),
                                   invoice("3", FRIDAY, "USD", "100.00")], RATES)
        self.assertEqual(list(frame["rate_date"]), [FRIDAY, FRIDAY, FRIDAY])
        self.assertEqual(list(frame["rate_fallback"]), [True, True, False])
        self.assertEqual(checks["fallback_rows"], 2)

    def test_no_rate_in_window_rejects_with_invoice_numbers(self):  # test 3
        with self.assertRaises(IntegrationError) as caught:
            integrate([invoice("INV-9", date(2026, 11, 20), "USD", "100.00")], RATES)
        self.assertIn("INV-9", str(caught.exception))

    def test_currency_without_any_rate_is_rejected(self):
        with self.assertRaises(IntegrationError):
            integrate([invoice("1", FRIDAY, "EUR", "100.00")], rates(("USD", FRIDAY, "5.50")))

    def test_duplicate_rate_key_is_rejected(self):  # test 3
        with self.assertRaises(IntegrationError) as caught:
            integrate([invoice("1", FRIDAY, "USD", "100.00")], rates(("USD", FRIDAY, "5.50"), ("USD", FRIDAY, "5.60")))
        self.assertIn("more than one rate", str(caught.exception))

    def test_many_invoices_one_rate_keeps_row_count_and_totals(self):  # many-to-one, counts and totals preserved
        invoices = [invoice(str(n), FRIDAY, "USD", "100.00") for n in range(5)] + [invoice("9", FRIDAY, "BRL", "10.00")]
        frame, checks = integrate(invoices, RATES)
        self.assertEqual((checks["rows_before"], checks["rows_after"]), (6, 6))
        self.assertEqual(checks["foreign_total_before"], checks["foreign_total_after"])
        self.assertEqual(checks["foreign_total_before"]["USD"], Decimal("500.00"))
        self.assertEqual(checks["total_brl"], Decimal("2750.00") + Decimal("10.00"))  # 5 x 550.00 + 10.00
        self.assertEqual(list(frame["invoice_number"]), ["0", "1", "2", "3", "4", "9"])

    def test_only_brl_needs_no_rates(self):
        frame, checks = integrate([invoice("1", FRIDAY, "BRL", "100.00")], rates())
        self.assertEqual(frame.loc[0, "total_brl"], Decimal("100.00"))
        self.assertEqual(checks["fallback_rows"], 0)


class SavedRealDataTest(unittest.TestCase):
    """The project batch against the saved PTAX responses (data/raw), checked with hand-made multiplications."""

    @classmethod
    def setUpClass(cls):
        from src.fx_api import acquire_rates
        from src.loader import load_batch
        root = Path(__file__).resolve().parent.parent
        invoices = load_batch(root / "data" / "input", date(2026, 11, 23))
        rates_frame, _ = acquire_rates(invoices, "saved", root / "data" / "raw")
        cls.frame, cls.checks = integrate(invoices, rates_frame)

    def total(self, number):
        return self.frame.loc[self.frame["invoice_number"] == number, "total_brl"].iloc[0]

    def test_hand_calculated_rows(self):
        # INV-A004: (1800.00 + 5% - 20.00) = 1870.00 x 5.5013 (2026-11-06) = 10287.431 -> 10287.43
        self.assertEqual(self.total("INV-A004"), Decimal("10287.43"))
        # INV-A005: 950.00 on Saturday 2026-11-07 uses the 2026-11-06 rate: 950 x 5.5013 = 5226.235 -> 5226.24
        self.assertEqual(self.total("INV-A005"), Decimal("5226.24"))
        # INV-B006: 1780.00 x 5.6143 (2026-11-12) = 9993.454 -> 9993.45, just under the director limit
        self.assertEqual(self.total("INV-B006"), Decimal("9993.45"))

    def test_counts_and_weekend_holiday_fallback(self):
        self.assertEqual((self.checks["rows_before"], self.checks["rows_after"]), (24, 24))
        self.assertEqual(self.checks["fallback_rows"], 4)  # 2026-11-02 and 11-20 (holidays), 11-07 and 11-15 (weekend)
        self.assertEqual(self.checks["unmatched_rows"], 0)


if __name__ == "__main__":
    unittest.main()
