# InvoiceGuard: AI use log

Deliverables 1.4 and 2.4 of the Summative Assessment - LO 1 (parts 1 and 2), and 4.4 and 5.4 of the Summative Assessment - LO 2 (parts 3 and 4), plus the AI-use declaration.

## Declaration of AI use (CONSUN 274/2024)

During the preparation of this activity, the group used Claude (Anthropic; Claude Code CLI, model Claude Sonnet 5.5) to draft the first version of the documents, the script and the test runner, to review the IPO model, the script and the decision rule, and to suggest test cases (LO 1); and, for LO 2, to plan the batch workflow, write the modules, the tests and the documents of ST4 and ST5, in Claude Code sessions on 2026-11-22 and 2026-11-23. Every suggestion listed below was read by the group, and what was accepted or rejected is recorded with the reason. The group takes full responsibility for the content submitted.

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

## Part 3: batch processing, workbook, report and robustness (deliverable 4.4, ST4)

Tool: Claude Code CLI, model Claude Sonnet 5.5. The prompts were written and reviewed by the three members together in one shared session on 2026-11-23, as reported by Lucas, so there is one record for the group. Source of the requirements: the Canvas task "Summative Assessment - LO 2" and its rubric, read on 2026-11-23. The ST3 deliverable is not in this repository, so "reuse of ST3" means reuse of the LO1 validation and a grouping written in the ST3 style; see "Adaptations of the ST3 logic" in the README.

### Prompt E: review of the RA2 plan

Prompt: the plan text prepared in the previous session, with the request "review it and tell us if we can proceed and what we must do". Claude read `docs/plano-ra2.md`, `invoiceguard.py` and `test_invoiceguard.py`.

Relevant response: the plan is coherent and can proceed, with four changes. First, `invoiceguard.py` runs `input()` at module level, so it cannot be imported and "reuse" has to mean rewriting BR-1 to BR-3 as pure functions. Second, the total in BRL must be the total in the invoice currency times the rate, rounded again to cents. Third, the national holiday of 2026-11-20 and the weekend are good data for the date fallback. Fourth, if time runs out, merge `workflow.py` into `run.py`. After reading the Canvas rubric, Claude added: the AI log needs separate ST4 and ST5 records, `source_file` must be in every output, and the workbook must be verified against the CSV.

| Suggestion | Decision | Why | Test or data check | Observed result and limitation |
|---|---|---|---|---|
| Rewrite BR-1 to BR-3 as pure functions in `src/rules.py`, leave `invoiceguard.py` untouched | Accepted | The script cannot be imported; the LO1 deliverable must stay as submitted | `tests/test_rules.py` runs the same 18 hand-written LO1 cases against the module | 18 of 18 give the same total and level. Limit: the rule now exists in two places, the script and the module, and a change must be made in both |
| Add a "level if read as BRL" column | Accepted | It shows what the exchange rate changes, which is the business question | `test_rate_changes_the_level` (USD 1,900.00 x 5.50 = 10,450.00, DIRECTOR APPROVAL against MANAGER REVIEW) | Passes; in the real batch 10 of 15 foreign invoices change level |
| Merge `workflow.py` into `run.py` if time is short | Rejected for now | There was time, and separate named functions are asked in rubric 5.3 | `tests/test_workflow.py` calls `run()` directly, which is only possible with the split | Kept as two files |

### Prompt F: input validation and error reporting of the batch

Prompt: build `src/loader.py` for two or more CSVs with at least three justified validation rules, where one rejected input stops the whole batch.

Relevant response and decision: five rules (columns present and no extra cells, unique invoice number across the batch, currency in BRL, USD or EUR, ISO date not in the future, LO1 number format with tax rate at most 100). Claude proposed to list every problem of the batch in one error and not to stop at the first.

| Suggestion | Decision | Why | Test or data check | Observed result and limitation |
|---|---|---|---|---|
| Report all problems with file and line, then reject the batch | Accepted | The user can fix a file in one pass; the batch still stops as the rubric requires | `test_error_names_every_problem_not_just_the_first` | Three problems of two rows listed together |
| One invalid-case fixture folder per error | Rejected | Eight small folders for eight one-line files; the cases are written in the test and only the demo fixture `tests/fixtures/invalid_value` stays | the loader tests (10 tests) | Pass. Limit: the other invalid files are not on disk for the audience to open |
| Use pandas to read the CSVs | Rejected | The `csv` module is enough for the checks, and the DataFrame is needed only after integration | `test_two_valid_files_load_in_one_call_with_source_filenames` | Pass; the amounts stay exact `Decimal` |

### Prompt G: workbook, report and atomic publication

Prompt: write the processed CSV, the workbook with a detail and a summary sheet, the text report, the log, and keep incomplete results apart from completed ones.

| Suggestion | Decision | Why | Test or data check | Observed result and limitation |
|---|---|---|---|---|
| Summary by currency and approval level sorted by BRL total, in the style of an ST3 grouping | Accepted | A meaningful metric for the accounts payable user | `test_sheets_are_numeric_formatted_frozen_filtered_and_summary_sorted` (sorted, total 195,519.01) | Pass. Limit: no grand-total row, because it would break the filter and the sort |
| Reopen the workbook and the CSV and compare counts and totals before publishing | Accepted | The rubric asks to verify the workbook against the processed data | `test_verification_catches_a_changed_value` (one cell changed by 1); break 3 of the mutation table | The change is detected; with the check disabled the test fails |
| Build in `output/incomplete/<id>` and publish with `os.replace` to `output/runs/<id>` | Accepted | A failed run must not look completed, and earlier runs must survive | tests 5 and 6 in [test-cases-ra2.md](test-cases-ra2.md); break 4 of the mutation table | No partial package in `runs/` in any failure test. Limit: a crash of the machine in the middle of the final rename is not simulated |
| Write the run status into `latest.txt` | Accepted | The rubric asks how users find the latest run and its status | `test_package_has_every_output_and_latest_says_success`, `test_invalid_input_fails_visibly_and_keeps_earlier_success` | `status`, `mode`, `location` and `last_success` as expected. Limit: the file is read by people, not by another program |

