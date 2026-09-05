import json
from datetime import date, timedelta

from industry_bottleneck_scanner.eod_market_data import CollectionDiagnostics
from industry_bottleneck_scanner.market_history import DailyBar, TickerMarketHistory
from industry_bottleneck_scanner.market_trigger import IndustryMarketTrigger, MarketTriggerPolicy
from industry_bottleneck_scanner.market_trigger_artifacts import (
    load_market_history_jsonl,
    write_market_history_jsonl,
    write_market_trigger_artifact,
)
from industry_bottleneck_scanner.market_universe import (
    MarketUniverseEntry,
    MarketUniverseSnapshot,
)


def universe() -> MarketUniverseSnapshot:
    return MarketUniverseSnapshot(
        universe_id="russell_3000",
        as_of=date(2026, 8, 1),
        source="test-membership",
        active_member_count=2,
        entries=(
            MarketUniverseEntry(
                "AAA",
                "Industrials",
                "Electrical Equipment",
                security_id="security-aaa",
                issuer_id="issuer-aaa",
                company_name="Alpha",
            ),
        ),
        unclassified_tickers=("BBB",),
    )


def test_trigger_artifact_has_as_of_provenance_policy_and_coverage(tmp_path) -> None:
    trigger = IndustryMarketTrigger(
        bucket="Electrical Equipment",
        company_count=4,
        market_outperform_breadth=0.75,
        sector_outperform_breadth=0.5,
        near_high_breadth=0.5,
        abnormal_volume_breadth=0.25,
        median_market_relative_3m=0.1,
        median_sector_relative_3m=0.05,
        score=65.0,
        triggered=True,
        reasons=(),
    )
    path = tmp_path / "trigger.json"
    write_market_trigger_artifact(
        path,
        as_of=date(2026, 8, 21),
        benchmark_ticker="IWB",
        source="massive_grouped_daily_adjusted",
        triggers=(trigger,),
        policy=MarketTriggerPolicy(),
        diagnostics=CollectionDiagnostics(4, 4, (), (), 280, 1, 279),
        universe=universe(),
    )

    payload = json.loads(path.read_text())
    assert payload["schema_version"] == "industry-market-trigger-v1"
    assert payload["as_of"] == "2026-08-21"
    assert payload["aggregation"] == "company_membership_bottom_up"
    assert payload["coverage"]["cache_dates"] == 279
    assert payload["universe"]["classification_coverage_ratio"] == 0.5
    assert payload["triggers"][0]["bucket"] == "Electrical Equipment"


def test_normalized_history_archive_round_trips_benchmark_and_universe(tmp_path) -> None:
    start = date(2026, 1, 1)
    bars = tuple(
        DailyBar(start + timedelta(days=index), 100.0 + index, 1000.0)
        for index in range(130)
    )
    histories = (
        TickerMarketHistory("AAA", "Industrials", "Electrical Equipment", bars),
    )
    diagnostics = CollectionDiagnostics(1, 1, (), (), 130, 10, 120)
    path = tmp_path / "history.jsonl"

    count = write_market_history_jsonl(
        path,
        histories,
        as_of=bars[-1].trading_date,
        source="massive_grouped_daily_adjusted",
        benchmark_ticker="IWB",
        benchmark_bars=bars,
        diagnostics=diagnostics,
        universe=universe(),
    )
    archive = load_market_history_jsonl(path)

    assert count == 260
    assert archive.benchmark_ticker == "IWB"
    assert archive.benchmark_bars == bars
    assert archive.histories == histories
    assert archive.universe.entries[0].security_id == "security-aaa"
    assert archive.diagnostics == diagnostics
