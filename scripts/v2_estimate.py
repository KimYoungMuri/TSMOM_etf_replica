"""Long/short ETF trend estimate. Not the v1 live engine.

Run from repo root after `python -m trend download`:

    python scripts/v2_estimate.py

Findings are summarized in RESULTS.md. This is a research side-quest:
same 8 ETFs, sign(12m excess) in {-1,+1}, inverse-vol, weekly next-close.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from trend.config import load_costs, load_strategy, load_universe
from trend.data import build_price_panel, load_cached_prices
from trend.signals import ewma_vol, weekly_rebalance_dates


def metrics(equity: pd.Series, cash_r: pd.Series, spy_r: pd.Series) -> dict:
    equity = equity.dropna()
    rets = equity.pct_change().iloc[1:]
    cash = cash_r.reindex(rets.index).fillna(0.0)
    spy = spy_r.reindex(rets.index).fillna(0.0)
    excess = rets - cash
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    total = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = (1.0 + total) ** (1.0 / years) - 1.0
    vol = float(rets.std() * np.sqrt(252))
    sharpe = float(excess.mean() / excess.std() * np.sqrt(252)) if excess.std() else 0.0
    dd = float((equity / equity.cummax() - 1.0).min())
    return {
        "cagr": cagr,
        "vol": vol,
        "sharpe": sharpe,
        "max_dd": dd,
        "calmar": cagr / abs(dd) if dd < 0 else 0.0,
        "total": total,
        "end_nav": float(equity.iloc[-1]),
        "spy_corr": float(rets.corr(spy)),
        "years": years,
    }


def signed_forecast(prices: pd.DataFrame, ids: list[str], lookbacks: list[int]) -> pd.DataFrame:
    cash = prices["cash"]
    acc = None
    for h in lookbacks:
        excess = prices[ids].pct_change(h).sub(cash.pct_change(h), axis=0)
        s = np.sign(excess).replace(0.0, np.nan)
        acc = s if acc is None else acc.add(s, fill_value=np.nan)
    return acc / len(lookbacks)


def run_ls(
    prices: pd.DataFrame,
    universe,
    lookbacks: list[int],
    vol_target: float,
    gross_cap: float,
    borrow_bps: float = 40.0,
    ibkr_min: float = 0.0,
    inertia_l1: float = 0.10,
    capital: float = 10_000,
) -> tuple[pd.Series, pd.DataFrame, pd.Series]:
    ids = universe.risk_ids()
    budgets = universe.member_risk_budgets()
    rets = prices.pct_change()
    vol = ewma_vol(rets[ids], 60)
    f = signed_forecast(prices, ids, lookbacks)
    spreads = universe.half_spreads_bps()
    one_way = {i: spreads[i] + 2.0 for i in ids}

    rebalance = set(weekly_rebalance_dates(prices.index))
    dates = list(prices.index)
    warmup = max(lookbacks) + 61

    nav = capital
    current = pd.Series(0.0, index=ids)
    pending = None
    equity = pd.Series(index=prices.index, dtype=float)
    weights = pd.DataFrame(0.0, index=prices.index, columns=ids)
    gross_s = pd.Series(index=prices.index, dtype=float)

    for i, dt in enumerate(dates):
        if i == 0:
            equity.iloc[i] = nav
            continue
        r = rets.loc[dt, ids].fillna(0.0)
        r_cash = float(rets.loc[dt, "cash"]) if pd.notna(rets.loc[dt, "cash"]) else 0.0
        # Fully funded L/S: excess on positions + T-bill on capital, minus borrow on shorts.
        excess = (current * (r - r_cash)).sum()
        borrow = float(current.clip(upper=0).abs().sum()) * (borrow_bps / 10_000) / 252
        nav *= 1.0 + r_cash + float(excess) - borrow

        if pending is not None:
            delta = pending - current
            traded = (delta.abs() * nav)
            cost = 0.0
            for asset_id, notional in traded.items():
                cost += float(notional) * one_way[asset_id] / 10_000
            # IBKR Pro $1 min approximation: $1 per name that actually trades
            n_orders = int((delta.abs() > 1e-6).sum())
            cost += n_orders * ibkr_min
            nav -= cost
            current = pending
            pending = None

        equity.iloc[i] = nav
        weights.loc[dt] = current
        gross_s.iloc[i] = float(current.abs().sum())

        if i < warmup or dt not in rebalance or i + 1 >= len(dates):
            continue
        if vol.loc[dt, ids].isna().any() or f.loc[dt, ids].isna().any():
            continue
        raw = pd.Series(0.0, index=ids)
        for asset_id in ids:
            sigma = float(vol.loc[dt, asset_id])
            fc = float(f.loc[dt, asset_id])
            if sigma <= 0 or pd.isna(sigma) or pd.isna(fc):
                continue
            raw[asset_id] = budgets[asset_id] * fc * vol_target / sigma
        g = float(raw.abs().sum())
        if g > gross_cap and g > 0:
            raw *= gross_cap / g
        if float((raw - current).abs().sum()) < inertia_l1:
            continue
        pending = raw

    return equity.astype(float), weights, gross_s


def yearly(eq: pd.Series) -> pd.Series:
    y = eq.resample("YE").last()
    out = y.pct_change()
    out.iloc[0] = y.iloc[0] / eq.iloc[0] - 1.0
    out.index = out.index.year
    return out


def main() -> None:
    universe = load_universe()
    strategy = load_strategy()
    prices = build_price_panel(universe, strategy, raw=load_cached_prices(), mode="research")
    cash_r = prices["cash"].pct_change()
    spy_r = prices["us_equity"].pct_change()
    start = "2008-06-02"

    specs = [
        ("LS 12m 1.0x vt10", [252], 0.10, 1.0),
        ("LS 12m 1.5x vt10", [252], 0.10, 1.5),
        ("LS 12m 2.0x vt22", [252], 0.22, 2.0),
        ("LS 1/3/12 1.5x vt10", [21, 63, 252], 0.10, 1.5),
        ("LS 1/3/12 2.0x vt22", [21, 63, 252], 0.22, 2.0),
    ]

    rows = []
    for ibkr_min, cost_name in [(0.0, "RH/IBKR Lite"), (1.0, "IBKR Pro")]:
        print(f"\n======== {cost_name} + 40bp short borrow ========")
        for name, lbs, vt, cap in specs:
            eq, w, g = run_ls(prices, universe, lbs, vt, cap, ibkr_min=ibkr_min)
            eq = eq.loc[start:]
            eq = eq / eq.iloc[0] * 10_000
            m = metrics(eq, cash_r, spy_r)
            m["avg_gross"] = float(g.loc[start:].mean())
            rows.append(m)
            print(
                f"{name:22s}  CAGR {m['cagr']*100:5.1f}%  vol {m['vol']*100:4.1f}%  "
                f"Sh {m['sharpe']:.2f}  DD {m['max_dd']*100:5.1f}%  "
                f"NAV ${m['end_nav']:6.0f}  gross {m['avg_gross']:.2f}"
            )
            if ibkr_min == 0.0 and name in ("LS 12m 1.5x vt10", "LS 12m 2.0x vt22", "LS 1/3/12 1.5x vt10"):
                y = yearly(eq)
                bits = [f"{yr} {y.loc[yr]*100:+.1f}%" for yr in [2008, 2009, 2022, 2023, 2024] if yr in y.index]
                print("   " + "  ".join(bits))

    base = rows[0]
    scale = 0.08 / base["vol"] if base["vol"] else 1.0
    cash = 0.02
    print(f"\n12m LS 1x scaled to 8% vol (full-sample lever {scale:.2f}x, RH costs):")
    print(
        f"  implied CAGR {(base['cagr']-cash)*scale + cash:.1%}  "
        f"implied maxDD {base['max_dd']*scale:.1%}"
    )


if __name__ == "__main__":
    main()
