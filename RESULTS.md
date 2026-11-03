# What we found

Sample: **2008-06-02 → 2026-11-03**, $10k start, Yahoo adjusted closes, next-close weekly fills. First year of prices is warmup for the 12-month signal.

## v1 — long/cash (this repo)

Robinhood / IBKR Lite costs:

| Book | CAGR | Vol | Sharpe | Max DD | Ending NAV |
| --- | --- | --- | --- | --- | --- |
| Trend long/cash | 2.8% | 3.2% | 0.49 | −4.7% | $17.3k |
| Always-long same universe | 3.8% | 3.6% | **0.69** | −6.9% | $20.4k |
| Vol-matched SPY (16% SPY + cash) | 3.2% | 3.2% | 0.60 | −8.8% | $18.5k |
| 60/40 SPY/IEF | 8.7% | 11.4% | 0.68 | −28.6% | $48.1k |

IBKR Pro ($1/order) drops trend Sharpe from 0.49 → 0.42 (about 47 bps/year of cost vs 18).

**Read this as:** the on/off switch did not earn alpha. Always-long and vol-matched SPY both beat it. Smaller drawdowns are real; they are mostly less equity exposure. Average allocation was ~48% cash, ~18% UUP, ~11% IEF. Correlation to SPY: 0.10.

The filter helped in the crises (2008 +1.3% vs 60/40 −15%; 2022 +3.5% vs 60/40 −16%) and lagged recoveries (2009 in cash while stocks rallied). That is what a slow long/cash rule does.

Plots and the full table: [`reports/summary.md`](reports/summary.md).

## v2 — long/short estimate (not in the live engine)

Same 8 ETFs, `f = ±1`, 40 bp short borrow, weekly, inertia. Script: `scripts/v2_estimate.py`.

On commission-free (Robinhood / IBKR Lite), 12-month L/S was about **1.8% CAGR, 5% vol, Sharpe 0.14**, max DD −9 to −10%. Crisis years improved (2008 +6%, 2022 +8%); 2009 and bull years gave it back. Levering to ~10% vol did not raise CAGR and took max DD to about **−21%**.

IBKR Pro’s $1 minimum made L/S unusable at $10k (Sharpe negative). If this is ever live, use Robinhood or IBKR Lite.

v2 is closer to the papers and still **not** a path from $10k to $20k in a year. A 100% year is the wrong job for a 3–10% vol trend book.

## Why this is slower than the papers

Moskowitz / Hurst / CFM results are **long and short** on **50–70 futures**, with **vol targeting / leverage**, institutional costs. This repo is eight ETF proxies, long/cash, 100% cap. Realized vol landed near 3% because we do not lever the book up to a 10% portfolio target.

## Practical takeaway

- Learning the pipeline (data, sizing, next-bar execution, honest eval): this is the right first system.
- Compounding $10k quickly: this is the wrong system.
- Next research that could matter: saturating forecast, then long/short on IBKR Lite, then a tiny micro-futures sleeve. Each still has to beat always-long and vol-matched SPY after costs.
