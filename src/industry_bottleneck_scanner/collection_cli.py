from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import asdict
from pathlib import Path

from .alpha_vantage import AlphaVantageTranscriptSource
from .pilot_diagnostics import diagnose_pilot
from .transcript_collection import TranscriptRequest, collect_requested_transcripts
from .transcript_quality import evaluate_transcript_quality
from .transcript_store import FileTranscriptStore


def _load_requests(path: Path) -> tuple[TranscriptRequest, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"ticker", "quarter"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise SystemExit(f"request CSV missing required columns: {sorted(missing)}")
        requests = tuple(
            TranscriptRequest(
                ticker=(row.get("ticker") or ""),
                quarter=(row.get("quarter") or ""),
            )
            for row in reader
        )
    if not requests:
        raise SystemExit("request CSV must contain at least one row")
    return requests


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect explicit ticker/fiscal-quarter transcript requests with cache and budget guards."
    )
    parser.add_argument("--requests", type=Path, required=True, help="CSV with ticker,quarter columns")
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--max-provider-requests", type=int, default=20)
    parser.add_argument("--interval-seconds", type=float, default=1.1)
    parser.add_argument("--min-paired-companies", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("var/collection/transcripts.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.max_provider_requests < 1:
        raise SystemExit("--max-provider-requests must be at least 1")
    if args.interval_seconds < 0:
        raise SystemExit("--interval-seconds must be non-negative")
    if args.min_paired_companies < 1:
        raise SystemExit("--min-paired-companies must be at least 1")

    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("ALPHA_VANTAGE_API_KEY environment variable is required")

    requests = _load_requests(args.requests)
    source = AlphaVantageTranscriptSource(api_key=api_key)
    store = FileTranscriptStore(args.transcript_root)
    summary = collect_requested_transcripts(
        source,
        store=store,
        requests=requests,
        max_provider_requests=args.max_provider_requests,
        min_interval_seconds=args.interval_seconds,
    )
    diagnostics = diagnose_pilot(
        provider=source.provider_name,
        requests=requests,
        items=summary.items,
        transcript_store=store,
        min_paired_companies=args.min_paired_companies,
    )
    cached_transcripts = tuple(
        transcript
        for request in requests
        if (
            transcript := store.load(
                provider=source.provider_name,
                ticker=request.ticker,
                quarter=request.quarter,
            )
        )
        is not None
    )
    quality = evaluate_transcript_quality(cached_transcripts)

    diagnostic_payload = asdict(diagnostics)
    diagnostic_payload["resolved_rate"] = diagnostics.resolved_rate
    diagnostic_payload["availability_rate"] = diagnostics.availability_rate
    diagnostic_payload["transcript_quality"] = asdict(quality)
    payload = {
        "provider": source.provider_name,
        "requested": summary.requested,
        "cache_hits": summary.cache_hits,
        "fetched": summary.fetched,
        "missing": summary.missing,
        "rate_limited": summary.rate_limited,
        "errors": summary.errors,
        "provider_requests": summary.provider_requests,
        "items": [asdict(item) for item in summary.items],
        "pilot_diagnostics": diagnostic_payload,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        f"provider={source.provider_name} requested={summary.requested} "
        f"cache_hits={summary.cache_hits} fetched={summary.fetched} missing={summary.missing} "
        f"rate_limited={summary.rate_limited} errors={summary.errors} "
        f"provider_requests={summary.provider_requests} "
        f"paired_companies={diagnostics.fully_available_companies} "
        f"qa_detection_rate={quality.qa_detection_rate:.1%} "
        f"speaker_label_rate={quality.speaker_label_rate:.1%} "
        f"ready={str(diagnostics.ready_for_matched_experiment).lower()}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
