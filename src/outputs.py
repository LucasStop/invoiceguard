# Output files of a run: processed CSV (ST4), integrated CSV (ST5), workbook, text report.
# All of them are written from the same integrated DataFrame, so they cannot disagree.
import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

PROCESSED_COLUMNS = ["invoice_number", "supplier", "issue_date", "currency", "subtotal", "tax_rate", "discount",
                     "tax_value", "total_foreign", "source_file", "source_line"]
TITLES = {
    "invoice_number": "Invoice", "supplier": "Supplier", "issue_date": "Issue date", "currency": "Currency",
    "subtotal": "Subtotal", "tax_rate": "Tax rate (%)", "discount": "Discount", "tax_value": "Tax value",
    "total_foreign": "Total (invoice currency)", "rate_date": "Rate date", "rate_fallback": "Rate from earlier day",
    "rate": "BRL per unit", "total_brl": "Total payable (BRL)", "approval_status": "Approval level",
    "status_without_fx": "Level if read as BRL", "level_changed_by_fx": "Level changed by FX",
    "source_file": "Source file", "source_line": "Source line", "rate_mode": "Rate source mode",
}
MONEY = {"subtotal", "discount", "tax_value", "total_foreign", "total_brl"}
SUMMARY_COLUMNS = ["Currency", "Approval level", "Invoices", "Total (invoice currency)", "Total payable (BRL)",
                   "Level changed by FX"]
SUMMARY_TITLES_TO_FORMAT = {"Total (invoice currency)": "#,##0.00", "Total payable (BRL)": "#,##0.00", "Invoices": "0",
                            "Level changed by FX": "0"}


def write_csv(frame, columns, path):
    """CSV with Decimal values as exact text and dates as YYYY-MM-DD."""
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for row in frame[columns].itertuples(index=False):
            writer.writerow([_cell_text(v) for v in row])


def _cell_text(value):
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def summarize(frame):
    """ST3-style grouping: invoices and totals by (currency, approval level), biggest BRL total first."""
    groups = defaultdict(lambda: [0, Decimal("0"), Decimal("0"), 0])
    for row in frame.itertuples():
        g = groups[(row.currency, row.approval_status)]
        g[0] += 1
        g[1] += row.total_foreign
        g[2] += row.total_brl
        g[3] += bool(row.level_changed_by_fx)
    ordered = sorted(groups.items(), key=lambda item: (-item[1][2], item[0]))
    return [[currency, status, *values] for (currency, status), values in ordered]


def write_workbook(frame, path):
    """Detail sheet (one row per invoice) and summary sheet, with readable headers, widths, formats, frozen header, filter."""
    workbook = Workbook()
    detail = workbook.active
    detail.title = "Details"
    columns = list(frame.columns)
    _write_sheet(detail, [TITLES[c] for c in columns],
                 [list(row) for row in frame.itertuples(index=False)],
                 {TITLES[c]: ("#,##0.00" if c in MONEY else "0.0000" if c == "rate" else "0.00" if c == "tax_rate"
                              else "yyyy-mm-dd" if c in ("issue_date", "rate_date") else None) for c in columns})
    summary = workbook.create_sheet("Summary")
    _write_sheet(summary, SUMMARY_COLUMNS, summarize(frame), SUMMARY_TITLES_TO_FORMAT)
    workbook.save(path)


def _write_sheet(sheet, headers, rows, formats):
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for index, header in enumerate(headers, start=1):
        letter = get_column_letter(index)
        widest = max([len(header)] + [len(str(c.value)) for c in sheet[letter][1:] if c.value is not None])
        sheet.column_dimensions[letter].width = min(max(widest + 2, 12), 42)
        if formats.get(header):
            for cell in sheet[letter][1:]:
                cell.number_format = formats[header]
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions


