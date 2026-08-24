from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .market_trigger_artifacts import load_market_history_jsonl
from .market_trigger_calibration import run_market_trigger_calibration


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate provider-free strict-as-of monthly market-trigger calibration artifacts"
    )
    parser.add_argument("--history-jsonl", type=Path, required=True)
    parser.add_argument("--start-as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--end-as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    archive = load_market_history_jsonl(args.history_jsonl)
    manifest, results = run_market_trigger_calibration(
        archive,
        history_path=args.history_jsonl,
        output_dir=args.output_dir,
        start_as_of=args.start_as_of,
        end_as_of=args.end_as_of,
    )
    print(
        f"status=full provider_calls=0 dates={len(results)} "
        f"manifest={manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
