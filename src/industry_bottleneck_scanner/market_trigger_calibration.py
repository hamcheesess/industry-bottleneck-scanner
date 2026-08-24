from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from .market_history import MIN_REQUIRED_TRADING_DAYS, TickerMarketHistory, build_market_snapshots
from .market_trigger import MarketTriggerPolicy, rank_market_buckets
from .market_trigger_artifacts import MarketHistoryArchive, write_market_trigger_artifact

CALIBRATION_SCHEMA_VERSION = "market-trigger-calibration-v1"


@dataclass(frozen=True)
class DatedCalibrationResult:
    as_of: date
    benchmark_session_count: int
    eligible_ticker_count: int
    insufficient_history_tickers: tuple[str, ...]
    bucket_count: int
    triggered_bucket_count: int
    artifact_path: str
    artifact_sha256: str


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def month_end_replay_dates(
    archive: MarketHistoryArchive,
    *,
    start_as_of: date,
    end_as_of: date,
) -> tuple[date, ...]:
    if start_as_of < archive.universe.as_of:
        raise ValueError("calibration start cannot precede universe as_of")
    if end_as_of > archive.as_of:
        raise ValueError("calibration end cannot exceed archive as_of")
    if start_as_of > end_as_of:
        raise ValueError("calibration start cannot exceed end")

    sessions = sorted(
        {
            bar.trading_date
            for bar in archive.benchmark_bars
            if start_as_of <= bar.trading_date <= end_as_of
        }
    )
    if not sessions:
        raise ValueError("no benchmark sessions exist in the calibration window")
    by_month: dict[tuple[int, int], date] = {}
    for session in sessions:
        by_month[(session.year, session.month)] = session
    selected = set(by_month.values())
    selected.add(sessions[0])
    selected.add(sessions[-1])
    return tuple(sorted(selected))


def _eligible_histories(
    histories: tuple[TickerMarketHistory, ...],
    *,
    as_of: date,
) -> tuple[tuple[TickerMarketHistory, ...], tuple[str, ...]]:
    eligible: list[TickerMarketHistory] = []
    insufficient: list[str] = []
    for history in histories:
        session_count = len({bar.trading_date for bar in history.bars if bar.trading_date <= as_of})
        if session_count >= MIN_REQUIRED_TRADING_DAYS:
            eligible.append(history)
        else:
            insufficient.append(history.ticker)
    return tuple(eligible), tuple(sorted(insufficient))


def _validate_archive_bounds(archive: MarketHistoryArchive) -> None:
    if archive.universe.as_of > archive.as_of:
        raise ValueError("universe as_of cannot exceed archive as_of")
    future_benchmark = [
        bar.trading_date for bar in archive.benchmark_bars if bar.trading_date > archive.as_of
    ]
    future_constituents = [
        f"{history.ticker}:{bar.trading_date.isoformat()}"
        for history in archive.histories
        for bar in history.bars
        if bar.trading_date > archive.as_of
    ]
    if future_benchmark or future_constituents:
        raise ValueError("normalized archive contains bars after archive as_of")


def run_market_trigger_calibration(
    archive: MarketHistoryArchive,
    *,
    history_path: Path,
    output_dir: Path,
    start_as_of: date,
    end_as_of: date,
    policy: MarketTriggerPolicy = MarketTriggerPolicy(),
) -> tuple[Path, tuple[DatedCalibrationResult, ...]]:
    _validate_archive_bounds(archive)
    dates = month_end_replay_dates(
        archive,
        start_as_of=start_as_of,
        end_as_of=end_as_of,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[DatedCalibrationResult] = []
    for replay_as_of in dates:
        benchmark_sessions = tuple(
            bar for bar in archive.benchmark_bars if bar.trading_date <= replay_as_of
        )
        if len(benchmark_sessions) < MIN_REQUIRED_TRADING_DAYS:
            raise ValueError(
                f"{replay_as_of}: benchmark has fewer than "
                f"{MIN_REQUIRED_TRADING_DAYS} sessions"
            )
        eligible, insufficient = _eligible_histories(
            archive.histories,
            as_of=replay_as_of,
        )
        snapshots = build_market_snapshots(
            eligible,
            market_bars=archive.benchmark_bars,
            as_of=replay_as_of,
        )
        triggers = rank_market_buckets(snapshots, policy=policy)
        artifact_path = (
            output_dir
            / f"as_of={replay_as_of.isoformat()}"
            / "industry_market_triggers.json"
        )
        write_market_trigger_artifact(
            artifact_path,
            as_of=replay_as_of,
            benchmark_ticker=archive.benchmark_ticker,
            source=f"replay:{archive.source}",
            triggers=triggers,
            policy=policy,
            diagnostics=archive.diagnostics,
            universe=archive.universe,
        )
        results.append(
            DatedCalibrationResult(
                as_of=replay_as_of,
                benchmark_session_count=len(benchmark_sessions),
                eligible_ticker_count=len(eligible),
                insufficient_history_tickers=insufficient,
                bucket_count=len(triggers),
                triggered_bucket_count=sum(item.triggered for item in triggers),
                artifact_path=str(artifact_path.relative_to(output_dir)),
                artifact_sha256=file_sha256(artifact_path),
            )
        )

    manifest_path = output_dir / "calibration_manifest.json"
    payload = {
        "schema_version": CALIBRATION_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_history": str(history_path),
        "source_history_sha256": file_sha256(history_path),
        "provider_calls": 0,
        "archive_as_of": archive.as_of.isoformat(),
        "universe": {
            "universe_id": archive.universe.universe_id,
            "as_of": archive.universe.as_of.isoformat(),
            "source": archive.universe.source,
            "active_member_count": archive.universe.active_member_count,
            "classified_member_count": len(archive.universe.entries),
            "unclassified_member_count": len(archive.universe.unclassified_tickers),
        },
        "calibration_window": {
            "start_as_of": start_as_of.isoformat(),
            "end_as_of": end_as_of.isoformat(),
            "cadence": "last_available_benchmark_session_per_month",
        },
        "policy": asdict(policy),
        "policy_status": "frozen_observation_only_no_threshold_tuning",
        "dates": [
            {
                **asdict(item),
                "as_of": item.as_of.isoformat(),
                "insufficient_history_ticker_count": len(
                    item.insufficient_history_tickers
                ),
            }
            for item in results
        ],
    }
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, manifest_path)
    return manifest_path, tuple(results)
