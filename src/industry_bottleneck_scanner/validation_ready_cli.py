from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .phase1_validation import evaluate_validation_manifest, load_validation_cases_csv


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate only frozen Phase-1 cases whose result JSON already exists. "
            "This is an interim diagnostic and can never declare full Phase-1 validation complete."
        )
    )
    parser.add_argument("--manifest", type=Path, default=Path("experiments/phase1_validation_cases.csv"))
    parser.add_argument("--base-dir", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("var/validation/ready-validation.json"))
    parser.add_argument("--min-positive-recall", type=float, default=0.67)
    parser.add_argument("--max-control-fpr", type=float, default=0.20)
    parser.add_argument("--min-metric-recall", type=float, default=0.67)
    return parser


def _rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _result_exists(result_path: str, base_dir: Path) -> bool:
    path = Path(result_path)
    return (path if path.is_absolute() else base_dir / path).exists()


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    for name, value in (
        ("--min-positive-recall", args.min_positive_recall),
        ("--max-control-fpr", args.max_control_fpr),
        ("--min-metric-recall", args.min_metric_recall),
    ):
        if not 0.0 <= value <= 1.0:
            raise SystemExit(f"{name} must be between 0 and 1")

    all_cases = load_validation_cases_csv(args.manifest.read_text(encoding="utf-8"))
    ready_cases = tuple(case for case in all_cases if _result_exists(case.result_path, args.base_dir))
    missing_cases = tuple(case.case_id for case in all_cases if case not in ready_cases)
    if not ready_cases:
        raise SystemExit("no frozen validation result JSON files are available yet")

    report = evaluate_validation_manifest(ready_cases, base_dir=args.base_dir)
    summary = report.summary
    provisional_gate_ok = bool(
        summary.positive_recall is not None
        and summary.positive_recall >= args.min_positive_recall
        and summary.control_false_positive_rate is not None
        and summary.control_false_positive_rate <= args.max_control_fpr
        and summary.expected_metric_recall is not None
        and summary.expected_metric_recall >= args.min_metric_recall
        and summary.aggregation_mismatches == 0
    )
    complete = len(ready_cases) == len(all_cases)
    status = "complete_pass" if complete and provisional_gate_ok else (
        "complete_needs_more_validation" if complete else (
            "partial_gates_ok" if provisional_gate_ok else "partial_gates_not_met"
        )
    )

    payload = {
        "status": status,
        "full_validation_complete": complete,
        "provisional_gate_ok": provisional_gate_ok,
        "ready_case_ids": [case.case_id for case in ready_cases],
        "missing_case_ids": list(missing_cases),
        "thresholds": {
            "min_positive_recall": args.min_positive_recall,
            "max_control_false_positive_rate": args.max_control_fpr,
            "min_expected_metric_recall": args.min_metric_recall,
            "require_aggregation_match": True,
        },
        "summary": asdict(summary),
        "cases": [asdict(item) for item in report.cases],
        "policy": "interim diagnostic only; missing frozen cases prevent a Phase-1 pass",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        f"status={status} ready={len(ready_cases)}/{len(all_cases)} "
        f"positive_recall={_rate(summary.positive_recall)} "
        f"control_fpr={_rate(summary.control_false_positive_rate)} "
        f"metric_recall={_rate(summary.expected_metric_recall)} "
        f"aggregation_mismatches={summary.aggregation_mismatches} "
        f"missing={','.join(missing_cases) or 'none'}"
    )
    for item in report.cases:
        if item.role == "positive":
            print(
                f"positive_case={item.case_id} recovered={item.positive_recovered} "
                f"stage={item.expected_bucket_stage or 'none'} "
                f"metric_hits={','.join(item.expected_metric_hits) or 'none'} "
                f"metric_misses={','.join(item.expected_metric_misses) or 'none'}"
            )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
