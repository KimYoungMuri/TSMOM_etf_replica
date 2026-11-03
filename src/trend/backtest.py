from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from trend.config import BrokerCosts, CostConfig, StrategyConfig, Universe
from trend.costs import trade_cost_dollars
from trend.signals import binary_forecast, ewma_vol, weekly_rebalance_dates
from trend.sizing import apply_inertia, target_weights


@dataclass
class BacktestResult:
    name: str
    broker: str
    equity: pd.Series
    returns: pd.Series
    weights: pd.DataFrame
    cash_weight: pd.Series
    turnover: pd.Series
    costs: pd.Series
    signals: pd.DataFrame
    target_weights: pd.DataFrame
    vol: pd.DataFrame


def run_backtest(
    prices: pd.DataFrame,
    universe: Universe,
    strategy: StrategyConfig,
    costs: CostConfig,
    broker: BrokerCosts,
    name: str = "trend",
    always_long: bool = False,
) -> BacktestResult:
    """Daily long/cash backtest with next-close execution and no look-ahead fills.

    On a rebalance date t we form the signal from closes through t and queue
    the order. Fills happen at the next session close (t+1).
    """
    risk_ids = universe.risk_ids()
    rets = prices.pct_change()
    vol = ewma_vol(rets[risk_ids], strategy.vol_center_of_mass_days)
    if always_long:
        signals = pd.DataFrame(1.0, index=prices.index, columns=risk_ids)
        signals = signals.where(prices[risk_ids].notna() & vol.notna())
    else:
        signals = binary_forecast(prices, universe, strategy)

    rebalance_dates = set(weekly_rebalance_dates(prices.index))
    dates = list(prices.index)

    equity = pd.Series(index=prices.index, dtype=float)
    weights_held = pd.DataFrame(0.0, index=prices.index, columns=risk_ids)
    cash_w = pd.Series(index=prices.index, dtype=float)
    turnover = pd.Series(0.0, index=prices.index)
    cost_dollars = pd.Series(0.0, index=prices.index)
    targets = pd.DataFrame(0.0, index=prices.index, columns=risk_ids)

    nav = float(universe.capital)
    current = pd.Series(0.0, index=risk_ids)
    pending: pd.Series | None = None

    warmup = max(strategy.lookback_days, strategy.slow_ma_days, strategy.vol_center_of_mass_days) + 1

    for i, dt in enumerate(dates):
        if i == 0:
            equity.iloc[i] = nav
            cash_w.iloc[i] = 1.0
            continue

        asset_ret = rets.loc[dt, risk_ids].fillna(0.0)
        cash_ret = float(rets.loc[dt, "cash"]) if pd.notna(rets.loc[dt, "cash"]) else 0.0
        port_ret = float((current * asset_ret).sum() + (1.0 - float(current.sum())) * cash_ret)
        nav *= 1.0 + port_ret

        if pending is not None:
            delta = pending - current
            traded_notional = delta * nav
            cost = trade_cost_dollars(
                traded_notional,
                prices.loc[dt, risk_ids],
                universe,
                broker,
                costs.slippage_bps,
            )
            nav -= cost
            cost_dollars.loc[dt] = cost
            turnover.loc[dt] = float(delta.abs().sum())
            current = pending.clip(lower=0)
            if float(current.sum()) > strategy.gross_cap:
                current *= strategy.gross_cap / float(current.sum())
            pending = None

        equity.iloc[i] = nav
        weights_held.loc[dt] = current
        cash_w.iloc[i] = 1.0 - float(current.sum())

        if i < warmup or dt not in rebalance_dates:
            continue
        if i + 1 >= len(dates):
            continue
        if vol.loc[dt, risk_ids].isna().any() or signals.loc[dt, risk_ids].isna().any():
            continue

        target = target_weights(signals.loc[dt], vol.loc[dt], universe, strategy)
        targets.loc[dt] = target
        proposed = apply_inertia(current, target, strategy.inertia_l1, strategy.inertia_asset)
        pending = proposed

    equity = equity.astype(float)
    returns = equity.pct_change().fillna(0.0)
    return BacktestResult(
        name=name,
        broker=broker.name,
        equity=equity,
        returns=returns,
        weights=weights_held,
        cash_weight=cash_w,
        turnover=turnover,
        costs=cost_dollars,
        signals=signals,
        target_weights=targets,
        vol=vol,
    )


def buy_and_hold_mix(
    prices: pd.DataFrame,
    mix: dict[str, float],
    universe: Universe,
    strategy: StrategyConfig,
    costs: CostConfig,
    broker: BrokerCosts,
    name: str,
    start_on: pd.Timestamp | None = None,
) -> BacktestResult:
    """Constant mix, weekly rebalanced, next-close execution, same cost model."""
    risk_ids = universe.risk_ids()
    rets = prices.pct_change()
    rebalance_dates = set(weekly_rebalance_dates(prices.index))
    dates = list(prices.index)

    target = pd.Series(0.0, index=risk_ids)
    for asset_id, w in mix.items():
        if asset_id == "cash":
            continue
        target[asset_id] = w
    if float(target.sum()) > strategy.gross_cap:
        target *= strategy.gross_cap / float(target.sum())

    equity = pd.Series(index=prices.index, dtype=float)
    weights_held = pd.DataFrame(0.0, index=prices.index, columns=risk_ids)
    cash_w = pd.Series(index=prices.index, dtype=float)
    turnover = pd.Series(0.0, index=prices.index)
    cost_dollars = pd.Series(0.0, index=prices.index)

    nav = float(universe.capital)
    current = pd.Series(0.0, index=risk_ids)
    pending: pd.Series | None = None
    dummy_signals = pd.DataFrame(np.nan, index=prices.index, columns=risk_ids)
    dummy_targets = pd.DataFrame(0.0, index=prices.index, columns=risk_ids)
    dummy_vol = pd.DataFrame(np.nan, index=prices.index, columns=risk_ids)

    for i, dt in enumerate(dates):
        if i == 0:
            equity.iloc[i] = nav
            cash_w.iloc[i] = 1.0
            continue
        asset_ret = rets.loc[dt, risk_ids].fillna(0.0)
        cash_ret = float(rets.loc[dt, "cash"]) if pd.notna(rets.loc[dt, "cash"]) else 0.0
        port_ret = float((current * asset_ret).sum() + (1.0 - float(current.sum())) * cash_ret)
        nav *= 1.0 + port_ret
        if pending is not None:
            delta = pending - current
            traded_notional = delta * nav
            cost = trade_cost_dollars(
                traded_notional,
                prices.loc[dt, risk_ids],
                universe,
                broker,
                costs.slippage_bps,
            )
            nav -= cost
            cost_dollars.loc[dt] = cost
            turnover.loc[dt] = float(delta.abs().sum())
            current = pending
            pending = None
        equity.iloc[i] = nav
        weights_held.loc[dt] = current
        cash_w.iloc[i] = 1.0 - float(current.sum())
        if dt in rebalance_dates and i + 1 < len(dates):
            if start_on is not None and dt < start_on:
                continue
            dummy_targets.loc[dt] = target
            pending = apply_inertia(current, target, strategy.inertia_l1, strategy.inertia_asset)

    equity = equity.astype(float)
    return BacktestResult(
        name=name,
        broker=broker.name,
        equity=equity,
        returns=equity.pct_change().fillna(0.0),
        weights=weights_held,
        cash_weight=cash_w,
        turnover=turnover,
        costs=cost_dollars,
        signals=dummy_signals,
        target_weights=dummy_targets,
        vol=dummy_vol,
    )
