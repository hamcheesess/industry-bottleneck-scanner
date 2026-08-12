from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .phase1_validation import evaluate_validation_manifest, load_validation_cases_csv


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate known-positive, control, and blind Phase-1 experiments without changing trigger thresholds."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-dir", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("var/validation/phase1-validation.json"))
    parser.add_argument("--min-positive-recall", type=float, default=0.67)
    parser.add_argument("--max-control-fpr", type=float, default=0.20)
    parser.add_argument("--min-metric-recall", type=float, default=0.67)
    return parser


def _rate_text(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    for name, value in (
        ("--min-positive-recall", args.min_positive_recall),
        ("--max-control-fpr", args.max_control_fpr),
        ("--min-metric-recall", args.min_metric_recall),
    ):
        if not 0.0 <= value <= 1.0:
            raise SystemExit(f"{name} must be between 0 and 1")

    cases = load_validation_cases_csv(args.manifest.read_text(encoding="utf-8"))
    report = evaluate_validation_manifest(cases, base_dir=args.base_dir)
    summary = report.summary

    positive_ok = summary.positive_recall is not None and summary.positive_recall >= args.min_positive_recall
    control_ok = (
        summary.control_false_positive_rate is not None
        and summary.control_false_positive_rate <= args.max_control_fpr
    )
    metric_ok = (
        summary.expected_metric_recall is not None
        and summary.expected_metric_recall >= args.min_metric_recall
    )
    aggregation_ok = summary.aggregation_mismatches == 0
    ready = positive_ok and control_ok and metric_ok and aggregation_ok

    payload = {
        "status": "pass" if ready else "needs_more_validation",
        "thresholds": {
            "min_positive_recall": args.min_positive_recall,
            "max_control_false_positive_rate": args.max_control_fpr,
            "min_expected_metric_recall": args.min_metric_recall,
            "require_aggregation_match": True,
        },
        "summary": asdict(summary),
        "cases": [asdict(item) for item in report.cases],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        f"status={payload['status']} cases={summary.total_cases} "
        f"positive_recall={_rate_text(summary.positive_recall)} "
        f"control_fpr={_rate_text(summary.control_false_positive_rate)} "
        f"metric_recall={_rate_text(summary.expected_metric_recall)} "
        f"aggregation_mismatches={summary.aggregation_mismatches}"
    )
    print(f"wrote {args.output}")
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
