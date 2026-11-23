"""One command for the whole workflow: validate the CSVs, get the exchange rates, integrate, write the outputs.

Usage:
    python3 run.py --mode live     calls the PTAX API and saves the response in data/raw
    python3 run.py --mode saved    reuses the last saved response (offline, repeatable)
    python3 run.py --input tests/fixtures/invalid_value --mode saved    controlled failure for the demo

Status of the last run: cat output/latest.txt
"""
import argparse
import sys
from pathlib import Path

from src.workflow import read_latest, run

ROOT = Path(__file__).resolve().parent


def main(argv=None):
    parser = argparse.ArgumentParser(description="InvoiceGuard batch: invoices in BRL, USD and EUR to approval levels.")
    parser.add_argument("--mode", choices=["live", "saved"], default="live", help="rate source (default: live)")
    parser.add_argument("--input", default=str(ROOT / "data" / "input"), help="folder with the invoice CSVs")
    args = parser.parse_args(argv)

    output_dir = ROOT / "output"
    ok, run_id, message = run(args.input, ROOT / "data" / "raw", output_dir, args.mode)
    print(f"Run {run_id}: {'SUCCESS' if ok else 'FAILED'}")
    print(message)
    print("\noutput/latest.txt:")
    print("\n".join(f"  {k}={v}" for k, v in read_latest(output_dir).items()))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
