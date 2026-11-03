from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trend.config import BrokerCosts, CostConfig, Instrument, StrategyConfig, Universe


def make_instrument(asset_id: str, asset_class: str, ticker: str, spread: float = 1.0) -> Instrument:
    return Instrument(
        id=asset_id,
        name=asset_id,
        asset_class=asset_class,
        research_ticker=ticker,
        live_ticker=ticker,
        inception="2007-01-01",
        live_inception="2007-01-01",
        half_spread_bps=spread,
        splice_ticker=ticker,
    )


@pytest.fixture
def universe() -> Universe:
    return Universe(
        capital=10_000,
        asset_class_budgets={"equity": 0.5, "bonds": 0.5},
        risk_assets=(
            make_instrument("us_equity", "equity", "SPY"),
            make_instrument("intermediate_treasury", "bonds", "IEF"),
        ),
        cash=make_instrument("cash", "cash", "BIL"),
        exclusions=(),
    )


@pytest.fixture
def strategy() -> StrategyConfig:
    return StrategyConfig(
        signal="tsmom_12m",
        lookback_days=20,
        sma_days=10,
        fast_ma_days=5,
        slow_ma_days=10,
        vol_center_of_mass_days=10,
        vol_target=0.10,
        gross_cap=1.0,
        rebalance="weekly",
        execution="next_close",
        inertia_l1=0.0,
        inertia_asset=0.0,
        data_mode="research",
    )


@pytest.fixture
def costs() -> CostConfig:
    return CostConfig(
        slippage_bps=2.0,
        brokers={
            "robinhood": BrokerCosts("robinhood", "Robinhood", 0.0, 0.0),
            "ibkr_pro": BrokerCosts("ibkr_pro", "IBKR Pro", 0.005, 1.0),
        },
    )


def trending_prices(n: int = 400, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2015-01-01", periods=n)
    def path(drift, vol, start):
        r = drift / 252 + vol / np.sqrt(252) * rng.standard_normal(n)
        return start * np.exp(np.cumsum(r))
    return pd.DataFrame(
        {
            "us_equity": path(0.12, 0.16, 100),
            "intermediate_treasury": path(0.04, 0.07, 100),
            "cash": path(0.02, 0.005, 100),
        },
        index=idx,
    )
