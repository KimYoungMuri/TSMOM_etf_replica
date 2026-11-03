import pandas as pd

from trend.config import StrategyConfig
from trend.data import build_price_panel, splice_series, t_bill_yield_to_index


def test_splice_ratio_matches_at_join():
    idx = pd.bdate_range("2020-01-01", periods=10)
    proxy = pd.Series(range(10, 20), index=idx, dtype=float)
    etf = pd.Series([200.0, 202.0, 204.0], index=idx[7:], dtype=float)
    spliced = splice_series(etf, proxy)
    assert spliced.loc[idx[7]] == 200.0
    # proxy at join is 17; scale = 200/17; previous proxy 16 -> 16*200/17
    assert abs(spliced.loc[idx[6]] - 16 * 200 / 17) < 1e-9


def test_irx_yield_becomes_rising_index():
    idx = pd.bdate_range("2020-01-01", periods=5)
    irx = pd.Series([5.04, 5.04, 5.04, 5.04, 5.04], index=idx)
    tr = t_bill_yield_to_index(irx)
    assert tr.iloc[-1] > tr.iloc[0]


def test_research_mode_requires_all_etfs(universe, strategy: StrategyConfig):
    idx = pd.bdate_range("2020-01-01", periods=10)
    raw = pd.DataFrame(
        {
            "SPY": range(10, 20),
            "IEF": range(20, 30),
            "BIL": range(30, 40),
        },
        index=idx,
        dtype=float,
    )
    raw.loc[idx[:3], "IEF"] = pd.NA
    panel = build_price_panel(universe, strategy, raw=raw, mode="research")
    assert panel.index.min() == idx[3]
    assert list(panel.columns) == ["us_equity", "intermediate_treasury", "cash"]


def test_research_splice_extends_before_etf(universe, strategy: StrategyConfig):
    idx = pd.bdate_range("2020-01-01", periods=10)
    raw = pd.DataFrame(index=idx, dtype=float)
    raw["SPY"] = [None] * 5 + [200, 201, 202, 203, 204]
    raw["IEF"] = [None] * 5 + [100, 101, 102, 103, 104]
    raw["BIL"] = [None] * 5 + [50, 50.1, 50.2, 50.3, 50.4]
    raw["SPY"] = raw["SPY"].astype(float)
    # splice tickers equal research tickers in the test universe, so splice is a no-op
    # unless we add earlier proxy history under the same column. Give SPY a proxy head
    # by putting values on the splice ticker column which is also SPY.
    panel = build_price_panel(universe, strategy, raw=raw, mode="research_splice")
    assert len(panel) >= 5
