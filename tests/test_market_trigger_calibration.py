from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from industry_bottleneck_scanner.eod_market_data import CollectionDiagnostics
from industry_bottleneck_scanner.market_history import DailyBar, TickerMarketHistory
from industry_bottleneck_scanner.market_trigger_artifacts import (
    load_market_history_jsonl,
    write_market_history_jsonl,
)
from industry_bottleneck_scanner.market_trigger_calibration import (
    month_end_replay_dates,
    run_market_trigger_calibration,
)
from industry_bottleneck_scanner.market_trigger_calibration_cli import main
from industry_bottleneck_scanner.market_universe import (
    MarketUniverseEntry,
    MarketUniverseSnapshot,
)


START = date(2025, 1, 1)
UNIVERSE_AS_OF = START + timedelta(days=130)
ARCHIVE_AS_OF = START + timedelta(days=190)


def bars(start: date, count: int, *, offset: float = 0.0) -> tuple[DailyBar, ...]:
    return tuple(
        DailyBar(start + timedelta(days=index), 100.0 + offset + index, 1000.0 + index)
        for index in range(count)
    )


def archive_path(tmp_path, *, add_future: bool = False):
    universe = MarketUniverseSnapshot(
        universe_id="broad_us_common_stocks_v1",
        as_of=UNIVERSE_AS_OF,
        source="dated-test-universe",
        active_member_count=3,
        entries=(
            MarketUniverseEntry("AAA", "Industrials", "Electrical Equipment"),
            MarketUniverseEntry("BBB", "Industrials", "Electrical Equipment"),
        ),
        unclassified_tickers=("CCC",),
    )
    benchmark = bars(START, 191)
    first = bars(START, 191)
    second = bars(START + timedelta(days=30), 161, offset=10.0)
    if add_future:
        first += (DailyBar(ARCHIVE_AS_OF + timedelta(days=1), 400.0, 1000.0),)
    path = tmp_path / "history.jsonl"
    write_market_history_jsonl(
        path,
        (
            TickerMarketHistory("AAA", "Industrials", "Electrical Equipment", first),
            TickerMarketHistory("BBB", "Industrials", "Electrical Equipment", second),
        ),
        as_of=ARCHIVE_AS_OF,
        source="normalized-test-history",
        benchmark_ticker="IWB",
        benchmark_bars=benchmark,
        diagnostics=CollectionDiagnostics(2, 2, (), (), 191, 0, 191),
        universe=universe,
    )
    return path


def test_month_end_dates_stay_inside_universe_and_archive_cutoffs(tmp_path) -> None:
    path = archive_path(tmp_path)
    archive = load_market_history_jsonl(path)
    dates = month_end_replay_dates(
        archive,
        start_as_of=UNIVERSE_AS_OF,
        end_as_of=ARCHIVE_AS_OF,
    )

    assert dates[0] == UNIVERSE_AS_OF
    assert dates[-1] == ARCHIVE_AS_OF
    assert all(UNIVERSE_AS_OF <= item <= ARCHIVE_AS_OF for item in dates)
    with pytest.raises(ValueError, match="universe as_of"):
        month_end_replay_dates(
            archive,
            start_as_of=UNIVERSE_AS_OF - timedelta(days=1),
            end_as_of=ARCHIVE_AS_OF,
        )


def test_calibration_writes_dated_artifacts_with_explicit_eligibility(tmp_path) -> None:
    path = archive_path(tmp_path)
    archive = load_market_history_jsonl(path)
    output = tmp_path / "calibration"
    manifest_path, results = run_market_trigger_calibration(
        archive,
        history_path=path,
        output_dir=output,
        start_as_of=UNIVERSE_AS_OF,
        end_as_of=ARCHIVE_AS_OF,
    )

    manifest = json.loads(manifest_path.read_text())
    first = json.loads((output / results[0].artifact_path).read_text())
    assert manifest["schema_version"] == "market-trigger-calibration-v1"
    assert manifest["provider_calls"] == 0
    assert manifest["universe"]["as_of"] == UNIVERSE_AS_OF.isoformat()
    assert manifest["archive_as_of"] == ARCHIVE_AS_OF.isoformat()
    assert manifest["dates"][0]["eligible_ticker_count"] == 1
    assert manifest["dates"][0]["insufficient_history_tickers"] == ["BBB"]
    assert manifest["dates"][-1]["eligible_ticker_count"] == 2
    assert first["schema_version"] == "industry-market-trigger-v1"
    assert first["as_of"] == UNIVERSE_AS_OF.isoformat()
    assert first["source"] == "replay:normalized-test-history"


def test_calibration_rejects_archive_bars_after_archive_cutoff(tmp_path) -> None:
    path = archive_path(tmp_path, add_future=True)
    archive = load_market_history_jsonl(path)
    with pytest.raises(ValueError, match="after archive as_of"):
        run_market_trigger_calibration(
            archive,
            history_path=path,
            output_dir=tmp_path / "out",
            start_as_of=UNIVERSE_AS_OF,
            end_as_of=ARCHIVE_AS_OF,
        )


def test_calibration_cli_is_provider_free(tmp_path, capsys) -> None:
    path = archive_path(tmp_path)
    output = tmp_path / "cli-output"
    assert main(
        [
            "--history-jsonl",
            str(path),
            "--start-as-of",
            UNIVERSE_AS_OF.isoformat(),
            "--end-as-of",
            ARCHIVE_AS_OF.isoformat(),
            "--output-dir",
            str(output),
        ]
    ) == 0
    assert "provider_calls=0" in capsys.readouterr().out
    assert (output / "calibration_manifest.json").exists()
