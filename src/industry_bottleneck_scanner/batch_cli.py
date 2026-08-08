from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .artifacts import write_atomic_signals_jsonl
from .company_metadata import load_company_period_metadata_csv
from .diagnostics import summarize_signal_diagnostics
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
    parser.add_argument(
        "--aggregation-level",
        choices=("sector", "industry", "subindustry"),
        default="industry",
        help="Classification level used for cross-company breadth; Phase 1 defaults to industry",
    )
    parser.add_argument("--output", type=Path, default=Path("var/experiments/phase1-batch.json"))
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("var/experiments/artifacts"),
        help="Directory for auditable current/baseline AtomicSignal JSONL files",
    )
    return parser


def _strongest_acceleration(acceleration):
    if not acceleration:
        return None
    return max(
        acceleration,
        key=lambda item: (
            item.triggered,
            item.metric_prevalence_gain_count,
            item.company_metric_intensity_change,
            item.breadth_change,
        ),
    )


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
        aggregation_level=args.aggregation_level,
    )
    current = experiment.current
    baseline = experiment.baseline
    acceleration = experiment.acceleration
    current_diagnostics = summarize_signal_diagnostics(current.signals)
    baseline_diagnostics = summarize_signal_diagnostics(baseline.signals)

    current_signal_path = args.artifact_root / "current_signals.jsonl"
    baseline_signal_path = args.artifact_root / "baseline_signals.jsonl"
    write_atomic_signals_jsonl(current_signal_path, current.signals)
    write_atomic_signals_jsonl(baseline_signal_path, baseline.signals)

    payload = {
        "provider": args.provider,
        "aggregation_level": args.aggregation_level,
        "cohort": asdict(experiment.diagnostics),
        "artifacts": {
            "current_signals_jsonl": str(current_signal_path),
            "baseline_signals_jsonl": str(baseline_signal_path),
        },
        "current": {
            "companies": [asdict(item) for item in current.companies],
            "signal_count": len(current.signals),
            "missing_transcripts": current.missing_transcripts,
            "review_candidates": current.review_candidates,
            "clusters": [asdict(item) for item in current.clusters],
            "diagnostics": asdict(current_diagnostics),
        },
        "baseline": {
            "companies": [asdict(item) for item in baseline.companies],
            "signal_count": len(baseline.signals),
            "missing_transcripts": baseline.missing_transcripts,
            "review_candidates": baseline.review_candidates,
            "clusters": [asdict(item) for item in baseline.clusters],
            "diagnostics": asdict(baseline_diagnostics),
        },
        "acceleration": [asdict(item) for item in acceleration],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    triggered = sum(item.triggered for item in acceleration)
    confirmed = sum(item.confirmed for item in acceleration)
    strongest = _strongest_acceleration(acceleration)
    strongest_text = ""
    if strongest is not None:
        gains = ",".join(strongest.metric_prevalence_gains) or "none"
        strongest_text = (
            f" strongest_bucket={strongest.bucket!r}"
            f" breadth_delta={strongest.breadth_change:+d}"
            f" metric_prevalence_gains={strongest.metric_prevalence_gain_count}"
            f" metric_intensity_delta={strongest.company_metric_intensity_change:+.2f}"
            f" gain_metrics={gains}"
        )
    print(
        f"aggregation_level={args.aggregation_level} "
        f"eligible_companies={experiment.diagnostics.eligible_companies} "
        f"current_signals={len(current.signals)} baseline_signals={len(baseline.signals)} "
        f"clusters={len(acceleration)} triggered={triggered} confirmed={confirmed}"
        f"{strongest_text}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
