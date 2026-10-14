# InvoiceGuard: test cases

Deliverable 2.3 of the Summative Assessment - LO 1: tests for the decision rule in [business-model.md](business-model.md), section 2.1, plus a short table for input validation.

## How the tables were produced

- **Input** is what is typed into the script: subtotal, tax rate (%) and discount. The invoice number and the supplier are fixed placeholders in the runner, because they do not change the result.
- **Expected** was written by hand from the rule table in section 2.1 and from BR-1 and BR-2 (tax on the subtotal, rounded half up to cents; total = subtotal + tax - discount). It is not copied from the program output.
- **Actual** is the real output of [`invoiceguard.py`](../invoiceguard.py). The runner [`test_invoiceguard.py`](../test_invoiceguard.py) starts the script once per case as a separate process, types the inputs on its stdin and reads the lines it prints.
- **Passed?** is PASS when expected and actual are identical.

To reproduce, run `python3 test_invoiceguard.py` from the repository root. The exit code is 0 when every case passes and 1 otherwise.

## Results: decision rule (18 cases)

| # | Input: subtotal / tax rate % / discount | Expected: total / status | Actual: total / status | Passed? | What the case checks |
|---|---|---|---|---|---|
| 1 | 500.00 / 10 / 0 | 550.00 / AUTO-APPROVED | 550.00 / AUTO-APPROVED | PASS | typical invoice, middle of the first range |
| 2 | 999.99 / 0 / 0 | 999.99 / AUTO-APPROVED | 999.99 / AUTO-APPROVED | PASS | boundary: 0.01 below the manager limit |
| 3 | 950.00 / 10 / 0 | 1,045.00 / MANAGER REVIEW | 1,045.00 / MANAGER REVIEW | PASS | subtotal is below 1,000.00 but the tax pushes the total above it |
| 4 | 1000.00 / 0 / 0 | 1,000.00 / MANAGER REVIEW | 1,000.00 / MANAGER REVIEW | PASS | boundary: exactly on the manager limit moves up |
| 5 | 1000.00 / 10 / 100.00 | 1,000.00 / MANAGER REVIEW | 1,000.00 / MANAGER REVIEW | PASS | boundary reached through the calculation (tax and discount cancel out) |
| 6 | 9999.99 / 0 / 0 | 9,999.99 / MANAGER REVIEW | 9,999.99 / MANAGER REVIEW | PASS | boundary: 0.01 below the director limit |
| 7 | 10000.00 / 0 / 0 | 10,000.00 / DIRECTOR APPROVAL | 10,000.00 / DIRECTOR APPROVAL | PASS | boundary: exactly on the director limit moves up |
| 8 | 9000.00 / 12 / 0 | 10,080.00 / DIRECTOR APPROVAL | 10,080.00 / DIRECTOR APPROVAL | PASS | tax pushes the total across the director limit |
| 9 | 500.00 / 0 / 500.00 | 0.00 / REJECTED | 0.00 / REJECTED | PASS | boundary: total of exactly zero |
| 10 | 300.00 / 5 / 400.00 | -85.00 / REJECTED | -85.00 / REJECTED | PASS | discount larger than the invoice, negative total |
| 11 | 909.09 / 10 / 0 | 1,000.00 / MANAGER REVIEW | 1,000.00 / MANAGER REVIEW | PASS | tax of 90.909 rounds to 90.91 first, so the total lands exactly on the limit |
| 12 | 100.70 / 10 / 110.77 | 0.00 / REJECTED | 0.00 / REJECTED | PASS | full credit: discount equals subtotal plus tax (100.70 + 10.07), so the total is exactly zero |
| 13 | 0.01 / 0 / 0 | 0.01 / AUTO-APPROVED | 0.01 / AUTO-APPROVED | PASS | boundary: smallest payable total, 0.01 above zero |
| 14 | 100.00 / 0 / 100.01 | -0.01 / REJECTED | -0.01 / REJECTED | PASS | boundary: 0.01 below zero, the nearest negative total |
| 15 | 1000.01 / 0 / 0 | 1,000.01 / MANAGER REVIEW | 1,000.01 / MANAGER REVIEW | PASS | boundary: 0.01 above the manager limit |
| 16 | 10000.01 / 0 / 0 | 10,000.01 / DIRECTOR APPROVAL | 10,000.01 / DIRECTOR APPROVAL | PASS | boundary: 0.01 above the director limit |
| 17 | 100.00 / 10 / 105.00 | 5.00 / AUTO-APPROVED | 5.00 / AUTO-APPROVED | PASS | discount larger than the subtotal, but the tax keeps the total positive |
| 18 | 897.00 / 12.5 / 9.13 | 1,000.00 / MANAGER REVIEW | 1,000.00 / MANAGER REVIEW | PASS | tax of exactly 112.125 rounds half up to 112.13, so the total lands on the limit (half-even or float would give 999.99) |

18 of 18 cases passed.

## Results: input validation (3 cases)

A rejected answer makes the script print a message and ask the same question again. "Rejected" counts those messages; the total is the result of the invoice once every answer is accepted.

