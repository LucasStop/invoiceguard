"""Regression of the 18 LO1 decision cases against src/rules.py, plus the BRL conversion.

Expected values are the hand-written ones of test_invoiceguard.py (BR-1 to BR-3 in
docs/business-model.md), so a pass proves the rule did not change when it moved
from the LO1 script into a module.

Usage: python3 -m unittest discover -s tests
"""
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rules import approval_status, calculate_total, convert_to_brl

# (subtotal, tax rate %, discount, expected total payable, expected status)
LO1_CASES = [
    ("500.00", "10", "0", "550.00", "AUTO-APPROVED"),
    ("999.99", "0", "0", "999.99", "AUTO-APPROVED"),
    ("950.00", "10", "0", "1045.00", "MANAGER REVIEW"),
    ("1000.00", "0", "0", "1000.00", "MANAGER REVIEW"),
    ("1000.00", "10", "100.00", "1000.00", "MANAGER REVIEW"),
    ("9999.99", "0", "0", "9999.99", "MANAGER REVIEW"),
    ("10000.00", "0", "0", "10000.00", "DIRECTOR APPROVAL"),
    ("9000.00", "12", "0", "10080.00", "DIRECTOR APPROVAL"),
    ("500.00", "0", "500.00", "0.00", "REJECTED"),
    ("300.00", "5", "400.00", "-85.00", "REJECTED"),
    ("909.09", "10", "0", "1000.00", "MANAGER REVIEW"),
    ("100.70", "10", "110.77", "0.00", "REJECTED"),
    ("0.01", "0", "0", "0.01", "AUTO-APPROVED"),
    ("100.00", "0", "100.01", "-0.01", "REJECTED"),
    ("1000.01", "0", "0", "1000.01", "MANAGER REVIEW"),
    ("10000.01", "0", "0", "10000.01", "DIRECTOR APPROVAL"),
    ("100.00", "10", "105.00", "5.00", "AUTO-APPROVED"),
    ("897.00", "12.5", "9.13", "1000.00", "MANAGER REVIEW"),
]


class Lo1RegressionTest(unittest.TestCase):
    def test_all_18_cases_keep_total_and_status(self):
        for subtotal, tax_rate, discount, expected_total, expected_status in LO1_CASES:
            with self.subTest(subtotal=subtotal, tax_rate=tax_rate, discount=discount):
                _, total = calculate_total(Decimal(subtotal), Decimal(tax_rate), Decimal(discount))
                self.assertEqual(total, Decimal(expected_total))
                self.assertEqual(approval_status(total), expected_status)


class ConversionTest(unittest.TestCase):
    def test_half_cent_rounds_up(self):
        # 100.10 * 5.125 = 513.0125 -> 513.01; 0.50 * 5.01 = 2.505 -> 2.51 (half up, not half even)
        self.assertEqual(convert_to_brl(Decimal("100.10"), Decimal("5.125")), Decimal("513.01"))
        self.assertEqual(convert_to_brl(Decimal("0.50"), Decimal("5.01")), Decimal("2.51"))

    def test_brl_rate_one_is_unchanged(self):
        self.assertEqual(convert_to_brl(Decimal("1234.56"), Decimal("1")), Decimal("1234.56"))

    def test_exchange_rate_can_change_the_level(self):
        # same foreign total, two rates, two levels: why the limit is checked in BRL
        foreign_total = Decimal("1900.00")
        low = convert_to_brl(foreign_total, Decimal("5.00"))    # 9500.00
        high = convert_to_brl(foreign_total, Decimal("5.30"))   # 10070.00
        self.assertEqual(approval_status(low), "MANAGER REVIEW")
        self.assertEqual(approval_status(high), "DIRECTOR APPROVAL")


if __name__ == "__main__":
    unittest.main()
