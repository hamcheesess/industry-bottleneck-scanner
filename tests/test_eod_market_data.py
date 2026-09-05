import json
from datetime import date

import pytest

from industry_bottleneck_scanner.eod_market_data import (
    MarketDataError,
    MarketUniverseEntry,
    MassiveGroupedDailyClient,
    collect_grouped_market_history,
)


def payload(day: date, prices: dict[str, float]) -> bytes:
    return json.dumps(
        {
            "status": "OK",
            "results": [
                {"T": ticker, "c": close, "v": 1000.0}
                for ticker, close in prices.items()
            ],
        }
    ).encode()


def test_massive_adapter_requests_adjusted_grouped_data_and_reuses_cache(tmp_path) -> None:
    requested = []

    def transport(url: str) -> bytes:
        requested.append(url)
        return payload(date(2026, 8, 21), {"AAA": 12.5})

    client = MassiveGroupedDailyClient(
        api_key="secret",
        cache_dir=tmp_path,
        transport=transport,
    )
    first = client.fetch_day(date(2026, 8, 21))
    second = client.fetch_day(date(2026, 8, 21))

    assert first == second
    assert first["AAA"].adjusted_close == 12.5
    assert "adjusted=true" in requested[0]
    assert len(requested) == 1
    assert client.provider_dates == 1
    assert client.cache_dates == 1


def test_grouped_collection_is_bottom_up_and_reports_missing_tickers(tmp_path) -> None:
    def transport(url: str) -> bytes:
        day = date.fromisoformat(url.split("/stocks/")[1].split("?")[0])
        return payload(day, {"AAA": 10.0, "IWB": 100.0})

    client = MassiveGroupedDailyClient(
        api_key="secret",
        cache_dir=tmp_path,
        transport=transport,
    )
    result = collect_grouped_market_history(
        (
            MarketUniverseEntry("AAA", "Industrials", "Electrical Equipment"),
            MarketUniverseEntry("MISSING", "Industrials", "Electrical Equipment"),
        ),
        benchmark_ticker="IWB",
        start=date(2026, 8, 21),
        as_of=date(2026, 8, 24),
        client=client,
    )

    assert result.histories == ()
    assert [bar.trading_date for bar in result.benchmark_bars] == [
        date(2026, 8, 21),
        date(2026, 8, 24),
    ]
    assert result.diagnostics.requested_dates == 2
    assert result.diagnostics.missing_tickers == ("MISSING",)
    assert result.diagnostics.insufficient_history_tickers == ("AAA",)


def test_provider_error_is_not_cached(tmp_path) -> None:
    client = MassiveGroupedDailyClient(
        api_key="secret",
        cache_dir=tmp_path,
        transport=lambda _: json.dumps({"status": "ERROR", "error": "quota"}).encode(),
    )

    with pytest.raises(MarketDataError, match="quota"):
        client.fetch_day(date(2026, 8, 21))

    assert not tmp_path.exists() or not list(tmp_path.iterdir())
