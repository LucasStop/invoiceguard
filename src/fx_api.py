# Acquisition and validation of exchange rates from the PTAX of the Banco Central do Brasil.
# Provider: Banco Central do Brasil, open data service Olinda (no key). Details: docs/source-record.md
# Modes: "live" calls the API and saves the raw response; "saved" reuses the last saved response.
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd

ENDPOINT = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
            "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)")
FIELDS = "cotacaoCompra,cotacaoVenda,dataHoraCotacao,tipoBoletim"
TIMEOUT_SECONDS = 15
LOOKBACK_DAYS = 7          # window before the first invoice date, to find the last business day
RATE_BULLETIN = "Fechamento"  # team assumption: closing selling rate (the company buys currency to pay)
UNITS = "BRL per 1 unit of the foreign currency"


class FxError(Exception):
    """Exchange rates could not be acquired or are not usable."""


def fetch_period(currency, start, end, timeout=TIMEOUT_SECONDS, urlopen=urllib.request.urlopen):
    """GET the PTAX bulletins of one currency between two dates. Returns (raw response text, metadata)."""
    params = {"@moeda": f"'{currency}'", "@dataInicial": f"'{start:%m-%d-%Y}'",
              "@dataFinalCotacao": f"'{end:%m-%d-%Y}'", "$format": "json", "$select": FIELDS}
    try:
        with urlopen(f"{ENDPOINT}?{urllib.parse.urlencode(params)}", timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        raise FxError(f"PTAX {currency}: the API answered HTTP {error.code} {error.reason}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise FxError(f"PTAX {currency}: request failed or timed out after {timeout}s ({error})") from error
    except UnicodeDecodeError as error:
        raise FxError(f"PTAX {currency}: the response is not UTF-8 text") from error
    meta = {"provider": "Banco Central do Brasil (PTAX, Olinda)", "endpoint": ENDPOINT, "currency": currency,
            "parameters": {k: v for k, v in params.items()}, "start": start.isoformat(), "end": end.isoformat(),
            "acquired_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "units": UNITS, "rate_used": f"cotacaoVenda of the {RATE_BULLETIN} bulletin"}
    return body, meta


def rates_frame(body, meta):
    """Validate the JSON response and return a DataFrame of closing rates, one row per (currency, rate_date).

    Checks: structure (dict with a list "value"), required fields, cotacaoVenda numeric and above zero,
    parseable dates inside the requested window, and uniqueness of the key. Any failure raises FxError.
    """
    currency = meta["currency"]
    start, end = date.fromisoformat(meta["start"]), date.fromisoformat(meta["end"])
    try:
        payload = json.loads(body, parse_float=Decimal)
    except ValueError as error:
        raise FxError(f"PTAX {currency}: the response is not valid JSON") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("value"), list):
        raise FxError(f"PTAX {currency}: unexpected JSON structure, expected an object with a list 'value'")

    rows = []
    for position, record in enumerate(payload["value"]):
        where = f"PTAX {currency} record {position}"
        if not isinstance(record, dict) or not {"cotacaoVenda", "dataHoraCotacao", "tipoBoletim"} <= record.keys():
            raise FxError(f"{where}: missing cotacaoVenda, dataHoraCotacao or tipoBoletim")
        rate = record["cotacaoVenda"]
        if isinstance(rate, bool) or not isinstance(rate, (Decimal, int)) or rate <= 0:
            raise FxError(f"{where}: cotacaoVenda {rate!r} must be a number above zero")
        try:
            moment = datetime.fromisoformat(str(record["dataHoraCotacao"]))
        except ValueError as error:
            raise FxError(f"{where}: dataHoraCotacao {record['dataHoraCotacao']!r} is not a date") from error
        if not start <= moment.date() <= end:
            raise FxError(f"{where}: date {moment.date()} is outside the requested window {start} to {end}")
        if record["tipoBoletim"] == RATE_BULLETIN:
            rows.append({"currency": currency, "rate_date": moment.date(), "rate": Decimal(rate)})

    frame = pd.DataFrame(rows, columns=["currency", "rate_date", "rate"])
    if frame.duplicated(["currency", "rate_date"]).any():
        raise FxError(f"PTAX {currency}: more than one {RATE_BULLETIN} rate for the same date")
    return frame


def save_raw(body, meta, raw_dir):
    """Keep the response exactly as received plus its metadata. Written to a temp file, then replaced."""
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    stem = f"ptax_{meta['currency']}"
    for name, text in ((f"{stem}.json", body), (f"{stem}.meta.json", json.dumps(meta, indent=2))):
        temp = raw_dir / f"{name}.tmp"
        temp.write_text(text, encoding="utf-8")
        os.replace(temp, raw_dir / name)


def load_raw(currency, raw_dir):
    """Return (raw response text, metadata) saved by an earlier live run, or raise FxError."""
    stem = Path(raw_dir) / f"ptax_{currency}"
    try:
        body = stem.with_suffix(".json").read_text(encoding="utf-8")
        meta = json.loads(stem.with_suffix(".meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FxError(f"PTAX {currency}: no usable saved response in {raw_dir}; run once with --mode live") from error
    return body, meta


def acquire_rates(invoices, mode, raw_dir, urlopen=urllib.request.urlopen):
    """Return (rates DataFrame, list of metadata) for every foreign currency in the batch.

    live: one request per currency covering LOOKBACK_DAYS before its first invoice up to its last;
    the response is validated first and only then saved. saved: reads the last saved response.
    """
    if mode not in ("live", "saved"):
        raise FxError(f"unknown mode '{mode}', use live or saved")
    frames, metas = [], []
    for currency in sorted({i["currency"] for i in invoices} - {"BRL"}):
        dates = [i["issue_date"] for i in invoices if i["currency"] == currency]
        if mode == "live":
            body, meta = fetch_period(currency, min(dates) - timedelta(days=LOOKBACK_DAYS), max(dates), urlopen=urlopen)
            frame = rates_frame(body, meta)
            save_raw(body, meta, raw_dir)
        else:
            body, meta = load_raw(currency, raw_dir)
            frame = rates_frame(body, meta)
        meta = dict(meta, mode=mode)
        frames.append(frame)
        metas.append(meta)
    rates = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["currency", "rate_date", "rate"])
    return rates, metas
