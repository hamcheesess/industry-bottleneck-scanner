from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from .pilot_diagnostics import diagnose_pilot, load_collection_items
from .transcript_collection import TranscriptRequest
from .transcript_quality import evaluate_transcript_quality
from .transcript_store import FileTranscriptStore


def _load_requests(path: Path) -> tuple[TranscriptRequest, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if {"ticker", "quarter"} - set(reader.fieldnames or ()):
            raise SystemExit("request CSV must contain ticker,quarter columns")
        return tuple(
            TranscriptRequest(
                ticker=(row.get("ticker") or ""),
                quarter=(row.get("quarter") or ""),
            )
            for row in reader
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose whether a transcript pilot is ready for a matched experiment.")
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--min-paired-companies", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("var/experiments/pilot-diagnostics.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    provider, items = load_collection_items(args.collection)
    requests = _load_requests(args.requests)
    store = FileTranscriptStore(args.transcript_root)
    diagnostics = diagnose_pilot(
        provider=provider,
        requests=requests,
        items=items,
        transcript_store=store,
        min_paired_companies=args.min_paired_companies,
    )

    cached_transcripts = tuple(
        transcript
        for request in requests
        if (
            transcript := store.load(
                provider=provider,
                ticker=request.ticker,
                quarter=request.quarter,
            )
        )
        is not None
    )
    quality = evaluate_transcript_quality(cached_transcripts)

    payload = asdict(diagnostics)
    payload["resolved_rate"] = diagnostics.resolved_rate
    payload["availability_rate"] = diagnostics.availability_rate
    payload["transcript_quality"] = asdict(quality)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"provider={provider} pairs={diagnostics.requested_pairs} "
        f"available={diagnostics.available_pairs} missing={diagnostics.missing_pairs} "
        f"unresolved={len(diagnostics.unresolved_pairs)} paired_companies={diagnostics.fully_available_companies} "
        f"qa_detection_rate={quality.qa_detection_rate:.1%} "
        f"speaker_label_rate={quality.speaker_label_rate:.1%} "
        f"ready={str(diagnostics.ready_for_matched_experiment).lower()}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
