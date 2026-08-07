from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .company_metadata import load_company_period_metadata_csv
from .experiment import run_comparable_cached_experiment
from .review_queue import FileReviewQueue
from .transcript_store import FileTranscriptStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan cached earnings-call transcripts and compare matched current vs baseline windows."
    )
    parser.add_argument("--current", type=Path, required=True, help="Current-window metadata CSV")
    parser.add_argument("--baseline", type=Path, required=True, help="Baseline-window metadata CSV")
    parser.add_argument("--provider", default="alpha_vantage")
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--review-queue", type=Path, default=Path("var/review/semantic.json"))
    parser.add_argument("--max-companies", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("var/experiments/phase1-batch.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.max_companies < 1:
        raise SystemExit("--max-companies must be at least 1")

    current_records = load_company_period_metadata_csv(args.current.read_text(encoding="utf-8"))
    baseline_records = load_company_period_metadata_csv(args.baseline.read_text(encoding="utf-8"))
    store = FileTranscriptStore(args.transcript_root)
    review_queue = FileReviewQueue(args.review_queue)

    experiment = run_comparable_cached_experiment(
        current_records,
        baseline_records,
        provider=args.provider,
        transcript_store=store,
        review_queue=review_queue,
        max_companies=args.max_companies,
    )
    current = experiment.current
    baseline = experiment.baseline
    acceleration = experiment.acceleration

    payload = {
        "provider": args.provider,
        "cohort": asdict(experiment.diagnostics),
        "current": {
            "companies": [asdict(item) for item in current.companies],
            "signal_count": len(current.signals),
            "missing_transcripts": current.missing_transcripts,
            "review_candidates": current.review_candidates,
            "clusters": [asdict(item) for item in current.clusters],
        },
        "baseline": {
            "companies": [asdict(item) for item in baseline.companies],
            "signal_count": len(baseline.signals),
            "missing_transcripts": baseline.missing_transcripts,
            "review_candidates": baseline.review_candidates,
            "clusters": [asdict(item) for item in baseline.clusters],
        },
        "acceleration": [asdict(item) for item in acceleration],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    triggered = sum(item.triggered for item in acceleration)
    confirmed = sum(item.confirmed for item in acceleration)
    print(
        f"eligible_companies={experiment.diagnostics.eligible_companies} "
        f"current_signals={len(current.signals)} baseline_signals={len(baseline.signals)} "
        f"clusters={len(acceleration)} triggered={triggered} confirmed={confirmed}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
