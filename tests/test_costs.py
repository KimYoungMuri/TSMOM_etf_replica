import pandas as pd

from trend.costs import trade_cost_dollars


def test_robinhood_is_spread_only(universe, costs):
    traded = pd.Series({"us_equity": 1000.0, "intermediate_treasury": 0.0})
    prices = pd.Series({"us_equity": 100.0, "intermediate_treasury": 100.0})
    cost = trade_cost_dollars(traded, prices, universe, costs.brokers["robinhood"], slippage_bps=2.0)
    # 1bp half-spread + 2bp slippage on $1000
    assert abs(cost - 1000 * 3 / 10_000) < 1e-9


def test_ibkr_pro_minimum_commission(universe, costs):
    traded = pd.Series({"us_equity": 200.0, "intermediate_treasury": 200.0})
    prices = pd.Series({"us_equity": 100.0, "intermediate_treasury": 100.0})
    cost = trade_cost_dollars(traded, prices, universe, costs.brokers["ibkr_pro"], slippage_bps=0.0)
    spread = 200 * 1 / 10_000 * 2
    assert abs(cost - (spread + 2.0)) < 1e-9
