from datetime import date, timedelta

import pytest

from industry_bottleneck_scanner.market_history import (
    DailyBar,
    TickerMarketHistory,
    build_market_snapshots,
)


def bars(*, growth: float, recent_volume: float = 1.0, count: int = 260):
    start = date(2025, 1, 1)
    result = []
    price = 100.0
    for index in range(count):
        price *= 1.0 + growth
        volume = 100.0 * (recent_volume if index >= count - 20 else 1.0)
        result.append(
            DailyBar(
                trading_date=start + timedelta(days=index),
                adjusted_close=price,
                volume=volume,
            )
        )
    return tuple(result)


def test_build_market_snapshots_uses_bottom_up_sector_median_and_adjusted_history() -> None:
    market = bars(growth=0.001)
    histories = (
        TickerMarketHistory(
            ticker="AAA",
            sector="Technology",
            bucket="AI Infrastructure",
            bars=bars(growth=0.002, recent_volume=2.0),
        ),
        TickerMarketHistory(
            ticker="BBB",
            sector="Technology",
            bucket="AI Infrastructure",
            bars=bars(growth=0.0005),
        ),
    )

    snapshots = build_market_snapshots(
        histories,
        market_bars=market,
        as_of=market[-1].trading_date,
    )
    by_ticker = {item.ticker: item for item in snapshots}

    assert by_ticker["AAA"].market_relative_3m > 0
    assert by_ticker["AAA"].sector_relative_3m > 0
    assert by_ticker["BBB"].sector_relative_3m < 0
    assert by_ticker["AAA"].volume_ratio_20d > 1.9
    assert by_ticker["AAA"].pct_from_52w_high == 0


def test_as_of_excludes_future_price_jump() -> None:
    base = list(bars(growth=0.001, count=200))
    as_of = base[-1].trading_date
    future = DailyBar(
        trading_date=as_of + timedelta(days=1),
        adjusted_close=base[-1].adjusted_close * 10,
        volume=10000,
    )
    history_with_future = TickerMarketHistory(
        ticker="AAA",
        sector="Technology",
        bucket="AI Infrastructure",
        bars=tuple(base + [future]),
    )
    market = tuple(base)

    snapshot = build_market_snapshots(
        (history_with_future,),
        market_bars=market,
        as_of=as_of,
    )[0]
    control = build_market_snapshots(
        (
            TickerMarketHistory(
                ticker="AAA",
                sector="Technology",
                bucket="AI Infrastructure",
                bars=tuple(base),
            ),
        ),
        market_bars=market,
        as_of=as_of,
    )[0]

    assert snapshot.return_3m == control.return_3m
    assert snapshot.volume_ratio_20d == control.volume_ratio_20d


def test_insufficient_history_is_rejected() -> None:
    short = bars(growth=0.001, count=100)
    with pytest.raises(ValueError, match="127"):
        build_market_snapshots(
            (
                TickerMarketHistory(
                    ticker="AAA",
                    sector="Technology",
                    bucket="AI Infrastructure",
                    bars=short,
                ),
            ),
            market_bars=bars(growth=0.001),
            as_of=bars(growth=0.001)[-1].trading_date,
        )
