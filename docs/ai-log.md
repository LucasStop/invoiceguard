# InvoiceGuard: AI use log

Deliverables 1.4 (AI log for the IPO model and the script) and 2.4 (AI log for the decision rule and the tests) of the Summative Assessment - LO 1, plus the AI-use declaration.

## Declaration of AI use (CONSUN 274/2024)

During the preparation of this activity, the group used Claude (Anthropic; Claude Code CLI, model Claude Sonnet 5.5) to draft the first version of the documents, the script and the test runner, to review the IPO model, the script and the decision rule, and to suggest test cases. Every suggestion listed below was read by the group, and what was accepted or rejected is recorded with the reason. The group takes full responsibility for the content submitted.

Review status of this log: author Lucas Stopinski da Silva reviewed it. Eduardo Pereira and Patrick de Oliveira reviewed the whole project (documents, script, tests and this log) and approved it with Lucas outside the repository, as reported by Lucas on 2026-10-17. According to Lucas, the prompts were written and reviewed by the three members together in one shared session, so there are no separate prompts per member, see "Additions by the other members" at the end.

## How the log was produced

- The first version of `docs/business-model.md`, `invoiceguard.py`, `test_invoiceguard.py` and `docs/test-cases.md` was written by Claude Code from the group context. It used `float` and `round()`, free-text input and 10 test cases.
- Afterwards, four reviews (A to D) were run, each in a **new Claude Sonnet 5.5 session** that had no access to the repository and none of the earlier conversation. Each prompt starts with "I am a beginner Python student..." and contains only the part of the project that is being reviewed. Each response was saved as received. Quotes below are literal; everything else is a summary.
- The reviews ran on the first (`float`) version, so some findings are already gone from the current files; the "Decision" column says what each one changed.
- Interactions marked **Claude Code** are findings made while building and checking the project in the main session, not answers of the review sessions.

## Part 1: IPO model and script (deliverable 1.4)

### Prompt A: review of the IPO model (sections 1.1 and 1.2 only, no code)

Prompt: asked for a review of the business problem and IPO table only, listing missing or unclear inputs, outputs, units, formats and rules, and asked for no code.

Relevant response: the calculation half of the IPO "is solid", but the decision half and the edge cases are "not specified enough for someone to write the program without guessing". It listed missing limits with their edges, no trigger for REJECTED, zero and negative totals, invalid input, a "confirm the amount" step with no input behind it, one invoice per run, "2 decimals" exact or at most, accepted characters (`1250,50`, `R$`, `nan`, `1e3`), no upper limits, inconsistent thousands separator, no literal sample output, and two ambiguities: the tax base and the half-cent rule ("`round(..., 2)` in the IPO does not settle which rule the business wants"). Its top three priorities: limits table and REJECTED triggers; zero, negative and invalid input; rounding rule and tax base.

| Suggestion | Decision | Why | Implementation it led to |
|---|---|---|---|
| Limits table with each edge marked inclusive or exclusive | Accepted | Without it the boundary cases cannot be written from the rule | Table in section 2.1 with `>=`/`<` per row; constants `APPROVAL_LIMIT_AUTO` and `APPROVAL_LIMIT_MANAGER` |
| Trigger for REJECTED and one-line meaning of each status | Accepted | A total of zero or less would otherwise be auto-approved | REJECTED = total `<= 0.00`, first branch of the chain; "What happens" column in 2.1 |
| Separate "invalid input" from REJECTED; say which fields are required | Accepted | A typing problem is not a business decision | Re-ask loop (`read_text`, `read_number`); all five inputs required, `0` for no discount |
| Format of the negative total, one thousands-separator rule, literal sample output | Accepted | A programmer should not have to guess the layout | `BRL -85.00` rule, `:,.2f` on every amount, literal example block in 1.2 |
| "2 decimals" at most or exactly | Accepted: at most 2 | Typing `100` for a whole amount is natural | Pattern `[0-9]+([.,][0-9]{1,2})?` |
| One invoice per run | Accepted | The script has no loop over invoices | Stated in 1.2; known limitation in the README |
| Name the half-cent rule and the tax base in BR-1 | Accepted | The same invoice gives different statuses depending on the rule (see B) | BR-1 rewritten; `Decimal` with `ROUND_HALF_UP`; tax on the subtotal, before the discount, stated as a group policy |
| Remove "confirm the amount the supplier is charging" or add an input for it | Accepted the removal, rejected the extra input | Comparing against the printed total adds an input, a tolerance and a mismatch outcome that the LO 1 problem does not need | 1.1 rewritten; comparison with the printed total declared out of scope |
| Accept `R$`, `%` and `1.250,50` | Rejected | Extra parsing for a program that runs once on typed values; the decimal comma is enough | Strict pattern; the format is written in 1.2 |
| Warn when the rate looks like 0.125 instead of 12.5 | Rejected | A warning needs a second rule that is not part of the business problem | README limitation: `0.125` is read as 0.125% |
| Print a reason line for REJECTED | Rejected | Only one trigger exists, so the reason is always the same | None |

