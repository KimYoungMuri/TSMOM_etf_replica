from __future__ import annotations

import numpy as np
import pandas as pd

from trend.config import StrategyConfig, Universe


def ewma_vol(returns: pd.DataFrame, center_of_mass_days: int) -> pd.DataFrame:
    """Ex-ante annualized EWMA vol. Today's vol does not include today's return."""
    lam_span = center_of_mass_days
    var = returns.pow(2).ewm(com=lam_span, min_periods=center_of_mass_days, adjust=False).mean()
    daily = np.sqrt(var)
    return daily.shift(1) * np.sqrt(252)


def binary_forecast(
    prices: pd.DataFrame,
    universe: Universe,
    strategy: StrategyConfig,
) -> pd.DataFrame:
    risk = prices[universe.risk_ids()]
    cash = prices["cash"]
    if strategy.signal == "tsmom_12m":
        asset_ret = risk.pct_change(strategy.lookback_days)
        cash_ret = cash.pct_change(strategy.lookback_days)
        excess = asset_ret.sub(cash_ret, axis=0)
        signal = (excess > 0).astype(float)
    elif strategy.signal == "sma_10m":
        ma = risk.rolling(strategy.sma_days, min_periods=strategy.sma_days).mean()
        signal = (risk > ma).astype(float)
    elif strategy.signal == "macross_50_200":
        fast = risk.rolling(strategy.fast_ma_days, min_periods=strategy.fast_ma_days).mean()
        slow = risk.rolling(strategy.slow_ma_days, min_periods=strategy.slow_ma_days).mean()
        signal = (fast > slow).astype(float)
    else:
        raise ValueError(f"Unknown signal {strategy.signal}")
    valid = risk.notna().mul(cash.notna(), axis=0)
    return signal.where(valid, np.nan)


def weekly_rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    weeks = pd.Series(index, index=index).groupby(index.to_period("W-FRI")).max()
    return pd.DatetimeIndex(weeks.values)
