# InvoiceGuard RA2: test cases

Tests of the batch workflow (Summative Assessment - LO 2, ST4 and ST5). The LO1 decision-rule cases are in [test-cases.md](test-cases.md) and still run, now also against `src/rules.py`.

## How to run

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests
```

Current result: **48 tests, all pass** (observed on 2026-11-23, Python 3.15.2, pandas 3.1.1, openpyxl 3.1.5; the CI runs the same suite on Python 3.12). No test needs the network: the API is replaced by a fake `urlopen`, and the saved responses in `data/raw/` stand in for a live answer.

Expected values were written by hand from the rules, never copied from the program output. Examples: `INV-A004` is (1800.00 + 5% - 20.00) = 1870.00 x 5.5013 = 10287.431, so BRL 10,287.43; `INV-A005` is 950.00 x 5.5013 = 5226.235, a half cent that must round up to 5,226.24.

## The six required tests (ST5)

| # | Test | Preparation | Expected | Observed | Result | Code |
|---|---|---|---|---|---|---|
| 1 | Valid and complete inputs | the two CSVs of `data/input`, saved rates, temp output folder | 24 invoices, one package with CSVs, workbook, report and log; `latest.txt` says SUCCESS; totals equal the hand calculation | package has the 5 files, `INV-A004` = 10,287.43 `DIRECTOR APPROVAL`, total BRL 195,519.01 | PASS | `SuccessfulRunTest`, `ValidBatchTest` |
| 2 | Invalid external data | JSON that is not an object, without `cotacaoVenda`, with a negative, zero, text or null rate, with a bad date or a date outside the window | each one rejected with a clear message, nothing published | `FxError` naming the problem in every case | PASS | `InvalidExternalDataTest` |
| 3 | Key problem | two closing rates for one day; an invoice date with no rate; a currency with no rate at all | duplicate rejected; weekend and holiday use the last business day and are marked; no rate within 7 days rejects the batch listing the invoices | duplicate: `FxError` "more than one"; Saturday and Sunday map to Friday with `rate_fallback` true (4 rows in the real batch); missing: `IntegrationError` with the invoice number | PASS | `KeyProblemTest`, `IntegrationTest` |
| 4 | Acquisition failure | fake `urlopen` raising HTTP 500 and a timeout; live run with HTTP 500 | visible error, nothing saved, `latest.txt` marks FAILED | `FxError` "HTTP 500" and "timed out"; `data/raw` empty; no `runs` folder; status FAILED | PASS | `AcquisitionFailureTest`, `FailureTest` |
| 5 | Output write failure | `os.replace` into `runs/` raising `OSError("disk full")`; separately the workbook writer raising `OSError` | no partial package marked as completed, earlier success untouched | the run is FAILED, files stay in `output/incomplete/<id>`, `runs/` keeps only the earlier run, `last_success` unchanged | PASS | `FailureTest` |
| 6 | Valid repeated run | two runs with the same input | same business results, first package preserved | `invoices_integrated.csv` and `invoices_processed.csv` byte-identical; first package still there; `latest.txt` points to the second | PASS | `RepeatedRunTest` |

## ST4 extra tests (batch and robustness)

| Test | Expected | Result |
|---|---|---|
| Invalid value in a CSV (`tests/fixtures/invalid_value`) | whole batch rejected, message with file and line (`invoices_a.csv:3`) | PASS |
| Several problems in one batch | every problem listed, not only the first | PASS |
| Missing column | batch rejected naming the column | PASS |
| No files, one file, missing folder | batch rejected: at least 2 CSV files are required | PASS |
| Duplicate invoice number across the two files | rejected, message says where it was first used | PASS |
| Future date, tax rate above 100, wrong number of cells, header-only files | rejected with a clear message | PASS |
| Failed run after a good run | status FAILED, `last_success` still the good run, no folder in `runs/` | PASS |
| Workbook content | two sheets, numeric amounts, formats, frozen header, filter, summary sorted by BRL total, summary total equals 195,519.01 | PASS |
| Workbook verification | a workbook with one changed value is detected against the CSV | PASS |
| LO1 regression | the 18 decision cases give the same total and level in `src/rules.py` | PASS |
| BRL conversion | half cent rounds up (2.505 -> 2.51); the same amount changes level with the rate | PASS |

## Do the tests fail on broken code?

A test suite that never fails proves little, so five deliberate breaks were tried one at a time on 2026-11-23 and then undone:

| Break | Tests that failed |
|---|---|
| conversion rounds half to even instead of half up | `test_half_cent_rounds_up` |
| business-day lookback set to 0 days | at least 8 tests (fallback, saved real data, repeated run, full run) |
| workbook verification ignores totals | `test_verification_catches_a_changed_value` |
| publish without `os.replace` (package built in place) | 8 or more workflow tests (success, failure and write-failure cases) |
| merge without `validate="many_to_one"` | none: the explicit duplicate-rate check before the merge already rejects that input, so the argument is a second safety net, not the only one |

The last row is an honest gap in the check, not in the code: duplicate rates are stopped earlier.

## What is not tested

- The live API in the automated suite (it would make the tests depend on the network and on the date). The live path was exercised by hand on 2026-11-23, which produced the saved responses.
- Very large batches and concurrent runs.
