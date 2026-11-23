# Reads a batch of invoice CSVs from one folder and validates it before anything is published.
# Rules (each one protects a later step):
#   1. all required columns present, no extra cells: a shifted row would silently corrupt amounts
#   2. invoice_number filled and unique in the whole batch: a duplicate would be paid twice
#   3. currency in BRL, USD or EUR: only these have a rate rule in the integration
#   4. issue_date is YYYY-MM-DD and not in the future: the exchange rate is looked up by this date
#   5. subtotal, tax_rate, discount match the LO1 number format; tax rate at most 100
# One bad row or file rejects the whole batch (BatchError lists every problem found).
import csv
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

COLUMNS = ["invoice_number", "supplier", "issue_date", "currency", "subtotal", "tax_rate", "discount"]
CURRENCIES = {"BRL", "USD", "EUR"}
MAX_TAX_RATE = Decimal("100")
# [0-9], not \d: \d also accepts digits of other alphabets
NUMBER = re.compile(r"[0-9]+([.,][0-9]{1,2})?")
ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class BatchError(Exception):
    """The batch was rejected; the message lists every problem with file and line."""


def load_batch(input_dir, today=None):
    """Return the validated invoices of every CSV in input_dir (at least 2), or raise BatchError."""
    today = today or date.today()
    folder = Path(input_dir)
    files = sorted(folder.glob("*.csv")) if folder.is_dir() else []
    if len(files) < 2:
        raise BatchError(f"{folder}: the batch needs at least 2 CSV files, found {len(files)}")

    errors, invoices, first_seen = [], [], {}
    for path in files:
        try:
            handle = open(path, newline="", encoding="utf-8")
        except OSError as error:
            errors.append(f"{path.name}: cannot read the file ({error.strerror})")
            continue
        with handle:
            reader = csv.DictReader(handle)
            missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                errors.append(f"{path.name}: missing column(s) {', '.join(missing)}")
                continue
            for line, raw in enumerate(reader, start=2):
                where = f"{path.name}:{line}"
                invoice = _validate_row(raw, where, today, first_seen, errors)
                if invoice:
                    invoices.append(dict(invoice, source_file=path.name, source_line=line))
    if not invoices and not errors:
        errors.append("the CSV files have no invoice rows")
    if errors:
        raise BatchError("batch rejected:\n- " + "\n- ".join(errors))
    return invoices


def _validate_row(raw, where, today, first_seen, errors):
    """Return the typed invoice, or None after appending the problems to errors."""
    problems = []
    if None in raw or any(raw[c] is None for c in COLUMNS):
        errors.append(f"{where}: wrong number of cells")
        return None
    row = {c: raw[c].strip() for c in COLUMNS}

    if not row["invoice_number"]:
        problems.append("invoice_number is empty")
    elif row["invoice_number"] in first_seen:
        problems.append(f"invoice_number {row['invoice_number']} already used at {first_seen[row['invoice_number']]}")
    else:
        first_seen[row["invoice_number"]] = where
    if not row["supplier"]:
        problems.append("supplier is empty")
    if row["currency"] not in CURRENCIES:
        problems.append(f"currency '{row['currency']}' is not one of {', '.join(sorted(CURRENCIES))}")

    issue_date = None
    if ISO_DATE.fullmatch(row["issue_date"]):
        try:
            issue_date = date.fromisoformat(row["issue_date"])
        except ValueError:
            pass
    if issue_date is None:
        problems.append(f"issue_date '{row['issue_date']}' is not a valid YYYY-MM-DD date")
    elif issue_date > today:
        problems.append(f"issue_date {issue_date} is in the future")

    numbers = {}
    for name in ("subtotal", "tax_rate", "discount"):
        if NUMBER.fullmatch(row[name]):
            numbers[name] = Decimal(row[name].replace(",", "."))
        else:
            problems.append(f"{name} '{row[name]}' must be a non-negative number with at most 2 decimals")
    if "tax_rate" in numbers and numbers["tax_rate"] > MAX_TAX_RATE:
        problems.append(f"tax_rate {numbers['tax_rate']} is above {MAX_TAX_RATE}")

    if problems:
        errors.extend(f"{where}: {p}" for p in problems)
        return None
    return {"invoice_number": row["invoice_number"], "supplier": row["supplier"],
            "issue_date": issue_date, "currency": row["currency"], **numbers}
