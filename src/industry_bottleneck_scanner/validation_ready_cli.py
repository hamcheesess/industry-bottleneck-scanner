from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .phase1_validation import ValidationCase, evaluate_validation_manifest, load_validation_cases_csv
from .pipeline_fingerprint import (
    RESULT_SCHEMA_VERSION,
    compute_experiment_input_fingerprint,
    compute_pipeline_fingerprint,
    missing_experiment_transcripts,
)
from .validation_policy import (
    FROZEN_VALIDATION_POLICY_ID,
    FROZEN_V1_MAX_CONTROL_FALSE_POSITIVE_RATE,
    FROZEN_V1_MIN_EXPECTED_METRIC_RECALL,
    FROZEN_V1_MIN_POSITIVE_RECALL,
    FROZEN_V1_REQUIRE_AGGREGATION_MATCH,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate only frozen Phase-1 results produced by the current pipeline from complete current local inputs. "
            "Missing, stale, or incomplete-cohort results can never contribute to a Phase-1 pass."
        )
    )
    parser.add_argument("--manifest", type=Path, default=Path("experiments/phase1_validation_cases.csv"))
    parser.add_argument("--base-dir", type=Path, default=Path("."))
    parser.add_argument("--metadata-root", type=Path, default=Path("var/validation/metadata"))
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--provider", default="alpha_vantage")
    parser.add_argument("--max-companies", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("var/validation/ready-validation.json"))
    parser.add_argument("--min-positive-recall", type=float, default=FROZEN_V1_MIN_POSITIVE_RECALL)
    parser.add_argument("--max-control-fpr", type=float, default=FROZEN_V1_MAX_CONTROL_FALSE_POSITIVE_RATE)
    parser.add_argument("--min-metric-recall", type=float, default=FROZEN_V1_MIN_EXPECTED_METRIC_RECALL)
    return parser


def _rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _resolve(base_dir: Path, path: Path) -> Path:
    return path if path.is_absolute() else base_dir / path


def _result_path(case: ValidationCase, base_dir: Path) -> Path:
    return _resolve(base_dir, Path(case.result_path))


def _metadata_paths(case: ValidationCase, *, base_dir: Path, metadata_root: Path) -> tuple[Path, Path]:
    if case.current_metadata_path and case.baseline_metadata_path:
        return (
            _resolve(base_dir, Path(case.current_metadata_path)),
            _resolve(base_dir, Path(case.baseline_metadata_path)),
        )
    root = _resolve(base_dir, metadata_root)
    return root / f"{case.case_id}-current.csv", root / f"{case.case_id}-baseline.csv"


