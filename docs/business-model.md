# InvoiceGuard: business model

Deliverables 1.1 (business problem), 1.2 (IPO model) and 2.1 (decision rule) of the Summative Assessment - LO 1.
The company, the suppliers and all amounts in this project are fictional.

## 1.1 Business problem

**Business context.** The accounts payable (AP) team of a small business receives invoices from suppliers every week. Before a payment is approved, an analyst has to work out the amount that is actually payable for the invoice and decide who is allowed to authorize it. Today both steps are done by hand.

**Problem.** For one invoice at a time, the analyst must (1) calculate the tax and the final amount to pay (subtotal + tax - discount) and (2) decide which approval level that amount needs. Done by hand this is slow and error-prone: a wrong total means paying the wrong amount, and a wrong approval level means a payment authorized by someone who is not allowed to authorize it. InvoiceGuard does both steps for a single invoice, in BRL. Line items, due dates, comparison with the total printed on the supplier invoice and the payment itself are out of scope.

**Purpose.** Support one decision: can this invoice be paid now, or does it need to go up or be sent back first? The program gives the analyst the total payable and one of four outcomes (auto-approve, manager review, director approval, reject), so that the invoice is paid for the right amount and signed off by the right authority.

## 1.2 IPO model

One run handles one invoice, then the program ends.

### Input

The program asks for five values, in this order, and asks again when an answer is not accepted (nothing is calculated until all five are valid). All five are required: with no discount, type `0`.

| Variable | Description | Type | Unit, format and accepted values | Example |
|---|---|---|---|---|
| `invoice_number` | Identifier printed on the supplier invoice | text | any text that is not empty; used only as a label | `INV-2026-0042` |
| `supplier_name` | Supplier that issued the invoice | text | any text that is not empty; used only as a label | `Acme Ltda` |
| `subtotal` | Amount charged before tax and discount | decimal number | BRL; digits with an optional decimal point or comma and 1 or 2 decimals; 0 or more; no thousands separator, no `R$` | `1250.50` |
| `tax_rate` | Tax rate applied on the subtotal | decimal number | percent: 12.5 means 12.5%, not 0.125; same format as above; from 0 to 100 | `12.5` |
| `discount` | Discount granted by the supplier | decimal number | BRL; same format as `subtotal`; 0 or more | `100.00` |

"2 decimals" means at most two: `100`, `100.5` and `100.50` are all valid. An answer that does not match is rejected with a message and the same question is asked again. That covers letters, empty text, a minus sign, `nan`, `inf`, exponents such as `1e3`, three or more decimals such as `1.500`, and a tax rate above 100. A discount larger than the subtotal is valid (see BR-2).

### Processing

1. Read and validate the five inputs. The three numbers are converted to exact decimal numbers (Python `Decimal`), not to `float`.
2. `tax_value = subtotal * tax_rate / 100`, rounded to cents, half a cent going up (BR-1).
3. `total_payable = subtotal + tax_value - discount` (BR-2). All three terms are whole cents, so no further rounding is needed.
4. Compare `total_payable` with the approval limits and set `approval_status` (BR-3, detailed in section 2.1).

### Output

The program prints one labeled block with one line per field, in this order. Every amount carries its unit, uses a comma as thousands separator and a point before the two decimals. A negative total is printed with a minus sign after `BRL`.

| Field | Unit and format | Example |
|---|---|---|
| Invoice number | text, as typed (leading and trailing spaces removed) | `INV-2026-0042` |
| Supplier | text, as typed (leading and trailing spaces removed) | `Acme Ltda` |
| Subtotal | `BRL` + thousands separator + 2 decimals | `BRL 1,250.50` |
| Tax rate | percent with 2 decimals | `12.50%` |
| Tax value | `BRL` + thousands separator + 2 decimals | `BRL 156.31` |
| Discount | `BRL` + thousands separator + 2 decimals | `BRL 100.00` |
| Total payable | `BRL` + thousands separator + 2 decimals; `BRL -85.00` when negative | `BRL 1,306.81` |
| Approval status | one of `AUTO-APPROVED`, `MANAGER REVIEW`, `DIRECTOR APPROVAL`, `REJECTED` | `MANAGER REVIEW` |