Notes. The review had only sections 1.1 and 1.2, so it could not see BR-2 or section 2.1. The 8888.88 and 8888.89 example it gave (totals 9,999.99 and 10,000.00 at 12.5%) was checked by the group before being used.

Decisions in the table above (Prompt A) are the defaults implemented by Claude Code; Lucas confirmed them on 2026-10-14 without giving a separate reason (see the list near the end).

### Prompt B: the course debug prompt, run on the script

Prompt: the instructor's debug prompt, literally: "Review the following beginner-level Python code. Identify possible syntax errors, logic errors, and input validation problems. Do not rewrite the entire code unless necessary. Explain each problem and each suggested correction." followed by the first `invoiceguard.py` (`float`, `round()`, bare `input()` and `float()`). The session saw the code only, no documents.

Relevant response: no syntax error. The logic was judged correct ("Tax is computed on the subtotal and the discount is subtracted afterwards"; `<= 0` first; `<` at the limits). The weak point was `round()` on floats: "`round(2.675, 2)` gives 2.67, not 2.68", ties go to the even cent, so 112.125 becomes 112.12. It proposed `Decimal` with an explicit rounding mode ("Choose whichever mode your rule requires") and a validated reader. Six input problems: (1) text, empty or `12,5` raises `ValueError`; (2) `nan` and `inf` are accepted (`nan` ends in DIRECTOR APPROVAL); (3) negative values are accepted (a negative discount works as a surcharge); (4) no upper limits; (5) empty text; (6) `1.500` read as 1.5. It ended with: "worth confirming with whoever owns BR-1" whether tax before the discount is intended.

