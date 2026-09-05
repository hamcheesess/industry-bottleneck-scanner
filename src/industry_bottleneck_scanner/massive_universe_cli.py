from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .massive_universe import (
    MassiveReferenceClient,
    build_massive_universe,
    write_massive_universe_artifacts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the canonical broad-US common-stock universe from Massive reference data"
    )
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--api-key-env", default="MASSIVE_API_KEY")
    parser.add_argument("--request-interval-seconds", type=float, default=13.0)
    parser.add_argument("--max-overview-requests", type=int, default=1200)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise SystemExit(f"missing API key environment variable: {args.api_key_env}")
    client = MassiveReferenceClient(
        api_key=api_key,
        cache_dir=args.cache_dir,
        request_interval_seconds=args.request_interval_seconds,
    )
    build = build_massive_universe(
        client,
        as_of=args.as_of,
        max_overview_requests=args.max_overview_requests,
    )
    write_massive_universe_artifacts(
        csv_path=args.output_csv,
        manifest_path=args.manifest,
        build=build,
        as_of=args.as_of,
        request_interval_seconds=args.request_interval_seconds,
    )
    print(json.dumps(asdict(build.diagnostics), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
