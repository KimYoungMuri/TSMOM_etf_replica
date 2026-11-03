from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from trend.config import ROOT, Instrument, StrategyConfig, Universe

CACHE_DIR = ROOT / "data" / "cache"


class DataError(RuntimeError):
    pass


def download_prices(tickers: list[str], cache_dir: Path | None = None) -> pd.DataFrame:
    import yfinance as yf

    cache_dir = cache_dir or CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    unique = list(dict.fromkeys(tickers))
    raw = yf.download(
        unique,
        period="max",
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="ticker",
    )
    closes = _extract_closes(raw, unique)
    if closes.empty:
        raise DataError(f"yfinance returned no prices for {unique}")
    path = cache_dir / "prices.parquet"
    closes.to_parquet(path)
    return closes


def load_cached_prices(cache_dir: Path | None = None) -> pd.DataFrame:
    path = (cache_dir or CACHE_DIR) / "prices.parquet"
    if not path.exists():
        raise DataError(f"No price cache at {path}. Run: python -m trend download")
    return pd.read_parquet(path)


def required_tickers(universe: Universe, mode: str) -> list[str]:
    tickers = universe.research_tickers()
    if mode == "live":
        tickers = universe.live_tickers()
    if mode == "research_splice":
        tickers = tickers + universe.splice_tickers()
    return list(dict.fromkeys(tickers))


def build_price_panel(
    universe: Universe,
    strategy: StrategyConfig,
    raw: pd.DataFrame | None = None,
    cache_dir: Path | None = None,
    mode: str | None = None,
) -> pd.DataFrame:
    """Return a panel indexed by date with columns = instrument ids, plus 'cash'.

    research: ETF prices only, aligned from the first date every risk asset exists.
    research_splice: index/fund proxies before ETF inception, ratio-spliced.
    live: live tickers only (shorter, what we would actually hold today).
    """
    mode = mode or strategy.data_mode
    if raw is None:
        raw = load_cached_prices(cache_dir)
    series = {}
    for inst in universe.risk_assets:
        series[inst.id] = _series_for(inst, raw, mode)
    series["cash"] = _series_for(universe.cash, raw, mode)
    panel = pd.DataFrame(series).sort_index()
    panel = panel.replace(0.0, np.nan)
    if mode == "research_splice":
        panel = panel.dropna(how="all").ffill(limit=3)
        first_risk = panel[universe.risk_ids()].dropna().index.min()
        panel = panel.loc[first_risk:]
    else:
        panel = panel.dropna(subset=universe.risk_ids())
        panel["cash"] = panel["cash"].ffill()
        panel = panel.dropna()
    if panel.empty:
        raise DataError(f"No overlapping prices in mode={mode}")
    return panel


def _series_for(inst: Instrument, raw: pd.DataFrame, mode: str) -> pd.Series:
    primary = inst.live_ticker if mode == "live" else inst.research_ticker
    etf = _col(raw, primary)
    if mode != "research_splice" or not inst.splice_ticker:
        return etf
    proxy = _col(raw, inst.splice_ticker)
    if inst.splice_ticker == "^IRX":
        proxy = t_bill_yield_to_index(proxy)
    return splice_series(etf, proxy)


def t_bill_yield_to_index(irx_pct: pd.Series) -> pd.Series:
    """Convert ^IRX (13-week T-bill yield, percent) into a total-return index."""
    daily = (irx_pct.astype(float) / 100.0) / 252.0
    return (1.0 + daily.fillna(0.0)).cumprod()


def splice_series(etf: pd.Series, proxy: pd.Series) -> pd.Series:
    """Ratio-splice proxy history onto an ETF at the ETF's first valid date.

    Research-only. Live trading uses the ETF, not the proxy.
    """
    etf = etf.dropna()
    proxy = proxy.dropna()
    if etf.empty:
        return proxy
    join = etf.index[0]
    if join not in proxy.index:
        prior = proxy.index[proxy.index <= join]
        if len(prior) == 0:
            return etf
        join = prior[-1]
    scale = float(etf.loc[etf.index[0]] / proxy.loc[join])
    head = proxy.loc[:join].iloc[:-1] * scale
    combined = pd.concat([head, etf])
    combined = combined[~combined.index.duplicated(keep="last")]
    return combined.sort_index()


def _extract_closes(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if isinstance(raw.columns, pd.MultiIndex):
        fields = raw.columns.get_level_values(-1)
        if "Close" in set(fields):
            closes = raw.xs("Close", axis=1, level=-1)
        else:
            closes = raw.xs("Close", axis=1, level=0)
        closes.columns = [str(c) for c in closes.columns]
        return closes
    if "Close" in raw.columns:
        return raw[["Close"]].rename(columns={"Close": tickers[0]})
    return raw


def _col(raw: pd.DataFrame, ticker: str) -> pd.Series:
    if ticker in raw.columns:
        return raw[ticker].astype(float)
    # yfinance sometimes strips the equals sign or caret in column names
    for col in raw.columns:
        if str(col).upper() == ticker.upper():
            return raw[col].astype(float)
    return pd.Series(dtype=float, name=ticker)
