from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .artifacts import write_atomic_signals_jsonl
from .company_metadata import load_company_period_metadata_csv
from .diagnostics import summarize_signal_diagnostics
from .discovery_score import rank_accelerations
from .embedding_adapters import HashingNgramEncoder
from .experiment import run_comparable_cached_experiment
from .handoff_contract import build_handoff_record, handoff_to_dict
from .novel_language import cluster_pending_review_language
from .pipeline_fingerprint import (
    RESULT_SCHEMA_VERSION,
    compute_experiment_input_fingerprint,
    compute_pipeline_fingerprint,
)
from .review_queue import FileReviewQueue
from .semantic_retrieval import LocalSemanticRetriever
from .taxonomy_candidates import build_taxonomy_candidates
from .transcript_store import FileTranscriptStore
from .viability import assess_phase1_viability


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
            item.confirmed,
            item.triggered,
            item.watchlisted,
            item.metric_prevalence_gain_count,
            item.company_metric_intensity_change,
            item.breadth_change,
        ),
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.max_companies < 1:
        raise SystemExit("--max-companies must be at least 1")

    pipeline_fingerprint = compute_pipeline_fingerprint()
    input_fingerprint = compute_experiment_input_fingerprint(
        current_metadata=args.current,
        baseline_metadata=args.baseline,
        provider=args.provider,
        transcript_root=args.transcript_root,
    )

    current_records = load_company_period_metadata_csv(args.current.read_text(encoding="utf-8"))
    baseline_records = load_company_period_metadata_csv(args.baseline.read_text(encoding="utf-8"))
    store = FileTranscriptStore(args.transcript_root)
    review_queue = FileReviewQueue(args.review_queue)
    encoder = HashingNgramEncoder()
    semantic_retriever = LocalSemanticRetriever(encoder)

    experiment = run_comparable_cached_experiment(
        current_records,
        baseline_records,
        provider=args.provider,
        transcript_store=store,
        semantic_retriever=semantic_retriever,
        review_queue=review_queue,
        max_companies=args.max_companies,
        aggregation_level=args.aggregation_level,
    )
    current = experiment.current
    baseline = experiment.baseline
    acceleration = experiment.acceleration
    scores = rank_accelerations(acceleration)
    score_by_bucket = {item.bucket: item for item in scores}
    viability = assess_phase1_viability(
        acceleration,
        eligible_companies=experiment.diagnostics.eligible_companies,
    )

    handoff_preview = tuple(
        build_handoff_record(snapshot, current.signals)
        for snapshot in acceleration
        if snapshot.triggered or snapshot.confirmed
    )
    novel_clusters = cluster_pending_review_language(
        review_queue.load(),
        encoder=encoder,
        min_companies=3,
    )
    taxonomy_candidates = build_taxonomy_candidates(novel_clusters)

    current_diagnostics = summarize_signal_diagnostics(current.signals)
    baseline_diagnostics = summarize_signal_diagnostics(baseline.signals)

    current_signal_path = args.artifact_root / "current_signals.jsonl"
    baseline_signal_path = args.artifact_root / "baseline_signals.jsonl"
    handoff_path = args.artifact_root / "handoff_preview.json"
    taxonomy_path = args.artifact_root / "taxonomy_candidates.json"
    viability_path = args.artifact_root / "phase1_viability.json"
    write_atomic_signals_jsonl(current_signal_path, current.signals)
    write_atomic_signals_jsonl(baseline_signal_path, baseline.signals)
    _write_json(handoff_path, [handoff_to_dict(item) for item in handoff_preview])
    _write_json(taxonomy_path, [asdict(item) for item in taxonomy_candidates])
    _write_json(viability_path, asdict(viability))

    payload = {
        "result_provenance": {
            "schema_version": RESULT_SCHEMA_VERSION,
            "pipeline_fingerprint": pipeline_fingerprint,
            "input_fingerprint": input_fingerprint,
            "provider": args.provider,
            "current_metadata": str(args.current),
            "baseline_metadata": str(args.baseline),
        },
        "provider": args.provider,
        "aggregation_level": args.aggregation_level,
        "cohort": asdict(experiment.diagnostics),
        "phase1_viability": asdict(viability),
        "artifacts": {
            "current_signals_jsonl": str(current_signal_path),
            "baseline_signals_jsonl": str(baseline_signal_path),
            "handoff_preview_json": str(handoff_path),
            "taxonomy_candidates_json": str(taxonomy_path),
            "phase1_viability_json": str(viability_path),
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
        "acceleration": [
            asdict(item) | {"discovery_score": asdict(score_by_bucket[item.bucket])}
            for item in acceleration
        ],
        "novel_language_clusters": [
            asdict(cluster) | {"distinct_companies": cluster.distinct_companies}
            for cluster in novel_clusters
        ],
        "taxonomy_candidates": [asdict(item) for item in taxonomy_candidates],
        "handoff_preview": [handoff_to_dict(item) for item in handoff_preview],
    }
    _write_json(args.output, payload)

    triggered = sum(item.triggered for item in acceleration)
    confirmed = sum(item.confirmed for item in acceleration)
    watchlisted = sum(item.watchlisted for item in acceleration)
    strongest = _strongest_acceleration(acceleration)
    strongest_text = ""
    if strongest is not None:
        gains = ",".join(strongest.metric_prevalence_gains) or "none"
        reasons = ",".join(strongest.watch_reasons) or "none"
        strongest_score = score_by_bucket[strongest.bucket]
        strongest_text = (
            f" strongest_bucket={strongest.bucket!r}"
            f" stage={strongest_score.stage}"
            f" discovery_score={strongest_score.score:.2f}"
            f" breadth_delta={strongest.breadth_change:+d}"
            f" metric_prevalence_gains={strongest.metric_prevalence_gain_count}"
            f" metric_intensity_delta={strongest.company_metric_intensity_change:+.2f}"
            f" gain_metrics={gains}"
            f" watch_reasons={reasons}"
        )
    print(
        f"aggregation_level={args.aggregation_level} "
        f"eligible_companies={experiment.diagnostics.eligible_companies} "
        f"current_signals={len(current.signals)} baseline_signals={len(baseline.signals)} "
        f"clusters={len(acceleration)} watchlisted={watchlisted} "
        f"triggered={triggered} confirmed={confirmed} "
        f"taxonomy_candidates={len(taxonomy_candidates)} "
        f"next_gate={viability.decision}"
        f"{strongest_text}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
