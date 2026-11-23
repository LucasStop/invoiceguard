# Source record: PTAX exchange rates

Record of the external data source used by InvoiceGuard RA2 (rubric 5.1).

## Why this source

The approval limits (BRL 1,000.00 and BRL 10,000.00) are in reais, but the invoice batch has invoices in USD and EUR. The local data cannot say how much an invoice of USD 1,900.00 is worth in BRL, so it cannot decide the approval level. The PTAX of the Banco Central do Brasil is the official reference rate, is open, needs no key and has a documented API.

## Source

| Item | Value |
|---|---|
| Provider | Banco Central do Brasil, open data service Olinda (PTAX) |
| Documentation | https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/documentacao |
| Endpoint | `https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)` |
| Method | `GET`, timeout 15 s, no authentication |
| Parameters | `@moeda='USD'` or `'EUR'`; `@dataInicial='MM-DD-YYYY'`; `@dataFinalCotacao='MM-DD-YYYY'`; `$format=json`; `$select=cotacaoCompra,cotacaoVenda,dataHoraCotacao,tipoBoletim` |
| Window | one request per currency: from 7 days before its first invoice date to its last invoice date |
| Acquisition date | 2026-11-23 (the exact UTC time of each response is in `data/raw/ptax_<CUR>.meta.json`) |
| Saved response | `data/raw/ptax_USD.json` and `data/raw/ptax_EUR.json`, exactly as received |
| Units | BRL per 1 unit of the foreign currency (`cotacaoVenda`) |
| Use conditions | The dataset page of the portal (dadosabertos.bcb.gov.br) states the license Open Data Commons Open Database License (ODbL): use is allowed with attribution. The reports and the README cite the Banco Central do Brasil as the source. |

## JSON structure

```
{ "@odata.context": "...", "value": [ { "cotacaoCompra": 5.4, "cotacaoVenda": 5.4935,
    "dataHoraCotacao": "2026-11-03 13:06:31.766", "tipoBoletim": "Fechamento" }, ... ] }
```

- The list `value` holds one record per bulletin: five per business day (Abertura, three Intermediario, Fechamento).
- Weekends and holidays have no bulletin: the list is empty for those days (confirmed on 2026-11-02, a holiday, and on 2026-11-21, a Saturday).
- Parameter name: the currency parameter is `moeda`; `codigoMoeda` makes the API answer HTTP 400.

## Fields used

| JSON field | DataFrame column | Meaning |
|---|---|---|
| (request parameter) | `currency` | currency code of the request |
| `dataHoraCotacao` (date part) | `rate_date` | business day of the bulletin |
| `cotacaoVenda` | `rate` | selling rate, kept as exact `Decimal` |
| `tipoBoletim` | (filter) | only `Fechamento` is kept |

Team assumption (not a legal rule): the selling rate of the closing bulletin, because the company buys foreign currency to pay the supplier.

## Checks and reaction to unsuitable data

| Check | Reaction |
|---|---|
| response is not JSON, or is not an object with a list `value` | `FxError`, run rejected |
| a record without `cotacaoVenda`, `dataHoraCotacao` or `tipoBoletim` | `FxError`, run rejected |
| `cotacaoVenda` not a number above zero | `FxError`, run rejected |
| date not parseable or outside the requested window | `FxError`, run rejected |
| two closing rates for the same (currency, date) | `FxError`, run rejected |
| HTTP error or timeout | `FxError` with the status or the timeout, run rejected |
| invoice date without rate (weekend, holiday) | falls back to the last business day within 7 days; `rate_date` and `rate_fallback` show it |
| no rate within 7 days | `IntegrationError` listing the invoices, run rejected |

A live response is validated before it replaces the saved one, so a bad response never overwrites the last good file.
