from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from pathlib import Path

from .eod_market_data import MassiveGroupedDailyClient, collect_grouped_market_history
from .market_history import build_market_snapshots
from .market_trigger import MarketTriggerPolicy, rank_market_buckets
from .market_trigger_artifacts import write_market_history_jsonl, write_market_trigger_artifact
from .market_universe import load_market_universe_csv
from .universe import CANONICAL_UNIVERSE_ID


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate bottom-up broad-US market triggers")
    parser.add_argument("--universe-csv", type=Path, required=True)
    parser.add_argument("--universe-as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--universe-source", required=True)
    parser.add_argument("--universe-id", default=CANONICAL_UNIVERSE_ID)
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
    universe = load_market_universe_csv(
        args.universe_csv.read_text(encoding="utf-8"),
        as_of=args.universe_as_of,
        source=args.universe_source,
        universe_id=args.universe_id,
    )
    if universe.as_of > args.as_of:
        raise SystemExit("universe-as-of cannot be later than market as-of")
    client = MassiveGroupedDailyClient(
        api_key=api_key,
        cache_dir=args.cache_dir,
        request_interval_seconds=args.request_interval_seconds,
    )
    collected = collect_grouped_market_history(
        universe.entries,
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
    write_market_history_jsonl(
        dated / "market_history.jsonl",
        collected.histories,
        as_of=args.as_of,
        source="massive_grouped_daily_adjusted",
        benchmark_ticker=args.benchmark,
        benchmark_bars=collected.benchmark_bars,
        diagnostics=collected.diagnostics,
        universe=universe,
    )
    write_market_trigger_artifact(
        dated / "industry_market_triggers.json",
        as_of=args.as_of,
        benchmark_ticker=args.benchmark,
        source="massive_grouped_daily_adjusted",
        triggers=triggers,
        policy=policy,
        diagnostics=collected.diagnostics,
        universe=universe,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
