"""Tests of the workflow and outputs: test 1 end to end, test 4 (acquisition failure), test 5 (write failure),
test 6 (repeated run), plus workbook content and verification.

Runs use the project batch (data/input) and the saved PTAX responses (data/raw); output goes to a temp folder.

Usage: python3 -m unittest discover -s tests
"""
import io
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import workflow
from src.outputs import verify_workbook
from src.workflow import read_latest, run

INPUT, RAW = ROOT / "data" / "input", ROOT / "data" / "raw"
INVALID = ROOT / "tests" / "fixtures" / "invalid_value"


def clock(second):
    return lambda: datetime(2026, 11, 23, 12, 0, second, tzinfo=timezone.utc)


class WorkflowTestCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.out = Path(folder.name) / "output"

    def run_ok(self, second=0, **kwargs):
        ok, run_id, message = run(INPUT, RAW, self.out, "saved", run_id=f"run{second}", now=clock(second), **kwargs)
        self.assertTrue(ok, message)
        return run_id


class SuccessfulRunTest(WorkflowTestCase):  # test 1
    def test_package_has_every_output_and_latest_says_success(self):
        run_id = self.run_ok()
        package = self.out / "runs" / run_id
        self.assertEqual(sorted(p.name for p in package.iterdir()),
                         ["invoices.xlsx", "invoices_integrated.csv", "invoices_processed.csv", "report.txt", "run.log"])
        latest = read_latest(self.out)
        self.assertEqual((latest["status"], latest["run_id"], latest["last_success"], latest["mode"]),
                         ("SUCCESS", run_id, run_id, "saved"))
        self.assertFalse((self.out / "incomplete" / run_id).exists())

    def test_totals_match_hand_calculation_in_every_output(self):
        run_id = self.run_ok()
        package = self.out / "runs" / run_id
        csv_text = (package / "invoices_integrated.csv").read_text()
        self.assertIn("INV-A004", csv_text)
        self.assertIn(",10287.43,DIRECTOR APPROVAL,", csv_text)  # 1870.00 x 5.5013, calculated by hand
        self.assertIn("BRL 195,519.01", (package / "report.txt").read_text())
        log = (package / "run.log").read_text()
        for part in ("validated 24 invoices from invoices_a.csv, invoices_b.csv", "rate source mode: saved", "workbook verified"):
            self.assertIn(part, log)

    def test_report_has_scope_three_indicators_finding_and_limitation(self):
        report = (self.out / "runs" / self.run_ok() / "report.txt").read_text()
        for part in ("Run: run0", "invoices_a.csv (12 invoices)", "Total payable in BRL by currency", "Invoices by approval level",
                     "whose level changes because of the rate", "Finding:", "Limitation:", "3. Interpretation (not a calculation)"):
            self.assertIn(part, report)


class WorkbookTest(WorkflowTestCase):
    def open(self):
        return load_workbook(self.out / "runs" / self.run_ok() / "invoices.xlsx")

    def test_sheets_are_numeric_formatted_frozen_filtered_and_summary_sorted(self):
        workbook = self.open()
        self.assertEqual(workbook.sheetnames, ["Details", "Summary"])
        for sheet in workbook:
            self.assertEqual(sheet.freeze_panes, "A2")
            self.assertTrue(sheet.auto_filter.ref)
        detail = workbook["Details"]
        header = [c.value for c in detail[1]]
        total = detail.cell(row=2, column=header.index("Total payable (BRL)") + 1)
        self.assertIsInstance(total.value, (int, float))
        self.assertEqual(total.number_format, "#,##0.00")
        self.assertEqual(detail.cell(row=2, column=header.index("Issue date") + 1).number_format, "yyyy-mm-dd")
        totals = [r[4] for r in workbook["Summary"].iter_rows(min_row=2, values_only=True)]
        self.assertEqual(totals, sorted(totals, reverse=True))
        self.assertAlmostEqual(sum(totals), 195519.01, places=2)

    def test_verification_catches_a_changed_value(self):
        run_id = self.run_ok()
        package = self.out / "runs" / run_id
        workbook = load_workbook(package / "invoices.xlsx")
        detail = workbook["Details"]
        column = [c.value for c in detail[1]].index("Total payable (BRL)") + 1
        detail.cell(row=2, column=column).value += 1
        workbook.save(package / "tampered.xlsx")
        from src.integrate import integrate
        from src.fx_api import acquire_rates
        from src.loader import load_batch
        invoices = load_batch(INPUT, datetime(2026, 11, 23).date())
        frame, _ = integrate(invoices, acquire_rates(invoices, "saved", RAW)[0])
        frame["rate_mode"] = "saved"
        with self.assertRaises(ValueError):
            verify_workbook(package / "tampered.xlsx", package / "invoices_integrated.csv", frame)


