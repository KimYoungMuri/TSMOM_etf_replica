from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


@dataclass(frozen=True)
class Instrument:
    id: str
    name: str
    asset_class: str
    research_ticker: str
    live_ticker: str
    inception: str
    live_inception: str
    half_spread_bps: float
    splice_ticker: str | None = None
    notes: str = ""

    def ticker(self, mode: str) -> str:
        if mode == "live":
            return self.live_ticker
        return self.research_ticker


@dataclass(frozen=True)
class Universe:
    capital: float
    asset_class_budgets: dict[str, float]
    risk_assets: tuple[Instrument, ...]
    cash: Instrument
    exclusions: tuple[str, ...]

    def risk_ids(self) -> list[str]:
        return [inst.id for inst in self.risk_assets]

    def research_tickers(self) -> list[str]:
        return [inst.research_ticker for inst in self.risk_assets] + [self.cash.research_ticker]

    def live_tickers(self) -> list[str]:
        return [inst.live_ticker for inst in self.risk_assets] + [self.cash.live_ticker]

    def splice_tickers(self) -> list[str]:
        tickers = []
        for inst in (*self.risk_assets, self.cash):
            if inst.splice_ticker:
                tickers.append(inst.splice_ticker)
        return tickers

    def member_risk_budgets(self) -> dict[str, float]:
        counts: dict[str, int] = {}
        for inst in self.risk_assets:
            counts[inst.asset_class] = counts.get(inst.asset_class, 0) + 1
        budgets = {}
        for inst in self.risk_assets:
            class_budget = self.asset_class_budgets[inst.asset_class]
            budgets[inst.id] = class_budget / counts[inst.asset_class]
        return budgets

    def by_id(self, asset_id: str) -> Instrument:
        if asset_id == self.cash.id:
            return self.cash
        for inst in self.risk_assets:
            if inst.id == asset_id:
                return inst
        raise KeyError(asset_id)

    def half_spreads_bps(self) -> dict[str, float]:
        return {inst.id: inst.half_spread_bps for inst in self.risk_assets}


@dataclass(frozen=True)
class BrokerCosts:
    name: str
    label: str
    commission_per_share: float
    commission_min: float
    notes: str = ""


@dataclass(frozen=True)
class CostConfig:
    slippage_bps: float
    brokers: dict[str, BrokerCosts]


@dataclass(frozen=True)
class StrategyConfig:
    signal: str
    lookback_days: int
    sma_days: int
    fast_ma_days: int
    slow_ma_days: int
    vol_center_of_mass_days: int
    vol_target: float
    gross_cap: float
    rebalance: str
    execution: str
    inertia_l1: float
    inertia_asset: float
    data_mode: str


def _read_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def load_universe(path: Path | None = None) -> Universe:
    raw = _read_yaml(path or CONFIG_DIR / "universe.yaml")
    assets = tuple(Instrument(**item) for item in raw["risk_assets"])
    cash = Instrument(asset_class="cash", splice_ticker=raw["cash"].get("splice_ticker"), **{
        k: v for k, v in raw["cash"].items() if k != "splice_ticker"
    })
    return Universe(
        capital=float(raw["capital"]),
        asset_class_budgets={k: float(v) for k, v in raw["asset_class_budgets"].items()},
        risk_assets=assets,
        cash=cash,
        exclusions=tuple(raw.get("exclusions", [])),
    )


def load_costs(path: Path | None = None) -> CostConfig:
    raw = _read_yaml(path or CONFIG_DIR / "costs.yaml")
    brokers = {
        name: BrokerCosts(
            name=name,
            label=cfg["label"],
            commission_per_share=float(cfg["commission_per_share"]),
            commission_min=float(cfg["commission_min"]),
            notes=cfg.get("notes", ""),
        )
        for name, cfg in raw["brokers"].items()
    }
    return CostConfig(slippage_bps=float(raw["slippage_bps"]), brokers=brokers)


def load_strategy(path: Path | None = None) -> StrategyConfig:
    raw = _read_yaml(path or CONFIG_DIR / "strategy.yaml")
    return StrategyConfig(
        signal=raw["signal"],
        lookback_days=int(raw["lookback_days"]),
        sma_days=int(raw["sma_days"]),
        fast_ma_days=int(raw["fast_ma_days"]),
        slow_ma_days=int(raw["slow_ma_days"]),
        vol_center_of_mass_days=int(raw["vol_center_of_mass_days"]),
        vol_target=float(raw["vol_target"]),
        gross_cap=float(raw["gross_cap"]),
        rebalance=raw["rebalance"],
        execution=raw["execution"],
        inertia_l1=float(raw["inertia_l1"]),
        inertia_asset=float(raw["inertia_asset"]),
        data_mode=raw["data_mode"],
    )
