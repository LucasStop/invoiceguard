# InvoiceGuard

Checks one supplier invoice: calculates the total payable (subtotal + tax - discount) and routes it to the approval level it needs (auto-approve, manager review, director approval or reject).

Group project for *AI-Assisted Python for Business Problem Solving* (PUCPR), Summative Assessment - LO 1. Professor: Evandro Alberto Zatti. All companies, suppliers and amounts in this repository are fictional.

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