def _freshness(
    case: ValidationCase,
    *,
    base_dir: Path,
    metadata_root: Path,
    transcript_root: Path,
    provider: str,
    max_companies: int,
    pipeline_fingerprint: str,
) -> tuple[str, str | None]:
    current_metadata, baseline_metadata = _metadata_paths(
        case,
        base_dir=base_dir,
        metadata_root=metadata_root,
    )
    if not current_metadata.exists() or not baseline_metadata.exists():
        return "blocked_inputs", "current or baseline metadata is not locally available"

    resolved_transcript_root = _resolve(base_dir, transcript_root)
    missing_transcripts = missing_experiment_transcripts(
        current_metadata=current_metadata,
        baseline_metadata=baseline_metadata,
        provider=provider,
        transcript_root=resolved_transcript_root,
    )
    if missing_transcripts:
        return "blocked_coverage", ",".join(missing_transcripts)

    result_path = _result_path(case, base_dir)
    if not result_path.exists():
        return "missing_result", None
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return "invalid_result", str(exc)
    if not isinstance(payload, dict):
        return "invalid_result", "result JSON is not an object"
    provenance = payload.get("result_provenance")
    if not isinstance(provenance, dict):
        return "stale_pipeline", "missing result_provenance"
    if provenance.get("schema_version") != RESULT_SCHEMA_VERSION:
        return "stale_pipeline", "result schema version differs from current batch schema"
    if provenance.get("pipeline_fingerprint") != pipeline_fingerprint:
        return "stale_pipeline", "pipeline fingerprint differs from current result-affecting code"

    expected_input_fingerprint = compute_experiment_input_fingerprint(
        current_metadata=current_metadata,
        baseline_metadata=baseline_metadata,
        provider=provider,
        transcript_root=resolved_transcript_root,
        aggregation_level=case.aggregation_level,
        max_companies=max_companies,
    )
    if provenance.get("input_fingerprint") != expected_input_fingerprint:
        return "stale_inputs", "metadata, transcript cache, or result-affecting runtime settings changed since the result was written"
    return "fresh", None


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.max_companies < 1:
        raise SystemExit("--max-companies must be at least 1")
    for name, value in (
        ("--min-positive-recall", args.min_positive_recall),
        ("--max-control-fpr", args.max_control_fpr),
        ("--min-metric-recall", args.min_metric_recall),
    ):
        if not 0.0 <= value <= 1.0:
            raise SystemExit(f"{name} must be between 0 and 1")

    all_cases = load_validation_cases_csv(args.manifest.read_text(encoding="utf-8"))
    pipeline_fingerprint = compute_pipeline_fingerprint()
    states: dict[str, dict[str, object]] = {}
    fresh_cases: list[ValidationCase] = []
    for case in all_cases:
        state, detail = _freshness(
            case,
            base_dir=args.base_dir,
            metadata_root=args.metadata_root,
            transcript_root=args.transcript_root,
            provider=args.provider,
            max_companies=args.max_companies,
            pipeline_fingerprint=pipeline_fingerprint,
        )
        states[case.case_id] = {"state": state, "detail": detail}
        if state == "fresh":
            fresh_cases.append(case)

    report = evaluate_validation_manifest(tuple(fresh_cases), base_dir=args.base_dir)
    summary = report.summary
    diagnostic_gate_ok = bool(
        summary.positive_recall is not None
        and summary.positive_recall >= args.min_positive_recall
        and summary.control_false_positive_rate is not None
        and summary.control_false_positive_rate <= args.max_control_fpr
        and summary.expected_metric_recall is not None
        and summary.expected_metric_recall >= args.min_metric_recall
        and summary.aggregation_mismatches == 0
    )
    complete = len(fresh_cases) == len(all_cases)
    if complete:
        status = "complete_pass" if diagnostic_gate_ok else "complete_needs_more_validation"
        full_gate_ok: bool | None = diagnostic_gate_ok
    else:
        status = "partial_waiting_data"
        full_gate_ok = None

    missing_cases = [case_id for case_id, item in states.items() if item["state"] == "missing_result"]
    stale_cases = [
        case_id
        for case_id, item in states.items()
        if item["state"] in {"stale_pipeline", "stale_inputs", "invalid_result"}
    ]
    blocked_cases = [case_id for case_id, item in states.items() if item["state"] == "blocked_inputs"]
    blocked_coverage_cases = [
        case_id for case_id, item in states.items() if item["state"] == "blocked_coverage"
    ]

    payload = {
        "status": status,
        "validation_policy_id": FROZEN_VALIDATION_POLICY_ID,
        "full_validation_complete": complete,
        "provisional_gate_ok": full_gate_ok,
        "partial_diagnostic_gate_ok": diagnostic_gate_ok if fresh_cases else None,
        "total_frozen_cases": len(all_cases),
        "ready_case_ids": [case.case_id for case in fresh_cases],
        "missing_case_ids": missing_cases,
        "stale_case_ids": stale_cases,
        "blocked_input_case_ids": blocked_cases,
        "blocked_coverage_case_ids": blocked_coverage_cases,
        "case_freshness": states,
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "pipeline_fingerprint": pipeline_fingerprint,
        "max_companies": args.max_companies,
        "thresholds": {
            "min_positive_recall": args.min_positive_recall,
            "max_control_false_positive_rate": args.max_control_fpr,
            "min_expected_metric_recall": args.min_metric_recall,
            "require_aggregation_match": FROZEN_V1_REQUIRE_AGGREGATION_MATCH,
        },
        "summary": asdict(summary),
        "cases": [asdict(item) for item in report.cases],
        "policy": (
            "partial metrics are diagnostics only; no gate pass/fail is assigned until every frozen case is "
            "complete-cohort, current-pipeline, current-input, and freshness-approved"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        f"status={status} policy={FROZEN_VALIDATION_POLICY_ID} fresh={len(fresh_cases)}/{len(all_cases)} "
        f"strict_positive_recall={_rate(summary.positive_recall)} "
        f"stage_recall={_rate(summary.positive_stage_recall)} "
        f"control_fpr={_rate(summary.control_false_positive_rate)} "
        f"metric_recall={_rate(summary.expected_metric_recall)} "
        f"aggregation_mismatches={summary.aggregation_mismatches} "
        f"missing={','.join(missing_cases) or 'none'} stale={','.join(stale_cases) or 'none'} "
        f"blocked_inputs={','.join(blocked_cases) or 'none'} "
        f"blocked_coverage={','.join(blocked_coverage_cases) or 'none'}"
    )
    for item in report.cases:
        if item.role == "positive":
            print(
                f"positive_case={item.case_id} strict_recovered={item.positive_recovered} "
                f"stage_recovered={item.positive_stage_recovered} stage={item.expected_bucket_stage or 'none'} "
                f"metric_hits={','.join(item.expected_metric_hits) or 'none'} "
                f"metric_misses={','.join(item.expected_metric_misses) or 'none'}"
            )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
