import numpy as np
import pandas as pd

from conftest import trending_prices
from trend.backtest import run_backtest
from trend.evaluate import run_evaluation, vol_matched_spy_weight


def test_fills_are_next_session_not_signal_bar(universe, strategy, costs):
    prices = trending_prices(n=250)
    result = run_backtest(prices, universe, strategy, costs, costs.brokers["robinhood"])
    targets = result.target_weights.sum(axis=1)
    held = result.weights.sum(axis=1)
    first_target = targets[targets > 0].index.min()
    first_held = held[held > 0].index.min()
    assert first_held > first_target


def test_always_long_stays_invested(universe, strategy, costs):
    prices = trending_prices()
    result = run_backtest(
        prices,
        universe,
        strategy,
        costs,
        costs.brokers["robinhood"],
        always_long=True,
    )
    active = result.weights.loc[result.turnover.replace(0, np.nan).first_valid_index() :]
    assert float(active.sum(axis=1).median()) > 0.3


def test_no_leverage(universe, strategy, costs):
    prices = trending_prices()
    result = run_backtest(prices, universe, strategy, costs, costs.brokers["robinhood"])
    gross = result.weights.sum(axis=1) + 1e-12
    assert float(gross.max()) <= 1.0 + 1e-8


def test_evaluation_has_three_benchmarks(universe, strategy, costs):
    prices = trending_prices(n=500)
    results = run_evaluation(prices, universe, strategy, costs, costs.brokers["robinhood"])
    assert set(results) == {
        "trend_long_cash",
        "same_universe_always_long",
        "sixty_forty",
        "vol_matched_spy",
    }
    spy_w = vol_matched_spy_weight(results["trend_long_cash"], prices["us_equity"].pct_change())
    assert 0 <= spy_w <= 1