class RepeatedRunTest(WorkflowTestCase):  # test 6
    def test_second_run_gives_same_results_and_keeps_the_first_package(self):
        first, second = self.run_ok(1), self.run_ok(2)
        a, b = (self.out / "runs" / first), (self.out / "runs" / second)
        for name in ("invoices_integrated.csv", "invoices_processed.csv"):
            self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
        self.assertTrue((a / "report.txt").exists() and (a / "invoices.xlsx").exists())
        latest = read_latest(self.out)
        self.assertEqual((latest["run_id"], latest["last_success"]), (second, second))


class FailureTest(WorkflowTestCase):
    def test_invalid_input_fails_visibly_and_keeps_earlier_success(self):
        good = self.run_ok(1)
        ok, bad, message = run(INVALID, RAW, self.out, "saved", run_id="bad", now=clock(2))
        self.assertFalse(ok)
        self.assertIn("subtotal 'abc'", message)
        latest = read_latest(self.out)
        self.assertEqual((latest["status"], latest["run_id"], latest["last_success"]), ("FAILED", "bad", good))
        self.assertFalse((self.out / "runs" / "bad").exists())
        self.assertIn("run FAILED", (self.out / "incomplete" / "bad" / "run.log").read_text())
        self.assertTrue((self.out / "runs" / good / "report.txt").exists())

    def test_acquisition_failure_in_live_mode_is_visible_and_publishes_nothing(self):  # test 4
        def urlopen(url, timeout=None):
            raise urllib.error.HTTPError(url, 500, "Internal Server Error", {}, io.BytesIO())

        raw = Path(self.out).parent / "raw"
        ok, run_id, message = run(INPUT, raw, self.out, "live", urlopen=urlopen, run_id="live1", now=clock(1))
        self.assertFalse(ok)
        self.assertIn("HTTP 500", message)
        self.assertEqual(read_latest(self.out)["status"], "FAILED")
        self.assertFalse((self.out / "runs").exists())
        self.assertFalse(raw.exists() and any(raw.iterdir()))  # nothing saved from a failed acquisition

    def test_saved_mode_without_saved_response_fails(self):
        empty = Path(self.out).parent / "empty_raw"
        ok, _, message = run(INPUT, empty, self.out, "saved", run_id="s1", now=clock(1))
        self.assertFalse(ok)
        self.assertIn("--mode live", message)

    def test_output_write_failure_never_publishes_a_partial_package(self):  # test 5
        good = self.run_ok(1)
        real_replace = os.replace

        def replace(src, dst):
            if "runs" in Path(dst).parts:
                raise OSError("disk full")
            return real_replace(src, dst)

        with mock.patch.object(workflow.os, "replace", side_effect=replace):
            ok, bad, message = run(INPUT, RAW, self.out, "saved", run_id="bad", now=clock(2))
        self.assertFalse(ok)
        self.assertIn("disk full", message)
        self.assertFalse((self.out / "runs" / "bad").exists())
        self.assertTrue((self.out / "incomplete" / "bad").exists())
        latest = read_latest(self.out)
        self.assertEqual((latest["status"], latest["last_success"]), ("FAILED", good))
        self.assertEqual(sorted(p.name for p in (self.out / "runs").iterdir()), [good])

    def test_write_error_in_the_middle_leaves_only_incomplete_files(self):  # test 5, second way
        with mock.patch("src.workflow.outputs.write_workbook", side_effect=OSError("read-only")):
            ok, _, message = run(INPUT, RAW, self.out, "saved", run_id="bad", now=clock(1))
        self.assertFalse(ok)
        self.assertFalse((self.out / "runs").exists())
        self.assertEqual(read_latest(self.out)["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
