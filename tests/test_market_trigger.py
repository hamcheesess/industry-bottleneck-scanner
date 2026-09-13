import pytest

from industry_bottleneck_scanner.market_trigger import (
    MarketTriggerPolicy,
    TickerMarketSnapshot,
    rank_market_buckets,
    summarize_market_bucket,
)


def snap(
    ticker: str,
    bucket: str,
    *,
    return_3m: float,
    market_3m: float = 0.05,
    sector_3m: float = 0.07,
    volume_ratio: float = 1.4,
    pct_from_high: float = -0.05,
) -> TickerMarketSnapshot:
    return TickerMarketSnapshot(
        ticker=ticker,
        bucket=bucket,
        return_1m=return_3m / 3,
        return_3m=return_3m,
        return_6m=return_3m * 1.5,
        market_return_1m=market_3m / 3,
        market_return_3m=market_3m,
        market_return_6m=market_3m * 1.5,
        sector_return_3m=sector_3m,
        volume_ratio_20d=volume_ratio,
        pct_from_52w_high=pct_from_high,
    )


def test_broad_industry_outperformance_triggers() -> None:
    items = (
        snap("A", "Electrical Equipment", return_3m=0.30),
        snap("B", "Electrical Equipment", return_3m=0.26),
        snap("C", "Electrical Equipment", return_3m=0.22),
        snap("D", "Electrical Equipment", return_3m=0.18),
        snap("E", "Electrical Equipment", return_3m=0.02, volume_ratio=0.9, pct_from_high=-0.20),
    )

    result = summarize_market_bucket(items)
    assert result.triggered is True
    assert result.market_outperform_breadth == 0.8
    assert result.sector_outperform_breadth == 0.8
    assert result.score > 60


def test_single_stock_spike_does_not_trigger_quiet_bucket() -> None:
    items = (
        snap("A", "Quiet Industry", return_3m=0.60),
        snap("B", "Quiet Industry", return_3m=0.01, volume_ratio=0.8, pct_from_high=-0.30),
        snap("C", "Quiet Industry", return_3m=0.00, volume_ratio=0.8, pct_from_high=-0.30),
        snap("D", "Quiet Industry", return_3m=-0.02, volume_ratio=0.8, pct_from_high=-0.30),
    )

    result = summarize_market_bucket(items)
    assert result.triggered is False
    assert "weak_market_relative_breadth" in result.reasons
    assert "weak_sector_relative_breadth" in result.reasons


def test_attention_confirmation_can_come_from_highs_or_volume() -> None:
    policy = MarketTriggerPolicy(near_high_breadth_min=0.75, abnormal_volume_breadth_min=0.50)
    items = (
        snap("A", "Bucket", return_3m=0.20, pct_from_high=-0.20, volume_ratio=1.5),
        snap("B", "Bucket", return_3m=0.20, pct_from_high=-0.20, volume_ratio=1.5),
        snap("C", "Bucket", return_3m=0.20, pct_from_high=-0.20, volume_ratio=1.5),
        snap("D", "Bucket", return_3m=0.20, pct_from_high=-0.20, volume_ratio=0.9),
    )

    result = summarize_market_bucket(items, policy=policy)
    assert result.triggered is True
    assert result.near_high_breadth == 0.0
    assert result.abnormal_volume_breadth == 0.75


def test_rank_market_buckets_prefers_triggered_breadth() -> None:
    snapshots = (
        snap("A", "Strong", return_3m=0.30),
        snap("B", "Strong", return_3m=0.25),
        snap("C", "Strong", return_3m=0.20),
        snap("D", "Strong", return_3m=0.18),
        snap("E", "Weak", return_3m=0.50),
        snap("F", "Weak", return_3m=0.01, volume_ratio=0.8, pct_from_high=-0.30),
        snap("G", "Weak", return_3m=0.00, volume_ratio=0.8, pct_from_high=-0.30),
        snap("H", "Weak", return_3m=-0.01, volume_ratio=0.8, pct_from_high=-0.30),
    )

    ranked = rank_market_buckets(snapshots)
    assert [item.bucket for item in ranked] == ["Strong", "Weak"]
    assert ranked[0].triggered is True
    assert ranked[1].triggered is False


def test_market_trigger_policy_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError):
        MarketTriggerPolicy(min_companies=0)
    with pytest.raises(ValueError):
        MarketTriggerPolicy(market_outperform_breadth_min=1.1)
