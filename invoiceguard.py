# InvoiceGuard: calculates the total payable of a supplier invoice and decides
# which approval level it needs. Business model and rules: docs/business-model.md
import re
from decimal import Decimal, ROUND_HALF_UP

# Approval limits in BRL (business rule BR-3). Policy values assumed by the team.
APPROVAL_LIMIT_AUTO = Decimal("1000.00")      # below this: the analyst approves alone
APPROVAL_LIMIT_MANAGER = Decimal("10000.00")  # below this: manager review; at or above: director
CENT = Decimal("0.01")
MAX_TAX_RATE = Decimal("100")


def read_text(prompt):
    """Ask until the answer is not empty."""
    while True:
        text = input(prompt).strip()
        if text:
            return text
        print("This field cannot be empty.")


def read_number(prompt, maximum=None):
    """Ask until the answer is a number with at most 2 decimals (point or comma), not above maximum."""
    while True:
        text = input(prompt).strip()
        # [0-9], not \d: \d also accepts digits of other alphabets
        if re.fullmatch(r"[0-9]+([.,][0-9]{1,2})?", text):
            value = Decimal(text.replace(",", "."))
            if maximum is None or value <= maximum:
                return value
        limit = "" if maximum is None else f", at most {maximum}"
        print(f"Invalid value: type a number that is not negative, with at most 2 decimals (e.g. 1250.50){limit}.")


# Input
invoice_number = read_text("Enter invoice number: ")
supplier_name = read_text("Enter supplier name: ")
subtotal = read_number("Enter subtotal (BRL): ")
tax_rate = read_number("Enter tax rate (%, e.g. 12.5 for 12.5%): ", maximum=MAX_TAX_RATE)
discount = read_number("Enter discount (BRL): ")

# Processing: BR-1 (tax on the subtotal, before the discount) and BR-2 (total).
# The tax is rounded to cents, half a cent going up. Every term is then a whole
# number of cents, so the total is exact and the limit comparisons below are exact.
tax_value = (subtotal * tax_rate / 100).quantize(CENT, rounding=ROUND_HALF_UP)
total_payable = subtotal + tax_value - discount

# BR-3: approval routing, decided by the total payable.
# "<= 0" comes first: a zero or negative total must never reach AUTO-APPROVED.
# A total exactly equal to a limit moves up to the next level.
# The chain only works while APPROVAL_LIMIT_AUTO < APPROVAL_LIMIT_MANAGER.
if total_payable <= 0:
    approval_status = "REJECTED"
elif total_payable < APPROVAL_LIMIT_AUTO:
    approval_status = "AUTO-APPROVED"
elif total_payable < APPROVAL_LIMIT_MANAGER:
    approval_status = "MANAGER REVIEW"
else:
    approval_status = "DIRECTOR APPROVAL"

# Output
print()
print("--- InvoiceGuard result ---")
print(f"Invoice number  : {invoice_number}")
print(f"Supplier        : {supplier_name}")
print(f"Subtotal        : BRL {subtotal:,.2f}")
print(f"Tax rate        : {tax_rate:.2f}%")
print(f"Tax value       : BRL {tax_value:,.2f}")
print(f"Discount        : BRL {discount:,.2f}")
print(f"Total payable   : BRL {total_payable:,.2f}")
print(f"Approval status : {approval_status}")
