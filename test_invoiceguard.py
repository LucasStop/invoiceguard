"""Runs invoiceguard.py once per test case and prints the results as a markdown table.

Expected values were written by hand from the business rules in
docs/business-model.md (BR-1 to BR-3), never copied from the script's output.
Exit code is 0 when every case passes, 1 otherwise.

Usage: python3 test_invoiceguard.py
"""
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("invoiceguard.py")

# (subtotal, tax rate %, discount, expected total payable, expected status, what the case checks)
CASES = [
    ("500.00", "10", "0", "550.00", "AUTO-APPROVED", "typical invoice, middle of the first range"),
    ("999.99", "0", "0", "999.99", "AUTO-APPROVED", "boundary: 0.01 below the manager limit"),
    ("950.00", "10", "0", "1,045.00", "MANAGER REVIEW", "subtotal is below 1,000.00 but the tax pushes the total above it"),
    ("1000.00", "0", "0", "1,000.00", "MANAGER REVIEW", "boundary: exactly on the manager limit moves up"),
    ("1000.00", "10", "100.00", "1,000.00", "MANAGER REVIEW", "boundary reached through the calculation (tax and discount cancel out)"),
    ("9999.99", "0", "0", "9,999.99", "MANAGER REVIEW", "boundary: 0.01 below the director limit"),
    ("10000.00", "0", "0", "10,000.00", "DIRECTOR APPROVAL", "boundary: exactly on the director limit moves up"),
    ("9000.00", "12", "0", "10,080.00", "DIRECTOR APPROVAL", "tax pushes the total across the director limit"),
    ("500.00", "0", "500.00", "0.00", "REJECTED", "boundary: total of exactly zero"),
    ("300.00", "5", "400.00", "-85.00", "REJECTED", "discount larger than the invoice, negative total"),
    ("909.09", "10", "0", "1,000.00", "MANAGER REVIEW", "tax of 90.909 rounds to 90.91 first, so the total lands exactly on the limit"),
    ("100.70", "10", "110.77", "0.00", "REJECTED", "full credit: discount equals subtotal plus tax (100.70 + 10.07), so the total is exactly zero"),
    ("0.01", "0", "0", "0.01", "AUTO-APPROVED", "boundary: smallest payable total, 0.01 above zero"),
    ("100.00", "0", "100.01", "-0.01", "REJECTED", "boundary: 0.01 below zero, the nearest negative total"),
    ("1000.01", "0", "0", "1,000.01", "MANAGER REVIEW", "boundary: 0.01 above the manager limit"),
    ("10000.01", "0", "0", "10,000.01", "DIRECTOR APPROVAL", "boundary: 0.01 above the director limit"),
    ("100.00", "10", "105.00", "5.00", "AUTO-APPROVED", "discount larger than the subtotal, but the tax keeps the total positive"),
    ("897.00", "12.5", "9.13", "1,000.00", "MANAGER REVIEW", "tax of exactly 112.125 rounds half up to 112.13, so the total lands on the limit (half-even or float would give 999.99)"),
]

rows = []
failures = 0
for n, (subtotal, tax_rate, discount, expected_total, expected_status, purpose) in enumerate(CASES, start=1):
    stdin_text = f"INV-{n:03d}\nTest Supplier\n{subtotal}\n{tax_rate}\n{discount}\n"
    run = subprocess.run([sys.executable, str(SCRIPT)], input=stdin_text,
                         capture_output=True, text=True, timeout=10)

    printed = {}
    for line in run.stdout.splitlines():
        if ":" in line:
            label, value = line.split(":", 1)
            printed[label.strip()] = value.strip()

    if run.returncode != 0 or "Total payable" not in printed or "Approval status" not in printed:
        actual = "script error"
    else:
        actual = f"{printed['Total payable'].removeprefix('BRL ')} / {printed['Approval status']}"

    expected = f"{expected_total} / {expected_status}"
    passed = actual == expected
    failures += not passed
    rows.append((n, f"{subtotal} / {tax_rate} / {discount}", expected, actual,
                 "PASS" if passed else "FAIL", purpose))

print("| # | Input: subtotal / tax rate % / discount | Expected: total / status | Actual: total / status | Passed? | What the case checks |")
print("|---|---|---|---|---|---|")
for row in rows:
    print("| " + " | ".join(str(cell) for cell in row) + " |")
print()
print(f"{len(CASES) - failures} of {len(CASES)} cases passed.")

# Input validation: lines typed in order, rejected answers expected, final total expected.
# A rejected answer makes the script print "Invalid value..." or "This field cannot be empty." and ask again.
INPUT_CASES = [
    (["INV-1", "S", "1.500", "1250,50", "12,5", "100"], 1, "1,306.81",
     "three decimals rejected; decimal comma accepted for money and rate"),
    (["INV-1", "S", "100", "101", "100", "0"], 1, "200.00",
     "tax rate above 100 rejected, 100 accepted"),
    (["  ", "INV-1", "S", "abc", "-5", "nan", "-0", "1_000", "1e3", "10", "0", "0"], 7, "10.00",
     "empty text, letters, negative, nan, -0, underscore and exponent rejected"),
]
input_failures = 0
print()
print("| # | Lines typed | Expected: rejected / total | Actual: rejected / total | Passed? | What the case checks |")
print("|---|---|---|---|---|---|")
for n, (lines, rejected, total, purpose) in enumerate(INPUT_CASES, start=1):
    run = subprocess.run([sys.executable, str(SCRIPT)], input="\n".join(lines) + "\n",
                         capture_output=True, text=True, timeout=10)
    out = run.stdout
    actual_rejected = out.count("Invalid value") + out.count("cannot be empty")
    actual_total = next((l.split(":", 1)[1].strip().removeprefix("BRL ")
                         for l in out.splitlines() if l.startswith("Total payable")), "script error")
    ok = run.returncode == 0 and (actual_rejected, actual_total) == (rejected, total)
    input_failures += not ok
    print(f"| V{n} | {' / '.join(repr(l) for l in lines)} | {rejected} / {total} | "
          f"{actual_rejected} / {actual_total} | {'PASS' if ok else 'FAIL'} | {purpose} |")
print()
print(f"{len(INPUT_CASES) - input_failures} of {len(INPUT_CASES)} input cases passed.")
sys.exit(1 if failures or input_failures else 0)
