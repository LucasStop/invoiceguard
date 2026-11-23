"""Tests of src/fx_api.py: test 2 (invalid external data), test 3 (duplicate key) and test 4 (acquisition failure).

No test touches the network: urlopen is replaced by a fake.

Usage: python3 -m unittest discover -s tests
"""
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.fx_api import FxError, acquire_rates, fetch_period, load_raw, rates_frame

META = {"currency": "USD", "start": "2026-11-01", "end": "2026-11-10", "provider": "test"}


def record(day="2026-11-03", rate=5.5, kind="Fechamento"):
    return {"cotacaoCompra": 5.4, "cotacaoVenda": rate, "dataHoraCotacao": f"{day} 13:11:07.766", "tipoBoletim": kind}


def body(*records):
    return json.dumps({"@odata.context": "x", "value": list(records)})


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def fake_urlopen(text=None, error=None):
    calls = []

    def urlopen(url, timeout=None):
        calls.append((url, timeout))
        if error:
            raise error
        return FakeResponse(text.encode("utf-8"))

    urlopen.calls = calls
    return urlopen


class ValidResponseTest(unittest.TestCase):
    def test_keeps_only_closing_bulletins_with_exact_decimal_rates(self):
        frame = rates_frame(body(record(rate=5.4935), record(rate=5.1, kind="Abertura"), record("2026-11-04", 5.4778)), META)
        self.assertEqual(list(frame["rate_date"]), [date(2026, 11, 3), date(2026, 11, 4)])
        self.assertEqual(list(frame["rate"]), [Decimal("5.4935"), Decimal("5.4778")])

    def test_empty_list_is_valid_and_gives_no_rates(self):
        self.assertEqual(len(rates_frame(body(), META)), 0)


class InvalidExternalDataTest(unittest.TestCase):  # test 2
    def reject(self, text, part):
        with self.assertRaises(FxError) as caught:
            rates_frame(text, META)
        self.assertIn(part, str(caught.exception))

    def test_structure(self):
        self.reject("not json", "not valid JSON")
        self.reject("[]", "unexpected JSON structure")
        self.reject('{"value": {"a": 1}}', "unexpected JSON structure")

    def test_missing_field(self):
        broken = record()
        del broken["cotacaoVenda"]
        self.reject(body(broken), "missing cotacaoVenda")

    def test_rate_must_be_positive_number(self):
        self.reject(body(record(rate=-5.5)), "above zero")
        self.reject(body(record(rate=0)), "above zero")
        self.reject(body(record(rate="5.5")), "above zero")
        self.reject(body(record(rate=None)), "above zero")

    def test_bad_date_and_date_outside_window(self):
        bad = record()
        bad["dataHoraCotacao"] = "yesterday"
        self.reject(body(bad), "is not a date")
        self.reject(body(record("2026-12-01")), "outside the requested window")


class KeyProblemTest(unittest.TestCase):  # test 3
    def test_two_closing_rates_for_one_day_are_rejected(self):
        with self.assertRaises(FxError) as caught:
            rates_frame(body(record(rate=5.5), record(rate=5.6)), META)
        self.assertIn("more than one", str(caught.exception))


class AcquisitionFailureTest(unittest.TestCase):  # test 4
    def test_http_500_is_a_visible_error(self):
        error = urllib.error.HTTPError("u", 500, "Internal Server Error", {}, io.BytesIO())
        with self.assertRaises(FxError) as caught:
            fetch_period("USD", date(2026, 11, 1), date(2026, 11, 10), urlopen=fake_urlopen(error=error))
        self.assertIn("HTTP 500", str(caught.exception))

    def test_timeout_is_a_visible_error(self):
        with self.assertRaises(FxError) as caught:
            fetch_period("USD", date(2026, 11, 1), date(2026, 11, 10), urlopen=fake_urlopen(error=TimeoutError("slow")))
        self.assertIn("timed out", str(caught.exception))

    def test_request_has_parameters_and_timeout(self):
        urlopen = fake_urlopen(body(record()))
        text, meta = fetch_period("USD", date(2026, 11, 1), date(2026, 11, 10), urlopen=urlopen)
        url, timeout = urlopen.calls[0]
        self.assertEqual(timeout, 15)
        for part in ("%40moeda=%27USD%27", "%2711-01-2026%27", "%2711-10-2026%27", "%24format=json"):
            self.assertIn(part, url)
        self.assertEqual(meta["currency"], "USD")

    def test_saved_mode_without_saved_response_fails_clearly(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FxError) as caught:
                load_raw("USD", folder)
            self.assertIn("--mode live", str(caught.exception))

    def test_failed_live_run_does_not_replace_the_saved_response(self):
        invoices = [{"currency": "USD", "issue_date": date(2026, 11, 5)}]
        with tempfile.TemporaryDirectory() as folder:
            acquire_rates(invoices, "live", folder, urlopen=fake_urlopen(body(record("2026-11-04", 5.5))))
            before = (Path(folder) / "ptax_USD.json").read_text()
            with self.assertRaises(FxError):
                acquire_rates(invoices, "live", folder, urlopen=fake_urlopen(body(record("2026-11-04", -1))))
            self.assertEqual((Path(folder) / "ptax_USD.json").read_text(), before)

    def test_live_then_saved_gives_the_same_rates(self):
        invoices = [{"currency": "USD", "issue_date": date(2026, 11, 5)}, {"currency": "BRL", "issue_date": date(2026, 11, 5)}]
        with tempfile.TemporaryDirectory() as folder:
            live, metas = acquire_rates(invoices, "live", folder, urlopen=fake_urlopen(body(record("2026-11-04", 5.5))))
            saved, saved_metas = acquire_rates(invoices, "saved", folder)
            self.assertTrue(live.equals(saved))
            self.assertEqual((metas[0]["mode"], saved_metas[0]["mode"]), ("live", "saved"))


if __name__ == "__main__":
    unittest.main()