def verify_workbook(workbook_path, csv_path, frame):
    """Reopen the saved files and compare them with the integrated data. Raises ValueError on any difference."""
    workbook = load_workbook(workbook_path)
    detail, summary = workbook["Details"], workbook["Summary"]
    for sheet in (detail, summary):
        if sheet.freeze_panes != "A2" or not sheet.auto_filter.ref:
            raise ValueError(f"sheet {sheet.title}: frozen header or filter missing")

    header = [c.value for c in detail[1]]
    brl_index = header.index(TITLES["total_brl"])
    sheet_rows = list(detail.iter_rows(min_row=2, values_only=True))
    if len(sheet_rows) != len(frame):
        raise ValueError(f"workbook has {len(sheet_rows)} detail rows, expected {len(frame)}")
    if not all(isinstance(r[brl_index], (int, float)) for r in sheet_rows):
        raise ValueError("Total payable (BRL) is not numeric in the workbook")
    expected = sum(frame["total_brl"], Decimal("0"))
    sheet_total = sum(Decimal(str(r[brl_index])) for r in sheet_rows)
    summary_total = sum(Decimal(str(r[4])) for r in summary.iter_rows(min_row=2, values_only=True))
    with open(csv_path, newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    csv_total = sum(Decimal(r["total_brl"]) for r in csv_rows)
    if len(csv_rows) != len(frame):
        raise ValueError(f"integrated CSV has {len(csv_rows)} rows, expected {len(frame)}")
    for name, value in (("details sheet", sheet_total), ("summary sheet", summary_total), ("integrated CSV", csv_total)):
        if abs(value - expected) > Decimal("0.005"):
            raise ValueError(f"{name} total {value} differs from the integrated data total {expected}")
    return {"detail_rows": len(sheet_rows), "total_brl": expected}


def build_report(frame, checks, metas, run):
    """Short text report. Part 2 is calculated from the data; part 3 is interpretation and says so."""
    foreign = frame[frame["currency"] != "BRL"]
    changed = frame[frame["level_changed_by_fx"]]
    levels = ["AUTO-APPROVED", "MANAGER REVIEW", "DIRECTOR APPROVAL", "REJECTED"]
    per_file = frame.groupby("source_file").size()
    lines = [
        "InvoiceGuard report: approval routing of supplier invoices",
        f"Run: {run['run_id']}   Rate source mode: {run['mode']}   Status: SUCCESS",
        "",
        "1. Scope",
        "Source files: " + "; ".join(f"{name} ({n} invoices)" for name, n in per_file.items()),
        f"Invoices: {len(frame)}, issue dates {frame['issue_date'].min()} to {frame['issue_date'].max()}, "
        f"currencies {', '.join(sorted(frame['currency'].unique()))}.",
        "External source: Banco Central do Brasil, PTAX (Olinda API), selling rate (cotacaoVenda) of the closing "
        "bulletin, BRL per 1 unit of currency, license ODbL.",
        *[f"  {m['currency']}: acquired {m['acquired_at']} ({m['mode']})" for m in metas],
        "Why it matters: the approval limits are in BRL, so a foreign-currency invoice is routed by its BRL total "
        "on the issue date, not by its face value.",
        "",
        "2. Calculated evidence",
        "Total payable in BRL by currency:",
        *[f"  {c}: BRL {t:,.2f} ({n} invoices)" for c, (n, t) in _by_currency(frame).items()],
        "Invoices by approval level:",
        *[f"  {level}: {int((frame['approval_status'] == level).sum())}" for level in levels],
        f"Foreign-currency invoices whose level changes because of the rate: {len(changed)} of {len(foreign)} "
        "(level if the amount were read as BRL -> level by the BRL total).",
        *[f"  {r.invoice_number} ({r.currency} {r.total_foreign:,.2f} -> BRL {r.total_brl:,.2f}): "
          f"{r.status_without_fx} -> {r.approval_status}" for r in changed.itertuples()],
        f"Invoices priced with the rate of an earlier business day (weekend or holiday): {checks['fallback_rows']}.",
        f"Checks: {checks['rows_before']} invoices before and {checks['rows_after']} after the merge; totals by "
        f"currency unchanged; total payable BRL {checks['total_brl']:,.2f}; unmatched invoices {checks['unmatched_rows']}.",
        "",
        "3. Interpretation (not a calculation)",
        f"Finding: {len(changed)} of {len(foreign)} foreign-currency invoices land in a higher approval level than "
        "their face value suggests; routing them by the unconverted amount would send them to the wrong approver.",
        "Limitation: the rate is the closing selling rate of the issue date, a team assumption; the payment date "
        "could use another rate. The invoices are fictional and the sample is small, so the counts illustrate the "
        "method and do not describe real spending.",
    ]
    return "\n".join(lines) + "\n"


def _by_currency(frame):
    result = {}
    for currency, group in frame.groupby("currency"):
        result[currency] = (len(group), sum(group["total_brl"], Decimal("0")))
    return result
