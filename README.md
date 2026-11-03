# Slow trend following (v1)

Long/cash time-series momentum on eight liquid ETFs. This is a $10k, no-leverage, IBKR-or-Robinhood version of the Moskowitz–Ooi–Pedersen / Hurst–Ooi–Pedersen managed-futures idea.

It is **not** stock picking and **not** a 50-market futures CTA. It is a research harness: one slow rule, honest benchmarks, costs.

Start here, then read [`RESULTS.md`](RESULTS.md) for what the backtest actually showed.

## What it does

Each week, for each ETF:

1. If 12-month return beat T-bills, go **long**. Otherwise hold **cash**.
2. Size by inverse volatility, with 25% of risk in each of equities, bonds, commodities, FX.
3. Never use leverage. Leftover capital stays in T-bills.
4. Trade the **next** session after the signal bar (no same-bar peeking).
5. Skip tiny reshuffles (10% L1 inertia).

Then compare against three benchmarks that a “just take less equity risk” overlay should not get credit for beating:

- **Vol-matched SPY** — SPY mixed with cash to the same volatility
- **Always-long universe** — same 8 ETFs, same sizing, never goes to cash
- **60/40** — 60% SPY / 40% IEF

## Universe

| Sleeve | Research ticker | Live ticker | Class |
| --- | --- | --- | --- |
| US large cap | SPY | VTI | equity |
| Developed ex-US | EFA | IEFA | equity |
| Emerging | EEM | IEMG | equity |
| Intermediate Treasuries | IEF | IEF | bonds |
| Long Treasuries | TLT | TLT | bonds |
| Gold | GLD | GLD | commodities |
| Broad commodities | DBC | PDBC | commodities |
| US dollar | UUP | UUP | fx |
| Cash (not a signal) | BIL | SGOV | cash |

Edit [`config/universe.yaml`](config/universe.yaml) if the list changes. That file is the source of truth.

## Repo layout

```
config/           universe, signal, broker costs
src/trend/        engine (data, signal, sizing, backtest, report)
tests/            unit tests, no Yahoo required
scripts/          research side-quests (v2 long/short estimate)
reports/          last v1 run: metrics, equity curves, plots
```

| File | Role |
| --- | --- |
| `src/trend/config.py` | Loads the YAML |
| `src/trend/data.py` | Yahoo download, cache, optional index splice |
| `src/trend/signals.py` | 12-month sign (also SMA / MA cross switches) |
| `src/trend/sizing.py` | Inverse-vol + class budgets + inertia |
| `src/trend/backtest.py` | Daily loop, next-close fills |
| `src/trend/evaluate.py` | Strategy vs the three benchmarks |
| `src/trend/costs.py` | Spreads, slippage, IBKR $1 minimum |

`data_mode: research` (default) uses ETF prices only, from the first date all eight exist (~2007). `research_splice` extends with index/fund proxies — research only, not what you would trade.

## Run

Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

python -m trend download
python -m trend run --broker robinhood ibkr_pro
pytest
```

Writes `reports/summary.md`, `reports/metrics.csv`, and plots. Re-download when you want new prices; the parquet cache is gitignored.

```bash
python -m trend run --mode research_splice   # longer history, not live-tradable
python scripts/v2_estimate.py                # long/short estimate, not the v1 engine
```

## Not the goal of this repo

Doubling $10k in a year. This book runs about 3% volatility. See RESULTS.md.
