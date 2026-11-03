import pandas as pd

from trend.sizing import apply_inertia, target_weights


def test_inverse_vol_gives_more_notional_to_quiet_asset(universe, strategy):
    forecast = pd.Series({"us_equity": 1.0, "intermediate_treasury": 1.0})
    vol = pd.Series({"us_equity": 0.20, "intermediate_treasury": 0.05})
    w = target_weights(forecast, vol, universe, strategy)
    assert w["intermediate_treasury"] > w["us_equity"]
    assert float(w.sum()) <= strategy.gross_cap + 1e-12


def test_flat_signal_is_cash(universe, strategy):
    forecast = pd.Series({"us_equity": 0.0, "intermediate_treasury": 0.0})
    vol = pd.Series({"us_equity": 0.20, "intermediate_treasury": 0.05})
    w = target_weights(forecast, vol, universe, strategy)
    assert float(w.sum()) == 0.0


def test_gross_cap_scales_down(universe, strategy):
    forecast = pd.Series({"us_equity": 1.0, "intermediate_treasury": 1.0})
    vol = pd.Series({"us_equity": 0.02, "intermediate_treasury": 0.02})
    w = target_weights(forecast, vol, universe, strategy)
    assert abs(float(w.sum()) - 1.0) < 1e-10


def test_inertia_skips_small_l1():
    current = pd.Series({"a": 0.50, "b": 0.20})
    target = pd.Series({"a": 0.52, "b": 0.21})
    held = apply_inertia(current, target, inertia_l1=0.10, inertia_asset=0.02)
    pd.testing.assert_series_equal(held, current)


def test_inertia_trades_large_move():
    current = pd.Series({"a": 0.50, "b": 0.00})
    target = pd.Series({"a": 0.00, "b": 0.40})
    held = apply_inertia(current, target, inertia_l1=0.10, inertia_asset=0.02)
    assert held["a"] == 0.0
    assert held["b"] == 0.40
