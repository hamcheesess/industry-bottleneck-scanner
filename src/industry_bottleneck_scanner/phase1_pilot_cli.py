from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import asdict
from pathlib import Path

from .alpha_vantage import AlphaVantageTranscriptSource
from .artifacts import write_atomic_signals_jsonl
from .company_metadata import load_company_period_metadata_csv
from .diagnostics import summarize_signal_diagnostics
from .discovery_score import rank_accelerations
from .embedding_adapters import HashingNgramEncoder
from .experiment import run_comparable_cached_experiment
from .handoff_contract import build_handoff_record, handoff_to_dict
from .novel_language import cluster_pending_review_language
from .pilot_diagnostics import diagnose_pilot
from .review_queue import FileReviewQueue
from .semantic_retrieval import LocalSemanticRetriever
from .taxonomy_candidates import build_taxonomy_candidates
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
        description=(
            "Run the bounded Phase-1 transcript pilot end to end: collect/cache, "
            "validate provider quality, scan matched windows, aggregate, and emit artifacts."
        )
    )
    parser.add_argument(
        "--requests",
        type=Path,
        default=Path("experiments/pilot_power_infrastructure_requests.csv"),
    )
    parser.add_argument(
        "--current",
        type=Path,
        default=Path("experiments/pilot_power_infrastructure_current.csv"),
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("experiments/pilot_power_infrastructure_baseline.csv"),
    )
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--review-queue", type=Path, default=Path("var/review/pilot_semantic.json"))
    parser.add_argument("--max-provider-requests", type=int, default=10)
    parser.add_argument("--interval-seconds", type=float, default=1.1)
    parser.add_argument("--min-paired-companies", type=int, default=4)
    parser.add_argument(
        "--aggregation-level",
        choices=("sector", "industry", "subindustry"),
        default="industry",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("var/experiments/power-infrastructure-pilot.json"),
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("var/experiments/power-infrastructure-artifacts"),
    )
    return parser


