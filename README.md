# InvoiceGuard

Checks one supplier invoice: calculates the total payable (subtotal + tax - discount) and routes it to the approval level it needs (auto-approve, manager review, director approval or reject).

Group project for *AI-Assisted Python for Business Problem Solving* (PUCPR), Summative Assessments LO 1 (one invoice per run) and LO 2 (batch of invoices with exchange rates). Professor: Evandro Alberto Zatti. All companies, suppliers and amounts in this repository are fictional.

## Team

| Member | GitHub |
|---|---|
| Eduardo Pereira | [@EduardoPereirabsi](https://github.com/EduardoPereirabsi) |
| Lucas Stopinski da Silva | [@LucasStop](https://github.com/LucasStop) |
| Patrick de Oliveira | [@Ptrick-de](https://github.com/Ptrick-de) |

## What it does

The accounts payable team of a small business receives supplier invoices and has to decide who may authorize each payment. For one invoice at a time, in BRL, InvoiceGuard:

1. reads the invoice number, supplier, subtotal, tax rate (%) and discount, and asks again when an answer is not valid;
2. calculates the tax on the subtotal (rounded to cents, half a cent up) and the total payable, with exact decimal arithmetic;
3. decides the approval level from the total payable, never from the subtotal:

| Total payable (BRL) | Approval status |
|---|---|
| 0.00 or less | `REJECTED` |
| 0.01 up to 999.99 | `AUTO-APPROVED` |
| 1,000.00 up to 9,999.99 | `MANAGER REVIEW` |
| 10,000.00 or more | `DIRECTOR APPROVAL` |

A total exactly equal to a limit goes to the higher level. The business problem, the IPO model and the full rule are in [docs/business-model.md](docs/business-model.md).

## How to run

Needs Python 3.9 or newer and nothing else (developed with Python 3.15.0).

```
python3 invoiceguard.py
```

Example session (a real run; the text after each colon is what was typed):

```text
Enter invoice number: INV-2026-0042
Enter supplier name: Acme Ltda
Enter subtotal (BRL): 1250.50
Enter tax rate (%, e.g. 12.5 for 12.5%): 12.5
Enter discount (BRL): 100

--- InvoiceGuard result ---
Invoice number  : INV-2026-0042
Supplier        : Acme Ltda
Subtotal        : BRL 1,250.50
Tax rate        : 12.50%
Tax value       : BRL 156.31
Discount        : BRL 100.00
Total payable   : BRL 1,306.81
Approval status : MANAGER REVIEW
```

## Tests

```
python3 test_invoiceguard.py
```

The runner starts `invoiceguard.py` once per case, prints the results table and exits with 0 when every case passes and 1 otherwise. Current result: 18 of 18 cases passed and 3 of 3 input cases passed. The tables, the coverage of the three limits and the check that the cases fail on 18 broken versions of the script are in [docs/test-cases.md](docs/test-cases.md).

## Where each deliverable is

| Item | Deliverable | File |
|---|---|---|
| 1.1 | Business problem | [docs/business-model.md](docs/business-model.md), section 1.1 |
| 1.2 | IPO model | [docs/business-model.md](docs/business-model.md), section 1.2 |
| 1.3 | Python program | [invoiceguard.py](invoiceguard.py) |
| 1.4 | AI use log, part 1 | [docs/ai-log.md](docs/ai-log.md) |
| 2.1 | Decision rule | [docs/business-model.md](docs/business-model.md), section 2.1 |
| 2.2 | `if / elif / else` | [invoiceguard.py](invoiceguard.py) |
| 2.3 | Test table | [docs/test-cases.md](docs/test-cases.md), [test_invoiceguard.py](test_invoiceguard.py) |
| 2.4 | AI use log, part 2 | [docs/ai-log.md](docs/ai-log.md) |

The AI use declaration is at the top of [docs/ai-log.md](docs/ai-log.md).

## Known limitations

- **One invoice per run.** Run the script again for the next invoice. If the input ends before all five answers are given (for example a closed pipe), Python stops with `EOFError`.
- **Input format is strict.** Numbers accept a point or a comma as decimal separator and at most two decimals. These are rejected and asked again: `1.250,50`, `R$ 100`, `12%`, `.5`, `5.`, `+5`, `1e3`, `1_000`, `nan`, negatives. Type `0.5`, not `.5`.
- **The tax rate is a percentage.** Typing `0.125` means 0.125%, not 12.5%; the program cannot tell the difference. The rate is limited to 100.
- **No cap on the discount.** A discount larger than subtotal plus tax is accepted and gives a negative total, which is `REJECTED` (rule BR-2).
- **The program does not check the total printed on the supplier invoice.** It calculates the total payable from the five inputs only.
- **The policy values are assumptions.** The approval limits (BRL 1,000.00 and BRL 10,000.00), the tax base (subtotal, before the discount; inherited from the TE1 pipeline) and half-up rounding are choices of the group for a fictional company, not tax-law rules. The limits are the two named constants at the top of [invoiceguard.py](invoiceguard.py).

---

# RA2 (LO 2): batch of invoices with exchange rates

## The recurring task

Every week the accounts payable team receives invoice files from its suppliers, in BRL, USD and EUR. The approval limits are in BRL, so an invoice in a foreign currency has to be converted before it is routed. **Business question:** what is the total payable in BRL of each invoice, at the official rate of its issue date, and which approval level does it need? The local data cannot answer it; the exchange rate comes from the PTAX of the Banco Central do Brasil.

- **User:** the accounts payable analyst.
- **Input:** two or more CSV files in `data/input/` with the columns `invoice_number, supplier, issue_date, currency, subtotal, tax_rate, discount`.
- **Output:** a processed CSV, an integrated CSV, a workbook and a text report, in `output/runs/<run id>/`.

## Setup and the one command

Open the project folder in VS Code, open a terminal (Terminal > New Terminal) and run:

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt        # pandas and openpyxl; on Windows: .venv\Scripts\pip
.venv/bin/python run.py --mode live              # calls the API and saves the response in data/raw
.venv/bin/python run.py --mode saved             # offline: reuses the last saved response
.venv/bin/python run.py --input tests/fixtures/invalid_value --mode saved    # controlled failure
cat output/latest.txt                            # which run was the last, its status and the last success
```

The first run needs `--mode live` unless `data/raw/` already has the saved responses (it does in this repository). Exit code 0 means success, 1 means the run was rejected.

## How a run works

1. **Acquire and validate the files** (`src/loader.py`): reads every CSV of the folder (at least two) and applies five rules. One bad row or file rejects the whole batch with every problem listed with its file and line.
2. **Acquire the rates** (`src/fx_api.py`): one GET per foreign currency, with parameters, a 15 s timeout and HTTP error handling. The response is checked (structure, fields, rate above zero, dates, unique key) and only then saved to `data/raw/`.
3. **Integrate** (`src/integrate.py`): joins invoices and rates, checks counts and totals before and after.
4. **Store** (`src/outputs.py`, `src/workflow.py`): writes the files in `output/incomplete/<id>`, checks the workbook against the CSV and moves the folder to `output/runs/<id>`.

The rules of the invoice (tax, total, approval level) are in `src/rules.py`, the same arithmetic as `invoiceguard.py`.

### Validation rules and why

| Rule | Why |
|---|---|
| All required columns, no missing or extra cells | a shifted row would silently corrupt the amounts |
| `invoice_number` filled and unique in the whole batch | a duplicate would be paid twice |
| `currency` is BRL, USD or EUR | only these have a rate rule |
| `issue_date` is `YYYY-MM-DD` and not in the future | the rate is looked up by this date |
| `subtotal`, `tax_rate`, `discount` in the LO1 format, tax rate at most 100 | same input contract as LO1 |

### Integration rule

| Source | One row is |
|---|---|
| Invoices (CSV) | one supplier invoice, key `invoice_number` |
| Rates (API) | the closing selling rate of one currency on one business day, key `(currency, rate_date)` |

`rate_date` is the issue date, or the last business day before it when that day has no rate (weekend, holiday, up to 7 days back). Many invoices share one rate (many to one). BRL invoices need no rate. The total payable in BRL is the total in the invoice currency times the rate, rounded half up to cents; the approval level is decided on that BRL total. The run checks that the number of rows and the totals by currency are the same before and after the merge, and rejects invoices without a rate.

### Source mode and failure policy

- `live` calls the API; `saved` reads `data/raw/`. The mode is in `run.log`, in the report and in the `rate_mode` column of the integrated CSV.
- A run is built in `output/incomplete/<id>` and becomes `output/runs/<id>` only when every step passed. A failed run stays in `incomplete/` with its `run.log`, `latest.txt` says `status=FAILED`, and earlier successful runs are never changed (`last_success` keeps pointing to the last good one).

### Output files of a run

| File | Content |
|---|---|
| `invoices_processed.csv` | validated invoices with tax and total in the invoice currency (ST4) |
| `invoices_integrated.csv` | plus rate, rate date, total in BRL, approval level and source file (ST5) |
| `invoices.xlsx` | sheet *Details* (one row per invoice) and *Summary* (by currency and level, sorted by BRL total); numeric amounts, formats, frozen header, filters |
| `report.txt` | run, files, scope, indicators, one finding and one limitation |
| `run.log` | sources, steps and outcome |

### Adaptations of the ST3 logic

The ST3 deliverable is not in this repository. The validation of the LO1 input format was reused in `src/loader.py` (same number pattern, same tax limit) and extended to files: required columns, uniqueness, currency and date. The ST3-style aggregation (grouping and sorting by a metric) became the summary by currency and approval level. If the group has ST3 code to reuse, it replaces these two functions without changing the workflow.

## Source

Banco Central do Brasil, PTAX (Olinda API), licence ODbL. Provider, endpoint, parameters, acquisition date, units and conditions: [docs/source-record.md](docs/source-record.md). The rate used is the selling rate of the closing bulletin, a group assumption.

## Tests

```
.venv/bin/python -m unittest discover -s tests
```

48 tests, no network. Results of the six required tests, the ST4 extras and a check that the tests fail on broken code: [docs/test-cases-ra2.md](docs/test-cases-ra2.md).

## Where each LO 2 deliverable is

| Rubric item | File |
|---|---|
| 4.1 batch, folders, source filenames | `src/loader.py`, `data/input/`, `source_file` column |
| 4.2 workbook | `src/outputs.py`, `output/runs/<id>/invoices.xlsx` |
| 4.3 report, rules, log, latest run | `src/outputs.py`, `src/workflow.py`, `output/latest.txt` |
| 4.4 AI log, ST4 | [docs/ai-log.md](docs/ai-log.md), part 3 |
| 5.1 API | `src/fx_api.py`, [docs/source-record.md](docs/source-record.md) |
| 5.2 integration | `src/integrate.py`, section "Integration rule" above |
| 5.3 workflow | `run.py`, `src/workflow.py` |
| 5.4 AI log, ST5 | [docs/ai-log.md](docs/ai-log.md), part 4 |
| Plan | [docs/plano-ra2.md](docs/plano-ra2.md) |

## Limitations (RA2)

- The rate type (closing selling rate of the issue date) is a group assumption; the payment date could use another rate.
- The sample is fictional and small; the counts in the report illustrate the method.
- The live API is checked by hand, not by the automated tests.
- A date without a rate uses the last business day within 7 days; with no rate in that window the batch is rejected.
- The LO1 rule exists twice, in `invoiceguard.py` and `src/rules.py`; a change must be made in both.
- Only BRL, USD and EUR are supported.