Literal example for subtotal 1250.50, tax rate 12.5 and discount 100:

```text
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

### Business rules

| Id | Rule |
|---|---|
| BR-1 | The tax is calculated on the subtotal, before the discount, and rounded to cents. A tax that falls exactly on half a cent is rounded up (112.125 becomes 112.13). The calculation is exact, with no binary floating point. |
| BR-2 | Total payable = subtotal + tax value - discount. It can be zero or negative when the discount is larger than subtotal + tax. |
| BR-3 | The approval level is decided by the total payable, not by the subtotal (section 2.1). |

Worked example: subtotal 1250.50, tax rate 12.5, discount 100.00. Tax = 1250.50 x 12.5% = 156.3125, rounded to 156.31. Total = 1250.50 + 156.31 - 100.00 = 1,306.81. That is at least 1,000.00 and at most 9,999.99, so the status is `MANAGER REVIEW`.

Why the rounding rule is written down: with 897.00 at 12.5% the exact tax is 112.125. Rounded half up it is 112.13, the total with a 9.13 discount is exactly 1,000.00 and the invoice needs a manager. Rounded to the even cent (112.12), which is what Python's `round()` and a `float` give, the total is 999.99 and the same invoice would be approved by the analyst alone.

**Policy assumptions.** The tax base (before the discount) comes from the TE1 invoice pipeline of this course and is kept as a business decision of the group; it is not claimed to be a tax-law rule. The maximum tax rate of 100 and the decimal comma are also choices made for this program.

## 2.1 Decision rule

**Question the rule answers:** which approval level does this invoice need?

**Value that decides:** the total payable after rounding to cents (BR-2), never the subtotal. An invoice of 950.00 with 10% tax has a subtotal below 1,000.00 but a total of 1,045.00, and it must go to the manager.

| Total payable (BRL) | Approval status | What happens |
|---|---|---|
| 0.00 or less (`<= 0.00`) | `REJECTED` | Nothing is payable; the invoice goes back to AP for review. This is the only trigger for `REJECTED`: invalid typing never reaches the rule, because it is asked again. |
| 0.01 up to 999.99 (`> 0.00` and `< 1,000.00`) | `AUTO-APPROVED` | The analyst releases the payment alone |
| 1,000.00 up to 9,999.99 (`>= 1,000.00` and `< 10,000.00`) | `MANAGER REVIEW` | A manager must approve |
| 10,000.00 or more (`>= 10,000.00`) | `DIRECTOR APPROVAL` | A director must approve |

**Equality.** A total exactly equal to a limit goes to the higher level: 1,000.00 is `MANAGER REVIEW` and 10,000.00 is `DIRECTOR APPROVAL`. A total of exactly 0.00 is `REJECTED`.

**Rounding.** The tax is rounded to cents (BR-1) before the total is formed, so the total is always a whole number of cents and the comparison with a limit is exact.

**Order of the branches** in [`invoiceguard.py`](../invoiceguard.py):

1. `if total_payable <= 0` comes first. Otherwise a zero or negative total would be caught by `< APPROVAL_LIMIT_AUTO` and wrongly auto-approved.
2. `elif total_payable < APPROVAL_LIMIT_AUTO` (1,000.00). The lower bound is already guaranteed by the first branch.
3. `elif total_payable < APPROVAL_LIMIT_MANAGER` (10,000.00). The lower bound is guaranteed by the second branch.
4. `else` is everything from 10,000.00 up.

The limits are tested with `<`, not `<=`, which is what makes an equal value move up to the next level. The chain only works while `APPROVAL_LIMIT_AUTO` is smaller than `APPROVAL_LIMIT_MANAGER`; the script says so in a comment.

**Policy assumption.** BRL 1,000.00 and BRL 10,000.00 are approval limits assumed by the group for this fictional company. They are the named constants `APPROVAL_LIMIT_AUTO` and `APPROVAL_LIMIT_MANAGER` at the top of the script, so changing the policy means changing two lines.