| # | Lines typed | Expected: rejected / total | Actual: rejected / total | Passed? | What the case checks |
|---|---|---|---|---|---|
| V1 | 'INV-1' / 'S' / '1.500' / '1250,50' / '12,5' / '100' | 1 / 1,306.81 | 1 / 1,306.81 | PASS | three decimals rejected; decimal comma accepted for money and rate |
| V2 | 'INV-1' / 'S' / '100' / '101' / '100' / '0' | 1 / 200.00 | 1 / 200.00 | PASS | tax rate above 100 rejected, 100 accepted |
| V3 | '  ' / 'INV-1' / 'S' / 'abc' / '-5' / 'nan' / '-0' / '1_000' / '1e3' / '10' / '0' / '0' | 7 / 10.00 | 7 / 10.00 | PASS | empty text, letters, negative, nan, -0, underscore and exponent rejected |

3 of 3 input cases passed.

## What the cases cover

Each of the three limits of the rule has the last value of the lower level, the first value of the higher level, and at least one case that reaches the limit through the calculation.

| Limit | Last value of the lower level | First value of the higher level | Reached through the calculation |
|---|---|---|---|
| 0.00 (REJECTED / AUTO-APPROVED) | case 9: total 0.00; case 14: total -0.01 | case 13: total 0.01 | case 10: negative total; case 12: zero total after rounding |
| 1,000.00 (AUTO-APPROVED / MANAGER REVIEW) | case 2: total 999.99 | case 4: total 1,000.00; case 15: total 1,000.01 | case 3: tax crosses the limit; cases 5, 11 and 18: total of exactly 1,000.00 |
| 10,000.00 (MANAGER REVIEW / DIRECTOR APPROVAL) | case 6: total 9,999.99 | case 7: total 10,000.00; case 16: total 10,000.01 | case 8: tax crosses the limit |

All four outcomes appear in at least two cases. Case 1 is the ordinary invoice in the middle of the first range. Cases 17 and 18 cover the two rules that are easy to get wrong without touching a limit by a whole amount: a discount larger than the subtotal (BR-2) and the half-cent tie (BR-1).

## How the cases were validated

A table that passes proves little if it would also pass on a broken program. Each change below was applied on its own to a copy of `invoiceguard.py` kept outside the repository, and the same runner (both tables) was run against that copy. A useful table has to fail on every change.

| Id | Change made to the copy | Cases that fail |
|---|---|---|
| M01 | AUTO-APPROVED test `<` becomes `<=` | 4, 5, 11, 18 |
| M02 | MANAGER REVIEW test `<` becomes `<=` | 7 |
| M03 | REJECTED test `<= 0` becomes `< 0` | 9, 12 |
| M04 | AUTO-APPROVED test compares `subtotal` instead of `total_payable` | 3, 11, 18 |
| M05 | MANAGER REVIEW test compares `subtotal` instead of `total_payable` | 8 |
| M06 | REJECTED test becomes `< -1000000`, so the branch never fires | 9, 10, 12, 14 |
| M07 | tax computed on `subtotal - discount` (breaks BR-1) | 5, 10, 12, 17, 18, V1 |
| M08 | `APPROVAL_LIMIT_AUTO` changed from 1000.00 to 1001.00 | 4, 5, 11, 15, 18 |
| M09 | `APPROVAL_LIMIT_MANAGER` changed from 10000.00 to 9999.99 | 6 |
| M10 | total = subtotal - tax - discount | 1, 3, 5, 8, 10, 11, 12, 17, 18, V1, V2 |
| M11 | tax not rounded to cents (`quantize` removed) | 11, 18 |
| M12 | tax rate not divided by 100 | 1, 3, 5, 8, 10, 11, 12, 17, 18, V1, V2 |
| M13 | rounding mode `ROUND_HALF_UP` becomes `ROUND_HALF_EVEN` | 18 |
| M14 | REJECTED test `<= 0` becomes `<= 0.01` | 13 |
| M15 | rounding mode `ROUND_HALF_UP` becomes `ROUND_DOWN` | 11, 18 |
| M16 | tax rate has no upper limit of 100 | V2 |
| M17 | input pattern accepts three decimals | V1 |
| M18 | decimal comma is not converted to a point | V1 |

All 18 changes are caught; none survives.

**How the table got to 18 cases.**

- The first ten cases were written straight from the rule table. Run against the first version of the script (which used `float` and `round()`), the same kind of change let four through: removing the rounding (M11), removing it from the total only, removing it from the tax only, and `<= 0` becoming `<= 0.01`. Cases 11, 12 and 13 were added to catch them.
- Cases 14 to 17 came from an independent review of the test design (log entry in [ai-log.md](ai-log.md)): the two edges next to zero and the two edges next to the limits, and a discount larger than the subtotal.
- Case 18 was added after the group chose `Decimal` with half-up rounding. It is the only case that separates half-up from half-even (M13).
- Case 16 is a completeness case: no change in the table fails on it alone, because case 7 and case 6 already guard the same limit.
- The validation cases V1 to V3 were added with the input checks, and are what catches M16, M17 and M18.
