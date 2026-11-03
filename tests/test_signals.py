import numpy as np
import pandas as pd

from trend.config import Universe
from trend.signals import binary_forecast, ewma_vol, weekly_rebalance_dates


def test_tsmom_positive_excess_is_long(universe: Universe, strategy):
    idx = pd.bdate_range("2020-01-01", periods=40)
    prices = pd.DataFrame(
        {
            "us_equity": np.linspace(100, 150, 40),
            "intermediate_treasury": np.linspace(100, 90, 40),
            "cash": np.linspace(100, 101, 40),
        },
        index=idx,
    )
    f = binary_forecast(prices, universe, strategy)
    last = f.iloc[-1]
    assert last["us_equity"] == 1.0
    assert last["intermediate_treasury"] == 0.0


def test_ewma_vol_is_ex_ante():
    idx = pd.bdate_range("2020-01-01", periods=80)
    r = pd.Series(0.0, index=idx)
    r.iloc[50] = 0.20
    vol = ewma_vol(pd.DataFrame({"a": r}), center_of_mass_days=10)["a"]
    assert pd.isna(vol.iloc[50]) or vol.iloc[50] < vol.iloc[51]
    assert vol.iloc[51] > vol.iloc[49]


def test_weekly_rebalance_is_last_session_of_week():
    idx = pd.bdate_range("2024-01-02", periods=10)
    dates = weekly_rebalance_dates(idx)
    assert all(d in idx for d in dates)
    assert dates[0] == idx[idx.to_period("W-FRI") == idx[0].to_period("W-FRI")].max()
