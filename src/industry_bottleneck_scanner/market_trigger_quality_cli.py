from __future__ import annotations

import argparse
from pathlib import Path

from .market_trigger_quality import build_market_trigger_quality_review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review dated market-trigger stability without outcomes or provider calls"
    )
    parser.add_argument("--calibration-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_market_trigger_quality_review(
        args.calibration_dir,
        output_path=args.output,
    )
    summary = payload["summary"]
    print(
        f"status={payload['promotion_status']} provider_calls=0 "
        f"dates={summary['date_count']} "
        f"persistent={summary['latest_persistent_bucket_count']} "
        f"emerging={summary['latest_emerging_bucket_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
