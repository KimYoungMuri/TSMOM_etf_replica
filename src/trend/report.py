from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from trend.backtest import BacktestResult
from trend.config import ROOT, Universe
from trend.evaluate import metrics_table

REPORTS = ROOT / "reports"


def write_reports(
    results_by_broker: dict[str, dict[str, BacktestResult]],
    prices: pd.DataFrame,
    universe: Universe,
    outdir: Path | None = None,
) -> Path:
    outdir = outdir or REPORTS
    outdir.mkdir(parents=True, exist_ok=True)

    tables = []
    equity_cols = {}
    for broker, results in results_by_broker.items():
        table = metrics_table(results, prices)
        tables.append(table)
        for name, res in results.items():
            equity_cols[f"{broker}:{name}"] = res.equity
    metrics = pd.concat(tables, ignore_index=True)
    metrics.to_csv(outdir / "metrics.csv", index=False)

    equity = pd.DataFrame(equity_cols)
    equity.to_csv(outdir / "equity_curves.csv")

    _plot_equity(results_by_broker, outdir / "equity_curves.png")
    primary = next(iter(results_by_broker.values()))
    _plot_weights(primary["trend_long_cash"], outdir / "trend_weights.png")
    summary = render_summary(metrics, universe, prices)
    (outdir / "summary.md").write_text(summary)
    return outdir


def render_summary(metrics: pd.DataFrame, universe: Universe, prices: pd.DataFrame) -> str:
    tickers = ", ".join(
        f"{inst.id}={inst.research_ticker}/{inst.live_ticker}" for inst in universe.risk_assets
    )
    start, end = prices.index[0].date(), prices.index[-1].date()
    lines = [
        "# Slow trend-following baseline",
        "",
        f"Universe (research/live): {tickers}",
        f"Cash: {universe.cash.research_ticker}/{universe.cash.live_ticker}",
        f"Price window: {start} to {end}",
        f"Capital: ${universe.capital:,.0f}",
        "",
        "Signal is 12-month excess return sign, long/cash, inverse-vol with equal class risk budgets, weekly next-close execution, 10% L1 inertia, 100% gross cap.",
        "",
        "A system that merely takes less equity exposure should not beat vol-matched SPY or the always-long same-universe book. Those two are the honest tests.",
        "",
        "## Metrics",
        "",
        _md_table(metrics),
        "",
        "## How to read this",
        "",
        "- `trend_long_cash` is the strategy.",
        "- `vol_matched_spy` is SPY mixed with cash to the same full-sample realized vol. If trend only wins vs raw SPY, this absorbs the 'less equity' effect.",
        "- `same_universe_always_long` is the 8 ETFs with the same inverse-vol class budgets, never going to cash. If trend only wins vs this, the edge is the on/off switch.",
        "- `sixty_forty` is 60% SPY / 40% IEF, weekly rebalanced.",
        "- `cost_drag_bps` is annualized implementation cost in basis points of starting capital.",
        "- IBKR Pro's $1 minimum per order is why inertia exists; Robinhood and IBKR Lite are commission-free.",
        "",
    ]
    return "\n".join(lines)


def _md_table(df: pd.DataFrame) -> str:
    show = df.copy()
    pct_cols = ["cagr", "ann_vol", "max_drawdown", "total_return", "avg_gross"]
    for col in pct_cols:
        show[col] = show[col].map(lambda x: f"{x:.1%}")
    show["sharpe"] = show["sharpe"].map(lambda x: f"{x:.2f}")
    show["calmar"] = show["calmar"].map(lambda x: f"{x:.2f}")
    show["avg_turnover"] = show["avg_turnover"].map(lambda x: f"{x:.2f}")
    show["cost_drag_bps"] = show["cost_drag_bps"].map(lambda x: f"{x:.0f}")
    show["spy_corr"] = show["spy_corr"].map(lambda x: f"{x:.2f}")
    cols = [
        "broker",
        "name",
        "cagr",
        "ann_vol",
        "sharpe",
        "max_drawdown",
        "calmar",
        "avg_gross",
        "avg_turnover",
        "cost_drag_bps",
        "spy_corr",
    ]
    show = show[cols]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in show.to_dict("records")]
    return "\n".join([header, sep, *rows])


def _plot_equity(results_by_broker: dict[str, dict[str, BacktestResult]], path: Path) -> None:
    fig, axes = plt.subplots(
        nrows=len(results_by_broker),
        figsize=(10, 4 * len(results_by_broker)),
        sharex=True,
        squeeze=False,
    )
    for ax, (broker, results) in zip(axes[:, 0], results_by_broker.items()):
        for name, res in results.items():
            eq = res.equity.dropna()
            ax.plot(eq.index, eq.values, label=name)
        ax.set_title(f"Equity curves ({broker})")
        ax.set_ylabel("NAV ($)")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(True, alpha=0.3)
    axes[-1, 0].set_xlabel("Date")
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def _plot_weights(result: BacktestResult, path: Path) -> None:
    w = result.weights.copy()
    w["cash"] = result.cash_weight
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.stackplot(w.index, [w[c].values for c in w.columns], labels=list(w.columns), alpha=0.9)
    ax.set_title("Trend long/cash weights")
    ax.set_ylabel("Portfolio weight")
    ax.set_ylim(0, 1)
    ax.legend(loc="upper left", ncol=3, fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
