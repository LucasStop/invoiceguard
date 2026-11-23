"""Tests of src/loader.py: test 1 (valid batch) and test 2 (invalid input rejects the whole batch).

Usage: python3 -m unittest discover -s tests
"""
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.loader import BatchError, load_batch

HEADER = "invoice_number,supplier,issue_date,currency,subtotal,tax_rate,discount\n"
GOOD_A = HEADER + "A1,Acme,2026-11-03,BRL,100.00,10,0\n"
GOOD_B = HEADER + "B1,Beta,2026-11-04,USD,\"50,5\",0,0\n"
TODAY = date(2026, 11, 23)


def batch(**files):
    """Write the given CSV texts to a temporary folder and return it."""
    folder = tempfile.TemporaryDirectory()
    for name, text in files.items():
        (Path(folder.name) / f"{name}.csv").write_text(text, encoding="utf-8")
    batch.keep.append(folder)
    return folder.name


batch.keep = []


class ValidBatchTest(unittest.TestCase):  # test 1
    def test_two_valid_files_load_in_one_call_with_source_filenames(self):
        invoices = load_batch(batch(a=GOOD_A, b=GOOD_B), TODAY)
        self.assertEqual([i["invoice_number"] for i in invoices], ["A1", "B1"])
        self.assertEqual([i["source_file"] for i in invoices], ["a.csv", "b.csv"])
        self.assertEqual(invoices[1]["subtotal"], Decimal("50.5"))  # decimal comma accepted
        self.assertEqual(invoices[0]["issue_date"], date(2026, 11, 3))

    def test_project_input_folder_loads(self):
        invoices = load_batch(ROOT / "data" / "input", TODAY)
        self.assertEqual(len(invoices), 24)
        self.assertEqual({i["source_file"] for i in invoices}, {"invoices_a.csv", "invoices_b.csv"})


class InvalidBatchTest(unittest.TestCase):  # test 2 and ST4 extras
    def reject(self, folder, *expected_parts):
        with self.assertRaises(BatchError) as caught:
            load_batch(folder, TODAY)
        for part in expected_parts:
            self.assertIn(part, str(caught.exception))

    def test_invalid_value_fixture_rejects_whole_batch(self):
        self.reject(ROOT / "tests" / "fixtures" / "invalid_value",
                    "invoices_a.csv:3", "subtotal 'abc'")

    def test_error_names_every_problem_not_just_the_first(self):
        bad = HEADER + "A1,Acme,2026-11-03,JPY,100.00,10,0\nA2,Acme,2026-13-40,BRL,-5,10,0\n"
        self.reject(batch(a=bad, b=GOOD_B), "a.csv:2: currency 'JPY'", "a.csv:3: issue_date", "a.csv:3: subtotal '-5'")

    def test_missing_column(self):
        self.reject(batch(a=GOOD_A, b="invoice_number,supplier\nB1,Beta\n"), "b.csv: missing column(s)")

    def test_no_files_or_single_file_or_missing_folder(self):
        self.reject(batch(), "found 0")
        self.reject(batch(a=GOOD_A), "at least 2 CSV files, found 1")
        self.reject(Path(tempfile.gettempdir()) / "does-not-exist-invoiceguard", "found 0")

    def test_duplicate_invoice_number_across_files(self):
        dup = HEADER + "A1,Beta,2026-11-04,BRL,10.00,0,0\n"
        self.reject(batch(a=GOOD_A, b=dup), "b.csv:2: invoice_number A1 already used at a.csv:2")

    def test_future_date_and_tax_above_100(self):
        bad = HEADER + "B1,Beta,2026-11-24,BRL,10.00,101,0\n"
        self.reject(batch(a=GOOD_A, b=bad), "is in the future", "tax_rate 101")

    def test_wrong_number_of_cells(self):
        self.reject(batch(a=GOOD_A, b=HEADER + "B1,Beta,2026-11-04,BRL,10.00,0\n"), "wrong number of cells")
        self.reject(batch(a=GOOD_A, b=HEADER + "B1,Beta,2026-11-04,BRL,10.00,0,0,9\n"), "wrong number of cells")

    def test_header_only_files_have_no_rows(self):
        self.reject(batch(a=HEADER, b=HEADER), "no invoice rows")


if __name__ == "__main__":
    unittest.main()
