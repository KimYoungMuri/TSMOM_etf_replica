from trend.config import load_costs, load_strategy, load_universe


def test_universe_is_eight_etfs_plus_cash():
    u = load_universe()
    assert len(u.risk_assets) == 8
    assert u.cash.id == "cash"
    assert u.cash.live_ticker == "SGOV"
    assert u.cash.research_ticker == "BIL"
    classes = {inst.asset_class for inst in u.risk_assets}
    assert classes == {"equity", "bonds", "commodities", "fx"}


def test_class_budgets_split_equally_within_class():
    u = load_universe()
    b = u.member_risk_budgets()
    assert abs(sum(b.values()) - 1.0) < 1e-12
    equity = [inst.id for inst in u.risk_assets if inst.asset_class == "equity"]
    assert len(equity) == 3
    assert abs(b[equity[0]] - 0.25 / 3) < 1e-12
    fx = [inst.id for inst in u.risk_assets if inst.asset_class == "fx"]
    assert b[fx[0]] == 0.25


def test_research_vs_live_tickers():
    u = load_universe()
    by_id = {inst.id: inst for inst in u.risk_assets}
    assert by_id["us_equity"].research_ticker == "SPY"
    assert by_id["us_equity"].live_ticker == "VTI"
    assert by_id["developed_ex_us"].research_ticker == "EFA"
    assert by_id["developed_ex_us"].live_ticker == "IEFA"
    assert by_id["emerging"].research_ticker == "EEM"
    assert by_id["emerging"].live_ticker == "IEMG"
    assert by_id["broad_commodities"].research_ticker == "DBC"
    assert by_id["broad_commodities"].live_ticker == "PDBC"


def test_strategy_and_cost_defaults():
    s = load_strategy()
    assert s.signal == "tsmom_12m"
    assert s.gross_cap == 1.0
    assert s.execution == "next_close"
    c = load_costs()
    assert c.brokers["robinhood"].commission_min == 0
    assert c.brokers["ibkr_pro"].commission_min == 1.0
