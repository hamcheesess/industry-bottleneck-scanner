from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable


@dataclass(frozen=True)
class TickerMarketSnapshot:
    ticker: str
    bucket: str
    return_1m: float
    return_3m: float
    return_6m: float
    market_return_1m: float
    market_return_3m: float
    market_return_6m: float
    sector_return_3m: float
    volume_ratio_20d: float
    pct_from_52w_high: float

    @property
    def market_relative_3m(self) -> float:
        return self.return_3m - self.market_return_3m

    @property
    def sector_relative_3m(self) -> float:
        return self.return_3m - self.sector_return_3m


@dataclass(frozen=True)
class MarketTriggerPolicy:
    min_companies: int = 4
    market_outperform_breadth_min: float = 0.60
    sector_outperform_breadth_min: float = 0.50
    near_high_breadth_min: float = 0.40
    abnormal_volume_breadth_min: float = 0.35
    near_high_threshold: float = -0.10
    abnormal_volume_ratio: float = 1.25

    def __post_init__(self) -> None:
        if self.min_companies < 1:
            raise ValueError("min_companies must be at least 1")
        for name in (
            "market_outperform_breadth_min",
            "sector_outperform_breadth_min",
            "near_high_breadth_min",
            "abnormal_volume_breadth_min",
        ):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.abnormal_volume_ratio <= 0:
            raise ValueError("abnormal_volume_ratio must be positive")


@dataclass(frozen=True)
class IndustryMarketTrigger:
    bucket: str
    company_count: int
    market_outperform_breadth: float
    sector_outperform_breadth: float
    near_high_breadth: float
    abnormal_volume_breadth: float
    median_market_relative_3m: float
    median_sector_relative_3m: float
    score: float
    triggered: bool
    reasons: tuple[str, ...]


def _share(values: Iterable[bool]) -> float:
    items = tuple(values)
    if not items:
        return 0.0
    return sum(items) / len(items)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _market_trigger_score(
    *,
    market_breadth: float,
    sector_breadth: float,
    near_high_breadth: float,
    volume_breadth: float,
) -> float:
    score = (
        0.40 * _clamp01(market_breadth)
        + 0.25 * _clamp01(sector_breadth)
        + 0.20 * _clamp01(near_high_breadth)
        + 0.15 * _clamp01(volume_breadth)
    )
    return round(score * 100.0, 2)


def summarize_market_bucket(
    snapshots: Iterable[TickerMarketSnapshot],
    *,
    policy: MarketTriggerPolicy = MarketTriggerPolicy(),
) -> IndustryMarketTrigger:
    items = tuple(snapshots)
    if not items:
        raise ValueError("at least one market snapshot is required")
    buckets = {item.bucket for item in items}
    if len(buckets) != 1:
        raise ValueError("all snapshots must belong to the same bucket")

    market_breadth = _share(item.market_relative_3m > 0 for item in items)
    sector_breadth = _share(item.sector_relative_3m > 0 for item in items)
    near_high_breadth = _share(item.pct_from_52w_high >= policy.near_high_threshold for item in items)
    volume_breadth = _share(item.volume_ratio_20d >= policy.abnormal_volume_ratio for item in items)

    reasons: list[str] = []
    if len(items) < policy.min_companies:
        reasons.append("insufficient_company_breadth")
    if market_breadth < policy.market_outperform_breadth_min:
        reasons.append("weak_market_relative_breadth")
    if sector_breadth < policy.sector_outperform_breadth_min:
        reasons.append("weak_sector_relative_breadth")
    if (
        near_high_breadth < policy.near_high_breadth_min
        and volume_breadth < policy.abnormal_volume_breadth_min
    ):
        reasons.append("weak_attention_confirmation")

    triggered = not reasons
    return IndustryMarketTrigger(
        bucket=items[0].bucket,
        company_count=len(items),
        market_outperform_breadth=round(market_breadth, 4),
        sector_outperform_breadth=round(sector_breadth, 4),
        near_high_breadth=round(near_high_breadth, 4),
        abnormal_volume_breadth=round(volume_breadth, 4),
        median_market_relative_3m=round(median(item.market_relative_3m for item in items), 6),
        median_sector_relative_3m=round(median(item.sector_relative_3m for item in items), 6),
        score=_market_trigger_score(
            market_breadth=market_breadth,
            sector_breadth=sector_breadth,
            near_high_breadth=near_high_breadth,
            volume_breadth=volume_breadth,
        ),
        triggered=triggered,
        reasons=tuple(reasons),
    )


def rank_market_buckets(
    snapshots: Iterable[TickerMarketSnapshot],
    *,
    policy: MarketTriggerPolicy = MarketTriggerPolicy(),
) -> tuple[IndustryMarketTrigger, ...]:
    grouped: dict[str, list[TickerMarketSnapshot]] = {}
    for item in snapshots:
        grouped.setdefault(item.bucket, []).append(item)

    results = [summarize_market_bucket(items, policy=policy) for items in grouped.values()]
    results.sort(
        key=lambda item: (
            item.triggered,
            item.score,
            item.market_outperform_breadth,
            item.company_count,
            item.bucket,
        ),
        reverse=True,
    )
    return tuple(results)
