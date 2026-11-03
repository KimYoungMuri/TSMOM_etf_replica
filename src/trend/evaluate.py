from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from trend.backtest import BacktestResult, buy_and_hold_mix, run_backtest
from trend.config import BrokerCosts, CostConfig, StrategyConfig, Universe


@dataclass
class Metrics:
    name: str
    broker: str
    start: str
    end: str
    cagr: float
    ann_vol: float
    sharpe: float
    max_drawdown: float
    calmar: float
    total_return: float
    avg_gross: float
    avg_turnover: float
    cost_drag_bps: float
    spy_corr: float


def summarize(result: BacktestResult, cash_returns: pd.Series, spy_returns: pd.Series) -> Metrics:
    equity = result.equity.dropna()
    rets = result.returns.loc[equity.index].iloc[1:]
    cash = cash_returns.reindex(rets.index).fillna(0.0)
    spy = spy_returns.reindex(rets.index).fillna(0.0)
    excess = rets - cash
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    total = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = float((1.0 + total) ** (1.0 / years) - 1.0) if years > 0 else 0.0
    ann_vol = float(rets.std() * np.sqrt(252))
    sharpe = float(excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0.0
    dd = equity / equity.cummax() - 1.0
    max_dd = float(dd.min())
    calmar = float(cagr / abs(max_dd)) if max_dd < 0 else 0.0
    avg_gross = float(result.weights.sum(axis=1).mean())
    # turnover is L1 weight change on trade days; annualize by summing / years
    avg_turnover = float(result.turnover.sum() / years) if years > 0 else 0.0
    cost_drag = float(result.costs.sum() / equity.iloc[0] / years) if years > 0 else 0.0
    corr = float(rets.corr(spy)) if spy.std() > 0 else 0.0
    return Metrics(
        name=result.name,
        broker=result.broker,
        start=str(equity.index[0].date()),
        end=str(equity.index[-1].date()),
        cagr=cagr,
        ann_vol=ann_vol,
        sharpe=sharpe,
        max_drawdown=max_dd,
        calmar=calmar,
        total_return=total,
        avg_gross=avg_gross,
        avg_turnover=avg_turnover,
        cost_drag_bps=cost_drag * 10_000,
        spy_corr=corr,
    )


def vol_matched_spy_weight(strategy: BacktestResult, spy_returns: pd.Series) -> float:
    """Full-sample constant SPY weight that matches strategy realized vol."""
    s_vol = float(strategy.returns.iloc[1:].std())
    spy = spy_returns.reindex(strategy.returns.index).iloc[1:]
    spy_vol = float(spy.std())
    if spy_vol <= 0:
        return 0.0
    return min(1.0, s_vol / spy_vol)


def run_evaluation(
    prices: pd.DataFrame,
    universe: Universe,
    strategy: StrategyConfig,
    costs: CostConfig,
    broker: BrokerCosts,
) -> dict[str, BacktestResult]:
    trend = run_backtest(prices, universe, strategy, costs, broker, name="trend_long_cash")
    traded = trend.turnover[trend.turnover > 0]
    start_on = traded.index.min() if len(traded) else prices.index[0]
    always_long = run_backtest(
        prices,
        universe,
        strategy,
        costs,
        broker,
        name="same_universe_always_long",
        always_long=True,
    )
    spy_weight = vol_matched_spy_weight(_from(trend, start_on), prices["us_equity"].pct_change())
    sixty_forty = buy_and_hold_mix(
        prices,
        {"us_equity": 0.60, "intermediate_treasury": 0.40},
        universe,
        strategy,
        costs,
        broker,
        name="sixty_forty",
        start_on=start_on,
    )
    vol_matched = buy_and_hold_mix(
        prices,
        {"us_equity": spy_weight},
        universe,
        strategy,
        costs,
        broker,
        name="vol_matched_spy",
        start_on=start_on,
    )
    return {
        "trend_long_cash": _from(trend, start_on),
        "same_universe_always_long": _from(always_long, start_on),
        "sixty_forty": _from(sixty_forty, start_on),
        "vol_matched_spy": _from(vol_matched, start_on),
    }


def _from(result: BacktestResult, start_on: pd.Timestamp) -> BacktestResult:
    sl = slice(start_on, None)
    return BacktestResult(
        name=result.name,
        broker=result.broker,
        equity=result.equity.loc[sl],
        returns=result.returns.loc[sl],
        weights=result.weights.loc[sl],
        cash_weight=result.cash_weight.loc[sl],
        turnover=result.turnover.loc[sl],
        costs=result.costs.loc[sl],
        signals=result.signals.loc[sl],
        target_weights=result.target_weights.loc[sl],
        vol=result.vol.loc[sl],
    )


def metrics_table(
    results: dict[str, BacktestResult],
    prices: pd.DataFrame,
) -> pd.DataFrame:
    cash_r = prices["cash"].pct_change()
    spy_r = prices["us_equity"].pct_change()
    rows = [summarize(res, cash_r, spy_r) for res in results.values()]
    df = pd.DataFrame([r.__dict__ for r in rows])
    return df
