# Business rules BR-1 to BR-3 of InvoiceGuard (docs/business-model.md) as pure functions.
# Same arithmetic as the LO1 script invoiceguard.py, which cannot be imported
# because it asks for input at module level.
from decimal import Decimal, ROUND_HALF_UP

# Approval limits in BRL (BR-3). Policy values assumed by the team.
APPROVAL_LIMIT_AUTO = Decimal("1000.00")      # below this: the analyst approves alone
APPROVAL_LIMIT_MANAGER = Decimal("10000.00")  # below this: manager review; at or above: director
CENT = Decimal("0.01")


def calculate_total(subtotal, tax_rate, discount):
    """BR-1 and BR-2: tax on the subtotal rounded half up to cents, then total = subtotal + tax - discount.

    Every term is a whole number of cents, so the total is exact. Returns (tax_value, total).
    """
    tax_value = (subtotal * tax_rate / 100).quantize(CENT, rounding=ROUND_HALF_UP)
    return tax_value, subtotal + tax_value - discount


def convert_to_brl(amount, rate):
    """Total payable in BRL: amount in the invoice currency times the BRL rate, rounded half up to cents."""
    return (amount * rate).quantize(CENT, rounding=ROUND_HALF_UP)


def approval_status(total_brl):
    """BR-3: approval level decided by the total payable in BRL.

    "<= 0" comes first so a zero or negative total never reaches AUTO-APPROVED.
    A total exactly equal to a limit moves up to the next level.
    """
    if total_brl <= 0:
        return "REJECTED"
    if total_brl < APPROVAL_LIMIT_AUTO:
        return "AUTO-APPROVED"
    if total_brl < APPROVAL_LIMIT_MANAGER:
        return "MANAGER REVIEW"
    return "DIRECTOR APPROVAL"
