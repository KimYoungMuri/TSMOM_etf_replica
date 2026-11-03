from __future__ import annotations

import argparse

from trend.backtest import BacktestResult
from trend.config import ROOT, load_costs, load_strategy, load_universe
from trend.data import build_price_panel, download_prices, load_cached_prices, required_tickers
from trend.evaluate import run_evaluation
from trend.report import write_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Slow trend-following research harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    dl = sub.add_parser("download", help="Download Yahoo prices for research, live, and splice tickers")
    dl.set_defaults(func=cmd_download)

    run = sub.add_parser("run", help="Run the baseline and honest benchmarks")
    run.add_argument(
        "--broker",
        nargs="+",
        default=["robinhood", "ibkr_pro"],
        help="Cost models to run (robinhood, ibkr_lite, ibkr_pro)",
    )
    run.add_argument(
        "--mode",
        choices=["research", "research_splice", "live"],
        default=None,
        help="Override strategy.yaml data_mode",
    )
    run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


def cmd_download(_args: argparse.Namespace) -> int:
    universe = load_universe()
    tickers = list(
        dict.fromkeys(
            universe.research_tickers()
            + universe.live_tickers()
            + universe.splice_tickers()
        )
    )
    print(f"Downloading {len(tickers)} tickers…")
    prices = download_prices(tickers)
    print(f"Cached {prices.shape[1]} series, {prices.index.min().date()} → {prices.index.max().date()}")
    print(f"Wrote {ROOT / 'data' / 'cache' / 'prices.parquet'}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    universe = load_universe()
    strategy = load_strategy()
    costs = load_costs()
    mode = args.mode or strategy.data_mode
    raw = load_cached_prices()
    missing = [t for t in required_tickers(universe, mode) if t not in raw.columns]
    if missing:
        raise SystemExit(f"Missing tickers {missing}. Run: python -m trend download")
    prices = build_price_panel(universe, strategy, raw=raw, mode=mode)
    print(f"Mode={mode}  rows={len(prices)}  {prices.index.min().date()} → {prices.index.max().date()}")

    results_by_broker: dict[str, dict[str, BacktestResult]] = {}
    for name in args.broker:
        if name not in costs.brokers:
            raise SystemExit(f"Unknown broker {name}. Choose from {list(costs.brokers)}")
        print(f"Running {name}…")
        results_by_broker[name] = run_evaluation(prices, universe, strategy, costs, costs.brokers[name])

    outdir = write_reports(results_by_broker, prices, universe)
    print((outdir / "summary.md").read_text())
    print(f"Wrote reports to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
