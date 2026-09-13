from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .market_history import build_market_snapshots
from .market_trigger import MarketTriggerPolicy, rank_market_buckets
from .market_trigger_artifacts import load_market_history_jsonl, write_market_trigger_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay market triggers from normalized history with a frozen as-of"
    )
    parser.add_argument("--history-jsonl", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    archive = load_market_history_jsonl(args.history_jsonl)
    if args.as_of > archive.as_of:
        raise SystemExit("replay as-of cannot be later than the archive as-of")
    if archive.universe.as_of > args.as_of:
        raise SystemExit("universe snapshot is later than replay as-of")

    snapshots = build_market_snapshots(
        archive.histories,
        market_bars=archive.benchmark_bars,
        as_of=args.as_of,
    )
    policy = MarketTriggerPolicy()
    write_market_trigger_artifact(
        args.output,
        as_of=args.as_of,
        benchmark_ticker=archive.benchmark_ticker,
        source=f"replay:{archive.source}",
        triggers=rank_market_buckets(snapshots, policy=policy),
        policy=policy,
        diagnostics=archive.diagnostics,
        universe=archive.universe,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
