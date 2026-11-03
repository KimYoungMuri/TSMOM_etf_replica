# Slow trend-following baseline

Universe (research/live): us_equity=SPY/VTI, developed_ex_us=EFA/IEFA, emerging=EEM/IEMG, intermediate_treasury=IEF/IEF, long_treasury=TLT/TLT, gold=GLD/GLD, broad_commodities=DBC/PDBC, usd=UUP/UUP
Cash: BIL/SGOV
Price window: 2007-05-30 to 2026-11-03
Capital: $10,000

Signal is 12-month excess return sign, long/cash, inverse-vol with equal class risk budgets, weekly next-close execution, 10% L1 inertia, 100% gross cap.

A system that merely takes less equity exposure should not beat vol-matched SPY or the always-long same-universe book. Those two are the honest tests.

## Metrics

| broker | name | cagr | ann_vol | sharpe | max_drawdown | calmar | avg_gross | avg_turnover | cost_drag_bps | spy_corr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| robinhood | trend_long_cash | 2.8% | 3.2% | 0.49 | -4.7% | 0.61 | 52.3% | 3.07 | 18 | 0.10 |
| robinhood | same_universe_always_long | 3.8% | 3.6% | 0.69 | -6.9% | 0.55 | 86.7% | 0.34 | 2 | 0.47 |
| robinhood | sixty_forty | 8.7% | 11.4% | 0.68 | -28.6% | 0.30 | 99.9% | 0.05 | 0 | 0.97 |
| robinhood | vol_matched_spy | 3.2% | 3.2% | 0.60 | -8.8% | 0.37 | 16.4% | 0.01 | 0 | 0.99 |
| ibkr_pro | trend_long_cash | 2.6% | 3.2% | 0.42 | -4.9% | 0.53 | 52.3% | 3.07 | 47 | 0.10 |
| ibkr_pro | same_universe_always_long | 3.7% | 3.6% | 0.66 | -6.9% | 0.53 | 86.7% | 0.34 | 17 | 0.47 |
| ibkr_pro | sixty_forty | 8.7% | 11.4% | 0.68 | -28.6% | 0.30 | 99.9% | 0.05 | 0 | 0.97 |
| ibkr_pro | vol_matched_spy | 3.2% | 3.2% | 0.60 | -8.8% | 0.37 | 16.4% | 0.01 | 0 | 0.99 |

## How to read this

- `trend_long_cash` is the strategy.
- `vol_matched_spy` is SPY mixed with cash to the same full-sample realized vol. If trend only wins vs raw SPY, this absorbs the 'less equity' effect.
- `same_universe_always_long` is the 8 ETFs with the same inverse-vol class budgets, never going to cash. If trend only wins vs this, the edge is the on/off switch.
- `sixty_forty` is 60% SPY / 40% IEF, weekly rebalanced.
- `cost_drag_bps` is annualized implementation cost in basis points of starting capital.
- IBKR Pro's $1 minimum per order is why inertia exists; Robinhood and IBKR Lite are commission-free.