Concrete case found by Claude Code while checking this response (the review gave only the 12.5% rate; the amounts are Claude Code's): subtotal 897.00, tax rate 12.5, discount 9.13. Exact tax 112.125. With `float`, 112.12, total 999.99, `AUTO-APPROVED`. With half up, 112.13, total 1,000.00, `MANAGER REVIEW`. The same invoice reaches a different approver.

| Suggestion | Decision | Why | Implementation it led to |
|---|---|---|---|
| Use `Decimal` and an explicit rounding mode instead of `float` and `round()` | Accepted, with `ROUND_HALF_UP` | The group's reason: it does not interfere with the plan or with how the code runs, so the exact type costs nothing. Added fact: the 897.00 case above changes the approval level | `from decimal import Decimal, ROUND_HALF_UP`; `quantize(CENT, rounding=ROUND_HALF_UP)`; test case 18 |
| Ask again instead of crashing on bad input | Accepted | The group's reason: it makes the program more complete | `read_text` and `read_number` loops; validation cases V1 to V3 |
| Reject empty text (`strip()`, not empty) | Accepted | Labels must not be blank | `read_text` |
| Reject `nan`, `inf`, negatives, more than 2 decimals | Accepted, but done with a regex and not with the suggested `Decimal(...)` checks | One pattern covers all of it and also `1e3`, which a `Decimal` check lets through as a number | `re.fullmatch(r"[0-9]+([.,][0-9]{1,2})?", text)` |
| Tax rate at most 100 | Proposed default, group confirmation pending | A rate above 100% is almost surely a typing error | `MAX_TAX_RATE = Decimal("100")`; V2; mutant M16 |
| Limit the discount to the subtotal (`maximum=subtotal`) | Rejected | The review did not see BR-2: the business rule allows a discount larger than the subtotal, because the total only has to be zero or less to be REJECTED. The suggestion would also make the invoice in cases 10, 12 and 17 impossible to type | No cap on the discount; BR-2 and README limitation say so |
| Confirm the tax base with the owner of BR-1 | Accepted as a documented assumption | No process owner exists in a course project | "Policy assumptions" in 1.2; tax base is not claimed as a tax-law rule |

Check made by the group. The suggested validator was run as received on the test table (copy kept outside the repository). It passed 11 of 13 cases of the first table: cases 10 and 12 break because the discount cap makes the script ask again and the runner's stdin ends (`EOFError`). Without the cap it passed 13 of 13. That is the evidence behind the rejection above.

Findings by **Claude Code**, not by review B: the suggested validator accepts `-0` (it printed `BRL -0.00`) and `1_000`, and the re-ask loop gives `EOFError` when the input ends. The regex removed the first two; the third is documented as a limit ("one invoice per run").

## Part 2: decision rule and tests (deliverable 2.4)

### Prompt C: review of the `if/elif/else` chain

Prompt: asked for a review of the branch chain only, to show only the lines that would change, and to check the order of the branches and the operators at the boundaries.

Relevant response: "Your chain is correct. The order of the branches and all three operators match section 2.1... so nothing has to change." It checked nine boundary totals (-0.01, 0.00, 0.01, 999.99, 1,000.00, 1,000.01, 9,999.99, 10,000.00, 10,000.01); all matched. It explained why `<= 0` must come first and why the other two tests use `<`. Two remarks: the chain "only works while `APPROVAL_LIMIT_AUTO` is smaller than `APPROVAL_LIMIT_MANAGER`", and `nan` would fall into `else` (DIRECTOR APPROVAL). Optional change: `if not total_payable > 0`.

| Suggestion | Decision | Why | Implementation it led to |
|---|---|---|---|
| Keep the chain as it is | Accepted | The nine boundary checks agree with the table in 2.1 | No change in the order or operators |
| Say that the chain needs `AUTO < MANAGER` | Accepted | If the constants were swapped, MANAGER REVIEW would never be reached | Comment above the chain in `invoiceguard.py`; one sentence in 2.1 |
| `if not total_payable > 0` so that `nan` is REJECTED | Rejected | With the regex and `Decimal`, `nan` never reaches the chain, and section 2.1 and the tests are written with `<= 0` | `if total_payable <= 0` kept |
| The `else` always sets `approval_status` | Noted | No `NameError` is possible in the output block | None |

The review itself did not change any logic; its value is the check of the nine boundaries and the dependency between the two constants.

### Prompt D: boundary test cases

Prompt: asked for a table of boundary test cases for the four-level rule, at least three values for each rule, with the expected result worked out from the rule and not from any code. The session did not see the existing 13 cases.

Relevant response: 14 cases (R1 to R3, A1 to A3, M1 to M5, D1 to D3), each limit with one cent below, exactly on and one cent above. It said it ran no code. It also avoided half-cent ties and advised: "Decide the convention first, then add a test for it."

Check made by the group: all 14 expected values were run against the script (`float` version and the current `Decimal` version); there were no differences. The group did not copy the table: only the cases that were new for the existing table were added.

| Suggestion | Decision | Why | Implementation it led to |
|---|---|---|---|
| R2: 100.00 / 0 / 100.01, total -0.01 | Accepted | The nearest negative total; the existing table had no value just under zero | Test case 14 |
| M3: 1000.01 / 0 / 0 | Accepted | One cent above the manager limit was missing | Test case 15 |
| D2: 10000.01 / 0 / 0 | Accepted | One cent above the director limit was missing | Test case 16 (kept for completeness: cases 6 and 7 already fail on the same mutants) |
| A2: 100.00 / 10 / 105.00, total 5.00 | Accepted | Shows that rejection depends on the total and not on "discount larger than subtotal" | Test case 17; it is also why the discount cap of B was rejected |
| A3, M1, M4, M5, R3, A1, M2, R1 | Not added | Same input or same boundary as cases 2, 5, 3, 6, 9, 13, 11 and 10 | None |
| D1: 9000 / 12.5 / 125 and D3: 50000 / 12.5 / 1000 | Not added | They test the same limits as cases 7 and 8 and no change to the script depends on them | None |
| Decide the half-cent convention and test it | Accepted | After the `Decimal` decision (B), half up is the rule, so it needs a case | Test case 18: 897.00 / 12.5 / 9.13 (tax 112.125, total 1,000.00, MANAGER REVIEW); it is the only case that tells half up from half even (mutant M13) |

## Interactions with Claude Code in the main session

| Prompt (author's request) | AI response (summary) | Decision |
|---|---|---|
| Build the repository for the Summative Assessment from the Canvas rubric | Plan with the files, the four-level rule, 10 cases, plain script, `float` | Plan approved. Later changed to `Decimal` and a re-ask loop (see B) |
| Run a change-by-change check on a copy of the script (a "mutation check") to see whether the table can fail | First table (10 cases) let four changes through: no rounding, no rounding in the total only, no rounding in the tax only, `<= 0` as `<= 0.01` | Cases 11, 12 and 13 added. The same check on the final version: 18 of 18 changes caught (table in [test-cases.md](test-cases.md)) |
| Check the suggested validator against the test table and fix what fails | Found `-0`, `1_000` and `EOFError` in the suggested validator (see B); added V1 to V3 and mutants M16 to M18 | Regex reader; `.5`, `5.` and `+5` are also rejected and documented ("type `0.5`") |
| Rewrite the documents so that the IPO stands on its own | Moved limits, status meaning, literal output, half-up and tax base from the review of A into 1.2 and 2.1 | Applied; the group reviews the text |

## Defaults proposed by Claude Code, confirmed by Lucas

These were implemented as defaults and confirmed by Lucas on 2026-10-14 (no reason given beyond the confirmation). Eduardo and Patrick can still ask to change any of them:

- Tax rate limited to 100 and decimal comma accepted (B, A).
- No cap on the discount (reason in B: BR-2 and cases 10, 12, 17).
- Strict number format without `R$`, `%` or thousands separator (A).
- Tax on the subtotal before the discount, carried over from the TE1 pipeline (A, B).
- Total of exactly 0.00 is REJECTED; limits 1,000.00 and 10,000.00 are assumed for a fictional company.
- Test table of 18 cases and 3 validation cases, with the additions and the rejections of D.

## Additions by the other members

Eduardo Pereira and Patrick de Oliveira reviewed the whole project and approved it with Lucas (verbal approval, outside the repository, reported by Lucas on 2026-10-17). According to Lucas, the prompts were not made separately: the three members wrote and reviewed them together in one shared session. There are therefore no additional entries per member, and every AI interaction of this project is the one recorded above.
