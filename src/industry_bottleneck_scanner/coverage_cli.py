from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from .alpha_vantage import AlphaVantageTranscriptSource
from .transcript_coverage import evaluate_coverage

DEFAULT_SAMPLE = (
    "AAPL",
    "MSFT",
    "ETN",
    "POWL",
    "NVT",
    "CAT",
    "DE",
    "APH",
    "VRT",
    "HUBB",
    "WCC",
    "ATI",
    "CRS",
    "MOD",
    "AEIS",
    "PLAB",
    "ONTO",
    "CLS",
    "COHR",
    "FN",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a request-capped earnings-call transcript coverage probe."
    )
    parser.add_argument("--quarter", required=True, help="Fiscal quarter in YYYYQ# format")
    parser.add_argument(
        "--limit",
        type=int,
        choices=(5, 20, 50),
        default=5,
        help="Maximum number of provider requests. Start with 5.",
    )
    parser.add_argument(
        "--tickers",
        nargs="*",
        help="Optional ticker sample. Defaults to a mixed large/mid/smaller-cap sample.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("coverage-results.json"),
        help="Path for a JSON summary. API keys and raw transcript text are never written.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("ALPHA_VANTAGE_API_KEY environment variable is required")

    tickers = tuple(args.tickers or DEFAULT_SAMPLE)
    if args.limit > len(tickers):
        raise SystemExit(
            f"requested limit {args.limit} exceeds sample size {len(tickers)}; "
            "provide more --tickers or choose a smaller limit"
        )

    source = AlphaVantageTranscriptSource(api_key=api_key)
    summary = evaluate_coverage(
        source,
        tickers=tickers,
        quarter=args.quarter,
        max_requests=args.limit,
    )

    payload = {
        "provider": source.provider_name,
        "quarter": args.quarter.upper(),
        "requested": summary.requested,
        "available": summary.available,
        "missing": summary.missing,
        "errors": summary.errors,
        "availability_rate": summary.availability_rate,
        "results": [asdict(result) for result in summary.results],
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        f"provider={source.provider_name} quarter={args.quarter.upper()} "
        f"requested={summary.requested} available={summary.available} "
        f"missing={summary.missing} errors={summary.errors} "
        f"availability_rate={summary.availability_rate:.1%}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
