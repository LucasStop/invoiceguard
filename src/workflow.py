# Workflow: acquisition -> validation -> integration -> storage, with a log and an atomic package.
# A run is built in output/incomplete/<run_id>/ and moved to output/runs/<run_id>/ only when every
# step passed, so a half-written run never looks completed and earlier runs are never touched.
# output/latest.txt says which run was last, its status and which run was the last success.
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from src import outputs
from src.fx_api import FxError, acquire_rates
from src.integrate import IntegrationError, integrate
from src.loader import BatchError, load_batch

HANDLED = (BatchError, FxError, IntegrationError, ValueError, OSError)


def run(input_dir, raw_dir, output_dir, mode, urlopen=urllib.request.urlopen, run_id=None, now=None):
    """Run the whole workflow. Returns (ok, run_id, message). Never raises for a handled failure."""
    now = now or (lambda: datetime.now(timezone.utc))
    output_dir = Path(output_dir)
    run_id = run_id or _new_run_id(output_dir, now())
    staging = output_dir / "incomplete" / run_id
    log = []

    def say(message):
        log.append(f"{now().isoformat(timespec='seconds')} {message}")

    try:
        staging.mkdir(parents=True)
        say(f"run {run_id} started, rate source mode: {mode}")
        invoices = load_batch(input_dir, today=now().date())
        files = sorted({i["source_file"] for i in invoices})
        say(f"validated {len(invoices)} invoices from {', '.join(files)}")

        rates, metas = acquire_rates(invoices, mode, raw_dir, urlopen=urlopen)
        say("rates ready: " + (", ".join(f"{m['currency']} ({m['mode']}, acquired {m['acquired_at']})" for m in metas)
                               or "none needed, all invoices in BRL"))

        frame, checks = integrate(invoices, rates)
        frame["rate_mode"] = mode
        say(f"integrated {checks['rows_after']} of {checks['rows_before']} invoices, "
            f"{checks['fallback_rows']} with an earlier-day rate, total BRL {checks['total_brl']}")

        outputs.write_csv(frame, outputs.PROCESSED_COLUMNS, staging / "invoices_processed.csv")
        outputs.write_csv(frame, list(frame.columns), staging / "invoices_integrated.csv")
        outputs.write_workbook(frame, staging / "invoices.xlsx")
        verified = outputs.verify_workbook(staging / "invoices.xlsx", staging / "invoices_integrated.csv", frame)
        say(f"workbook verified against the CSV: {verified['detail_rows']} rows, total BRL {verified['total_brl']}")
        (staging / "report.txt").write_text(
            outputs.build_report(frame, checks, metas, {"run_id": run_id, "mode": mode}), encoding="utf-8")

        say("all steps passed, publishing the run")
        (staging / "run.log").write_text("\n".join(log) + "\n", encoding="utf-8")
        final = output_dir / "runs" / run_id
        final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, final)
    except HANDLED as error:
        message = str(error)
        one_line = " | ".join(message.splitlines())
        say(f"run FAILED: {one_line}")
        try:
            (staging / "run.log").write_text("\n".join(log) + "\n" + message + "\n", encoding="utf-8")
        except OSError:
            pass
        _write_latest(output_dir, run_id, "FAILED", mode, f"output/incomplete/{run_id}", one_line, now())
        return False, run_id, message
    _write_latest(output_dir, run_id, "SUCCESS", mode, f"output/runs/{run_id}", "ok", now())
    return True, run_id, f"output/runs/{run_id}"


def _new_run_id(output_dir, moment):
    base, n = moment.strftime("%Y%m%d-%H%M%S"), 1
    run_id = base
    while any((output_dir / folder / run_id).exists() for folder in ("runs", "incomplete")):
        n += 1
        run_id = f"{base}-{n}"
    return run_id


def _write_latest(output_dir, run_id, status, mode, location, message, moment):
    """latest.txt: the last run and its status, plus the last successful run. Replaced atomically."""
    previous = read_latest(output_dir)
    last_success = run_id if status == "SUCCESS" else previous.get("last_success", "none")
    text = "\n".join([f"run_id={run_id}", f"status={status}", f"mode={mode}", f"location={location}",
                      f"finished_at={moment.isoformat(timespec='seconds')}", f"last_success={last_success}",
                      f"message={message}"]) + "\n"
    output_dir.mkdir(parents=True, exist_ok=True)
    temp = output_dir / "latest.txt.tmp"
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, output_dir / "latest.txt")


def read_latest(output_dir):
    try:
        lines = (Path(output_dir) / "latest.txt").read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    return dict(line.split("=", 1) for line in lines if "=" in line)
