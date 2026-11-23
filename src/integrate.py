# Integration of the invoice batch with the exchange rates.
#   invoice source: one row = one supplier invoice (key: invoice_number)
#   rate source:    one row = the closing PTAX selling rate of one currency on one business day
# Join key: (currency, rate_date). rate_date is the issue date, or the last business day before it
# when the issue date has no rate (weekend, holiday), looking back at most LOOKBACK_DAYS.
# Many invoices share one rate (many-to-one). BRL invoices need no rate (rate 1).
from datetime import timedelta
from decimal import Decimal

import pandas as pd

from src.fx_api import LOOKBACK_DAYS
from src.rules import approval_status, calculate_total, convert_to_brl


class IntegrationError(Exception):
    """The invoices and the rates cannot be combined safely."""


def integrate(invoices, rates):
    """Return (integrated DataFrame, checks dict). Raises IntegrationError instead of losing or inflating rows."""
    frame = pd.DataFrame(invoices)
    if rates.duplicated(["currency", "rate_date"]).any():
        raise IntegrationError("the rate source has more than one rate for the same (currency, rate_date)")

    calculated = [calculate_total(r["subtotal"], r["tax_rate"], r["discount"]) for r in invoices]
    frame["tax_value"] = [tax for tax, _ in calculated]
    frame["total_foreign"] = [total for _, total in calculated]  # total in the invoice currency (BR-1, BR-2)

    available = {c: sorted(g["rate_date"]) for c, g in rates.groupby("currency")}
    frame["rate_date"] = [_rate_date(row, available) for row in frame.itertuples()]

    merged = frame.merge(rates, on=["currency", "rate_date"], how="left", validate="many_to_one")
    merged.loc[merged["currency"] == "BRL", "rate"] = Decimal("1")
    missing = merged[merged["rate"].isna()]
    if len(missing):
        listed = ", ".join(f"{r.invoice_number} ({r.currency} {r.issue_date})" for r in missing.itertuples())
        raise IntegrationError(f"no exchange rate within {LOOKBACK_DAYS} days before the issue date for: {listed}")

    merged["rate_fallback"] = (merged["currency"] != "BRL") & (merged["rate_date"] != merged["issue_date"])
    merged["total_brl"] = [convert_to_brl(t, r) for t, r in zip(merged["total_foreign"], merged["rate"])]
    merged["approval_status"] = [approval_status(t) for t in merged["total_brl"]]
    # What BR-3 would say if the foreign total were wrongly read as BRL: shows what the rate changes.
    merged["status_without_fx"] = [approval_status(t) for t in merged["total_foreign"]]
    merged["level_changed_by_fx"] = merged["approval_status"] != merged["status_without_fx"]

    checks = _reconcile(frame, merged)
    columns = ["invoice_number", "supplier", "issue_date", "currency", "subtotal", "tax_rate", "discount",
               "tax_value", "total_foreign", "rate_date", "rate_fallback", "rate", "total_brl",
               "approval_status", "status_without_fx", "level_changed_by_fx", "source_file", "source_line"]
    return merged[columns], checks


def _rate_date(row, available):
    if row.currency == "BRL":
        return row.issue_date
    earliest = row.issue_date - timedelta(days=LOOKBACK_DAYS)
    candidates = [d for d in available.get(row.currency, []) if earliest <= d <= row.issue_date]
    return max(candidates) if candidates else None


def _reconcile(before, after):
    """Counts and business totals must be the same before and after the merge."""
    checks = {"rows_before": len(before), "rows_after": len(after),
              "foreign_total_before": _sum_by_currency(before), "foreign_total_after": _sum_by_currency(after),
              "total_brl": sum(after["total_brl"], Decimal("0")),
              "fallback_rows": int(after["rate_fallback"].sum()),
              "unmatched_rows": int(after["rate"].isna().sum())}
    if checks["rows_before"] != checks["rows_after"]:
        raise IntegrationError(f"row count changed in the merge: {checks['rows_before']} -> {checks['rows_after']}")
    if checks["foreign_total_before"] != checks["foreign_total_after"]:
        raise IntegrationError("totals by currency changed in the merge")
    return checks


def _sum_by_currency(frame):
    return {c: sum(g["total_foreign"], Decimal("0")) for c, g in frame.groupby("currency")}
