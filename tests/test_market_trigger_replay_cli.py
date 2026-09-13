import json
from datetime import date, timedelta

from industry_bottleneck_scanner.eod_market_data import CollectionDiagnostics
from industry_bottleneck_scanner.market_history import DailyBar, TickerMarketHistory
from industry_bottleneck_scanner.market_trigger_artifacts import write_market_history_jsonl
from industry_bottleneck_scanner.market_trigger_replay_cli import main
from industry_bottleneck_scanner.market_universe import (
    MarketUniverseEntry,
    MarketUniverseSnapshot,
)


def test_replay_freezes_as_of_and_excludes_later_price_jump(tmp_path) -> None:
    start = date(2025, 1, 1)
    base = tuple(
        DailyBar(start + timedelta(days=index), 100.0 + index, 1000.0)
        for index in range(130)
    )
    replay_as_of = base[-1].trading_date
    future = DailyBar(replay_as_of + timedelta(days=1), 10000.0, 100000.0)
    tickers = ("AAA", "BBB", "CCC", "DDD")
    histories = tuple(
        TickerMarketHistory(
            ticker,
            "Industrials",
            "Electrical Equipment",
            base + (future,),
        )
        for ticker in tickers
    )
    universe = MarketUniverseSnapshot(
        universe_id="broad-us-test",
        as_of=start,
        source="frozen-test-membership",
        active_member_count=4,
        entries=tuple(
            MarketUniverseEntry(ticker, "Industrials", "Electrical Equipment")
            for ticker in tickers
        ),
        unclassified_tickers=(),
    )
    archive_path = tmp_path / "history.jsonl"
    output = tmp_path / "replay.json"
    write_market_history_jsonl(
        archive_path,
        histories,
        as_of=future.trading_date,
        source="fixture",
        benchmark_ticker="IWB",
        benchmark_bars=base + (future,),
        diagnostics=CollectionDiagnostics(4, 4, (), (), 131, 131, 0),
        universe=universe,
    )

    assert main(
        [
            "--history-jsonl",
            str(archive_path),
            "--as-of",
            replay_as_of.isoformat(),
            "--output",
            str(output),
        ]
    ) == 0

    payload = json.loads(output.read_text())
    assert payload["as_of"] == replay_as_of.isoformat()
    assert payload["source"] == "replay:fixture"
    assert payload["triggers"][0]["median_market_relative_3m"] == 0.0