def _quality_payload(store: FileTranscriptStore, provider: str, requests: tuple[TranscriptRequest, ...]) -> dict[str, object]:
    transcripts = tuple(
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
    return asdict(evaluate_transcript_quality(transcripts))


def _write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    store = FileTranscriptStore(args.transcript_root)
    source = AlphaVantageTranscriptSource(api_key=api_key)
    collection = collect_requested_transcripts(
        source,
        store=store,
        requests=requests,
        max_provider_requests=args.max_provider_requests,
        min_interval_seconds=args.interval_seconds,
    )
    pilot = diagnose_pilot(
        provider=source.provider_name,
        requests=requests,
        items=collection.items,
        transcript_store=store,
        min_paired_companies=args.min_paired_companies,
    )

    report: dict[str, object] = {
        "status": "collection_incomplete",
        "provider": source.provider_name,
        "collection": {
            "requested": collection.requested,
            "cache_hits": collection.cache_hits,
            "fetched": collection.fetched,
            "missing": collection.missing,
            "rate_limited": collection.rate_limited,
            "errors": collection.errors,
            "provider_requests": collection.provider_requests,
            "items": [asdict(item) for item in collection.items],
        },
        "pilot_diagnostics": {
            **asdict(pilot),
            "resolved_rate": pilot.resolved_rate,
            "availability_rate": pilot.availability_rate,
            "transcript_quality": _quality_payload(store, source.provider_name, requests),
        },
    }

    if not pilot.ready_for_matched_experiment:
        _write_report(args.output, report)
        quality = report["pilot_diagnostics"]["transcript_quality"]  # type: ignore[index]
        print(
            f"status=collection_incomplete provider={source.provider_name} "
            f"available_pairs={pilot.available_pairs}/{pilot.requested_pairs} "
            f"paired_companies={pilot.fully_available_companies} "
            f"unresolved={len(pilot.unresolved_pairs)} "
            f"rate_limited={collection.rate_limited} errors={collection.errors} "
            f"qa_detection_rate={quality['qa_detection_rate']:.1%} "  # type: ignore[index]
            f"speaker_label_rate={quality['speaker_label_rate']:.1%}"  # type: ignore[index]
        )
        print(f"wrote {args.output}")
        return 2

    current_records = load_company_period_metadata_csv(args.current.read_text(encoding="utf-8"))
    baseline_records = load_company_period_metadata_csv(args.baseline.read_text(encoding="utf-8"))
    review_queue = FileReviewQueue(args.review_queue)
    encoder = HashingNgramEncoder()
    semantic_retriever = LocalSemanticRetriever(encoder)
    experiment = run_comparable_cached_experiment(
        current_records,
        baseline_records,
        provider=source.provider_name,
        transcript_store=store,
        semantic_retriever=semantic_retriever,
        review_queue=review_queue,
        max_companies=len(current_records),
        aggregation_level=args.aggregation_level,
    )

    current_signal_path = args.artifact_root / "current_signals.jsonl"
    baseline_signal_path = args.artifact_root / "baseline_signals.jsonl"
    handoff_path = args.artifact_root / "handoff_preview.json"
    write_atomic_signals_jsonl(current_signal_path, experiment.current.signals)
    write_atomic_signals_jsonl(baseline_signal_path, experiment.baseline.signals)
    novel_clusters = cluster_pending_review_language(
        review_queue.load(),
        encoder=encoder,
        min_companies=3,
    )
    taxonomy_candidates = build_taxonomy_candidates(novel_clusters)
    scores = rank_accelerations(experiment.acceleration)
    score_by_bucket = {item.bucket: item for item in scores}
    handoff_preview = tuple(
        build_handoff_record(snapshot, experiment.current.signals)
        for snapshot in experiment.acceleration
        if snapshot.triggered or snapshot.confirmed
    )
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(
        json.dumps([handoff_to_dict(item) for item in handoff_preview], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report.update(
        {
            "status": "complete",
            "aggregation_level": args.aggregation_level,
            "cohort": asdict(experiment.diagnostics),
            "artifacts": {
                "current_signals_jsonl": str(current_signal_path),
                "baseline_signals_jsonl": str(baseline_signal_path),
                "review_queue": str(args.review_queue),
                "handoff_preview_json": str(handoff_path),
            },
            "current": {
                "companies": [asdict(item) for item in experiment.current.companies],
                "signal_count": len(experiment.current.signals),
                "clusters": [asdict(item) for item in experiment.current.clusters],
                "diagnostics": asdict(summarize_signal_diagnostics(experiment.current.signals)),
            },
            "baseline": {
                "companies": [asdict(item) for item in experiment.baseline.companies],
                "signal_count": len(experiment.baseline.signals),
                "clusters": [asdict(item) for item in experiment.baseline.clusters],
                "diagnostics": asdict(summarize_signal_diagnostics(experiment.baseline.signals)),
            },
            "acceleration": [
                asdict(item) | {"discovery_score": asdict(score_by_bucket[item.bucket])}
                for item in experiment.acceleration
            ],
            "novel_language_clusters": [
                asdict(cluster) | {"distinct_companies": cluster.distinct_companies}
                for cluster in novel_clusters
            ],
            "taxonomy_candidates": [asdict(item) for item in taxonomy_candidates],
            "handoff_preview": [handoff_to_dict(item) for item in handoff_preview],
        }
    )
    _write_report(args.output, report)

    triggered = sum(item.triggered for item in experiment.acceleration)
    confirmed = sum(item.confirmed for item in experiment.acceleration)
    watchlisted = sum(item.watchlisted for item in experiment.acceleration)
    strongest_score = scores[0] if scores else None
    quality = report["pilot_diagnostics"]["transcript_quality"]  # type: ignore[index]
    ranking_text = (
        f" strongest_bucket={strongest_score.bucket!r} stage={strongest_score.stage} "
        f"discovery_score={strongest_score.score:.2f}"
        if strongest_score is not None
        else ""
    )
    print(
        f"status=complete provider={source.provider_name} "
        f"available_pairs={pilot.available_pairs}/{pilot.requested_pairs} "
        f"paired_companies={pilot.fully_available_companies} "
        f"current_signals={len(experiment.current.signals)} "
        f"baseline_signals={len(experiment.baseline.signals)} "
        f"watchlisted={watchlisted} triggered={triggered} confirmed={confirmed} "
        f"taxonomy_candidates={len(taxonomy_candidates)} "
        f"qa_detection_rate={quality['qa_detection_rate']:.1%} "  # type: ignore[index]
        f"speaker_label_rate={quality['speaker_label_rate']:.1%}"  # type: ignore[index]
        f"{ranking_text}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
