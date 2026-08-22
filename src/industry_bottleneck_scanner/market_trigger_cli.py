from __future__ import annotations

import argparse
import csv
import os
from datetime import date, timedelta
from pathlib import Path

from .eod_market_data import (
    MarketUniverseEntry,
    MassiveGroupedDailyClient,
    collect_grouped_market_history,
)
from .market_history import build_market_snapshots
from .market_trigger import MarketTriggerPolicy, rank_market_buckets
from .market_trigger_artifacts import write_market_history_jsonl, write_market_trigger_artifact


def _entries(path: Path) -> tuple[MarketUniverseEntry, ...]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"ticker", "sector", "bucket"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"market universe CSV missing required columns: {sorted(missing)}")
        return tuple(
            MarketUniverseEntry(
                ticker=row["ticker"].strip().upper().replace(".", "-"),
                sector=row["sector"].strip(),
                bucket=row["bucket"].strip(),
            )
            for row in reader
            if row.get("active", "true").strip().casefold() not in {"0", "false", "no", "inactive"}
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate bottom-up broad-US market triggers")
    parser.add_argument("--universe-csv", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--benchmark", default="IWB")
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--api-key-env", default="MASSIVE_API_KEY")
    parser.add_argument("--request-interval-seconds", type=float, default=13.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise SystemExit(f"missing API key environment variable: {args.api_key_env}")
    start = args.start_date or args.as_of - timedelta(days=400)
    client = MassiveGroupedDailyClient(
        api_key=api_key,
        cache_dir=args.cache_dir,
        request_interval_seconds=args.request_interval_seconds,
    )
    collected = collect_grouped_market_history(
        _entries(args.universe_csv),
        benchmark_ticker=args.benchmark,
        start=start,
        as_of=args.as_of,
        client=client,
    )
    snapshots = build_market_snapshots(
        collected.histories,
        market_bars=collected.benchmark_bars,
        as_of=args.as_of,
    )
    policy = MarketTriggerPolicy()
    triggers = rank_market_buckets(snapshots, policy=policy)
    dated = args.output_dir / f"as_of={args.as_of.isoformat()}"
    write_market_history_jsonl(dated / "market_history.jsonl", collected.histories)
    write_market_trigger_artifact(
        dated / "industry_market_triggers.json",
        as_of=args.as_of,
        benchmark_ticker=args.benchmark,
        source="massive_grouped_daily_adjusted",
        triggers=triggers,
        policy=policy,
        diagnostics=collected.diagnostics,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
