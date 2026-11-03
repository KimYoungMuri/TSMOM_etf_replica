from __future__ import annotations

import pandas as pd

from trend.config import StrategyConfig, Universe


def target_weights(
    forecast: pd.Series,
    vol: pd.Series,
    universe: Universe,
    strategy: StrategyConfig,
) -> pd.Series:
    """Inverse-vol long/cash weights with equal asset-class risk budgets.

    w_i = b_i * f_i * vol_target / sigma_i, then cap gross at strategy.gross_cap.
    Unallocated capital stays in cash. We never scale up when few names are on.
    """
    budgets = universe.member_risk_budgets()
    raw = {}
    for asset_id in universe.risk_ids():
        f = float(forecast[asset_id]) if pd.notna(forecast[asset_id]) else 0.0
        sigma = float(vol[asset_id]) if pd.notna(vol[asset_id]) else float("nan")
        if f <= 0 or not sigma or sigma <= 0 or pd.isna(sigma):
            raw[asset_id] = 0.0
            continue
        raw[asset_id] = budgets[asset_id] * f * strategy.vol_target / sigma
    weights = pd.Series(raw, dtype=float)
    gross = float(weights.clip(lower=0).sum())
    if gross > strategy.gross_cap and gross > 0:
        weights *= strategy.gross_cap / gross
    weights = weights.clip(lower=0)
    return weights


def apply_inertia(
    current: pd.Series,
    target: pd.Series,
    inertia_l1: float,
    inertia_asset: float,
) -> pd.Series:
    """Keep current weights unless the move is large enough to be worth trading."""
    current = current.reindex(target.index).fillna(0.0)
    delta = target - current
    l1 = float(delta.abs().sum())
    if l1 < inertia_l1:
        return current
    traded = current.copy()
    for asset_id in target.index:
        if abs(delta[asset_id]) >= inertia_asset:
            traded[asset_id] = target[asset_id]
    traded = traded.clip(lower=0)
    if float(traded.sum()) > 1.0:
        traded *= 1.0 / float(traded.sum())
    return traded
