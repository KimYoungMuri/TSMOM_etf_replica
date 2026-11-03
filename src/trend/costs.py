from __future__ import annotations

import numpy as np
import pandas as pd

from trend.config import BrokerCosts, Universe


def trade_cost_dollars(
    traded_notional: pd.Series,
    prices: pd.Series,
    universe: Universe,
    broker: BrokerCosts,
    slippage_bps: float,
) -> float:
    """Cost of a simultaneous set of orders, one per asset id in traded_notional."""
    total = 0.0
    for asset_id, notional in traded_notional.items():
        if asset_id == "cash" or abs(notional) < 1e-8:
            continue
        inst = universe.by_id(asset_id)
        spread_bps = inst.half_spread_bps + slippage_bps
        spread_cost = abs(notional) * spread_bps / 10_000.0
        price = float(prices[asset_id])
        shares = abs(notional) / price if price > 0 else 0.0
        commission = 0.0
        if shares > 0 and (broker.commission_per_share > 0 or broker.commission_min > 0):
            commission = max(broker.commission_min, broker.commission_per_share * shares)
        total += spread_cost + commission
    return float(total)


def apply_costs_to_turnover(
    turnover_notional: pd.DataFrame,
    prices: pd.DataFrame,
    nav: pd.Series,
    universe: Universe,
    broker: BrokerCosts,
    slippage_bps: float,
) -> pd.Series:
    """Daily cost in dollars from a notional-turnover panel (same index as nav)."""
    costs = pd.Series(0.0, index=nav.index)
    for dt in turnover_notional.index:
        row = turnover_notional.loc[dt]
        if np.allclose(row.abs().sum(), 0.0):
            continue
        costs.loc[dt] = trade_cost_dollars(row, prices.loc[dt], universe, broker, slippage_bps)
    return costs
