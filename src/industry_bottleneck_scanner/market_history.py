from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import Iterable

from .market_trigger import TickerMarketSnapshot


@dataclass(frozen=True)
class DailyBar:
    trading_date: date
    adjusted_close: float
    volume: float

    def __post_init__(self) -> None:
        if self.adjusted_close <= 0:
            raise ValueError("adjusted_close must be positive")
        if self.volume < 0:
            raise ValueError("volume must be non-negative")


@dataclass(frozen=True)
class TickerMarketHistory:
    ticker: str
    sector: str
    bucket: str
    bars: tuple[DailyBar, ...]

    def __post_init__(self) -> None:
        if not self.ticker.strip():
            raise ValueError("ticker is required")
        if not self.sector.strip():
            raise ValueError("sector is required")
        if not self.bucket.strip():
            raise ValueError("bucket is required")


@dataclass(frozen=True)
class _ComputedHistory:
    ticker: str
    sector: str
    bucket: str
    return_1m: float
    return_3m: float
    return_6m: float
    volume_ratio_20d: float
    pct_from_52w_high: float


MIN_REQUIRED_TRADING_DAYS = 127


def _normalize_bars(bars: Iterable[DailyBar], *, as_of: date) -> tuple[DailyBar, ...]:
    by_date: dict[date, DailyBar] = {}
    for bar in bars:
        if bar.trading_date <= as_of:
            by_date[bar.trading_date] = bar
    return tuple(by_date[item] for item in sorted(by_date))


def _return_over_trading_days(bars: tuple[DailyBar, ...], lookback: int) -> float:
    if len(bars) <= lookback:
        raise ValueError(f"at least {lookback + 1} trading days are required")
    current = bars[-1].adjusted_close
    baseline = bars[-(lookback + 1)].adjusted_close
    return current / baseline - 1.0


def _volume_ratio_20d(bars: tuple[DailyBar, ...]) -> float:
    if len(bars) < 80:
        raise ValueError("at least 80 trading days are required for volume ratio")
    recent = bars[-20:]
    prior = bars[-80:-20]
    recent_average = sum(item.volume for item in recent) / len(recent)
    prior_average = sum(item.volume for item in prior) / len(prior)
    if prior_average <= 0:
        return 1.0 if recent_average <= 0 else float("inf")
    return recent_average / prior_average


def _pct_from_52w_high(bars: tuple[DailyBar, ...]) -> float:
    window = bars[-252:]
    high = max(item.adjusted_close for item in window)
    return bars[-1].adjusted_close / high - 1.0


def _compute_history(item: TickerMarketHistory, *, as_of: date) -> _ComputedHistory:
    bars = _normalize_bars(item.bars, as_of=as_of)
    if len(bars) < MIN_REQUIRED_TRADING_DAYS:
        raise ValueError(
            f"{item.ticker}: at least {MIN_REQUIRED_TRADING_DAYS} trading days are required"
        )
    return _ComputedHistory(
        ticker=item.ticker,
        sector=item.sector,
        bucket=item.bucket,
        return_1m=_return_over_trading_days(bars, 21),
        return_3m=_return_over_trading_days(bars, 63),
        return_6m=_return_over_trading_days(bars, 126),
        volume_ratio_20d=_volume_ratio_20d(bars),
        pct_from_52w_high=_pct_from_52w_high(bars),
    )


def build_market_snapshots(
    histories: Iterable[TickerMarketHistory],
    *,
    market_bars: Iterable[DailyBar],
    as_of: date,
) -> tuple[TickerMarketSnapshot, ...]:
    """Build bottom-up market snapshots without requiring sector ETFs.

    The broad-market return comes from the supplied benchmark history. Sector-relative
    returns use the median 3-month return of the supplied constituent histories in each
    sector. This keeps the canonical aggregation company-first; ETF data can remain an
    optional corroborating input rather than the industry definition.
    """

    items = tuple(histories)
    if not items:
        return ()

    market = _normalize_bars(market_bars, as_of=as_of)
    if len(market) < MIN_REQUIRED_TRADING_DAYS:
        raise ValueError(
            f"market benchmark: at least {MIN_REQUIRED_TRADING_DAYS} trading days are required"
        )
    market_return_1m = _return_over_trading_days(market, 21)
    market_return_3m = _return_over_trading_days(market, 63)
    market_return_6m = _return_over_trading_days(market, 126)

    computed = tuple(_compute_history(item, as_of=as_of) for item in items)
    sector_returns: dict[str, float] = {}
    for sector in sorted({item.sector for item in computed}):
        sector_returns[sector] = median(
            item.return_3m for item in computed if item.sector == sector
        )

    snapshots = [
        TickerMarketSnapshot(
            ticker=item.ticker,
            bucket=item.bucket,
            return_1m=item.return_1m,
            return_3m=item.return_3m,
            return_6m=item.return_6m,
            market_return_1m=market_return_1m,
            market_return_3m=market_return_3m,
            market_return_6m=market_return_6m,
            sector_return_3m=sector_returns[item.sector],
            volume_ratio_20d=item.volume_ratio_20d,
            pct_from_52w_high=item.pct_from_52w_high,
        )
        for item in computed
    ]
    snapshots.sort(key=lambda item: (item.bucket, item.ticker))
    return tuple(snapshots)
