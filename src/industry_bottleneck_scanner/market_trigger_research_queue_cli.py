from __future__ import annotations

import argparse
from pathlib import Path

from .market_trigger_research_queue import build_persistent_research_queue


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build bounded SEC issuer batches from persistent market-trigger buckets"
    )
    parser.add_argument("--quality-review", type=Path, required=True)
    parser.add_argument("--universe-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_persistent_research_queue(
        args.quality_review,
        args.universe_csv,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
    )
    print(
        f"status=ready provider_calls=0 buckets={payload['persistent_bucket_count']} "
        f"issuers={payload['selected_issuer_count']} batches={len(payload['batches'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