## Part 4: API, integration and workflow (deliverable 5.4, ST5)

### Prompt H: choice and use of the external source

Prompt: find a documented API that answers a question the local invoices cannot (the BRL value of foreign-currency invoices). Claude chose the PTAX of the Banco Central do Brasil in the plan, and called it for real on 2026-11-22 and again on 2026-11-23.

Relevant response: the API needs no key; the currency parameter is `moeda`, not `codigoMoeda` (HTTP 400); weekends and holidays return an empty list; there are five bulletins per business day.

| Suggestion | Decision | Why | Test or data check | Observed result and limitation |
|---|---|---|---|---|
| Use the selling rate of the closing bulletin | Accepted as a team assumption, not yet confirmed by Eduardo and Patrick in the repository | The company buys currency to pay the supplier; the rule is stated as an assumption in `docs/source-record.md` | Real response checked by hand: 2026-11-06 USD closing selling rate 5.5013 | Another rate type would change totals; the assumption is in the report as a limitation |
| One request per currency for the whole date window | Accepted | Two calls instead of one per invoice date | `test_request_has_parameters_and_timeout`; the live run saved the USD and EUR responses in `data/raw` | Pass. Limit: the window is the first invoice date minus 7 days up to the last date |
| Parse JSON numbers as `Decimal` | Accepted | The rate times the amount must be exact to the cent | `test_keeps_only_closing_bulletins_with_exact_decimal_rates` (5.4935 equals `Decimal("5.4935")`) | Pass |
| Validate the response before saving it | Accepted | A bad answer must never overwrite the last good one | `test_failed_live_run_does_not_replace_the_saved_response` | Saved file unchanged after an invalid live response |
| Read a saved response in a second mode | Accepted | The demo must not depend on the network | `test_live_then_saved_gives_the_same_rates` | Same rates in both modes. Limit: if the batch dates move outside the saved window, saved mode fails with a clear message |
| Check the licence before citing it | Accepted | The rubric asks for use conditions | the dataset page of dadosabertos.bcb.gov.br, read on 2026-11-23, states ODbL | Recorded in `docs/source-record.md`; the text of the licence itself was not read in full |

### Prompt I: integration key, fallback and reconciliation

Prompt: join invoices and rates, say what one row means in each source, define the key, check uniqueness, cardinality and missing matches, and prove counts and totals are preserved.

| Suggestion | Decision | Why | Test or data check | Observed result and limitation |
|---|---|---|---|---|
| Key `(currency, rate_date)` where `rate_date` is the issue date or the last business day within 7 days | Accepted | Gives the weekend and holiday cases a rule and keeps the key explicit | `test_weekend_falls_back_to_last_business_day`; real batch: 4 fallback rows (2026-11-02, 11-07, 11-15, 11-20) | Pass. Limit: the 7-day window is a choice |
| Use `pandas.merge_asof` for the date fallback | Rejected | It hides the window and the key that rubric 5.2 asks to explain; a plain lookup is easier to defend | `test_no_rate_in_window_rejects_with_invoice_numbers` | Invoices with no rate are listed by number |
| `validate="many_to_one"` on the merge | Accepted as a second safety net | Many invoices share one rate | `test_many_invoices_one_rate_keeps_row_count_and_totals`; break 5 of the mutation table | Pass. The break survived because the explicit duplicate check runs first, so the argument alone is not what stops a duplicate |
| Compare row count and totals by currency before and after the merge | Accepted | Proves nothing was lost or inflated | the same test plus `SavedRealDataTest` (24 rows before and after) | 24 of 24, totals by currency equal |
| Tune the sample amounts with the real rates | Accepted | To have invoices that change level and one just under the limit | hand calculation: 1780.00 x 5.6143 = 9,993.454 -> 9,993.45 (INV-B006) | Matches the integrated CSV |

### Prompt J: one command for the workflow

Prompt: connect acquisition, validation, integration and storage in named functions with one documented command.

| Suggestion | Decision | Why | Test or data check | Observed result and limitation |
|---|---|---|---|---|
| `python3 run.py --mode live` or `--mode saved`, source mode in the log, the report and the CSV | Accepted | Rubric 5.3 asks to identify the source mode | `test_totals_match_hand_calculation_in_every_output`; `run.log` lines | Mode appears in all three |
| Run one controlled failure for the demo (`--input tests/fixtures/invalid_value`) | Accepted | Shows the error, the log and the preserved earlier success | run by hand on 2026-11-23: exit code 1, `latest.txt` FAILED, `last_success` unchanged | As expected |
| Try five deliberate breaks to see whether the tests can fail | Accepted | A suite that never fails proves little | table in [test-cases-ra2.md](test-cases-ra2.md) | Four breaks were caught; one was not (see Prompt I) and is reported |

Remaining limitations of parts 3 and 4: the rate type is a team assumption; the data are fictional; the live API is exercised by hand and not by the automated tests; the two copies of the LO1 rule (script and module) must be changed together.
