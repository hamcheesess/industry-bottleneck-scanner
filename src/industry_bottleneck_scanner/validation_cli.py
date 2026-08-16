from __future__ import annotations

import argparse
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from .validation_policy import (
    FROZEN_VALIDATION_POLICY_ID,
    FROZEN_V1_MAX_CONTROL_FALSE_POSITIVE_RATE,
    FROZEN_V1_MIN_EXPECTED_METRIC_RECALL,
    FROZEN_V1_MIN_POSITIVE_RECALL,
)
from .validation_ready_cli import main as ready_main


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the complete frozen Phase-1 manifest under v1 gates, requiring current-pipeline, "
            "current-input, complete-cohort results for every case."
        )
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-dir", type=Path, default=Path("."))
    parser.add_argument("--metadata-root", type=Path, default=Path("var/validation/metadata"))
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--provider", default="alpha_vantage")
    parser.add_argument("--max-companies", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("var/validation/phase1-validation.json"))
    parser.add_argument("--min-positive-recall", type=float, default=FROZEN_V1_MIN_POSITIVE_RECALL)
    parser.add_argument("--max-control-fpr", type=float, default=FROZEN_V1_MAX_CONTROL_FALSE_POSITIVE_RATE)
    parser.add_argument("--min-metric-recall", type=float, default=FROZEN_V1_MIN_EXPECTED_METRIC_RECALL)
    return parser


def _rate(value: object) -> str:
    return "n/a" if not isinstance(value, (int, float)) else f"{float(value):.1%}"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.max_companies < 1:
        raise SystemExit("--max-companies must be at least 1")

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = ready_main(
            [
                "--manifest", str(args.manifest),
                "--base-dir", str(args.base_dir),
                "--metadata-root", str(args.metadata_root),
                "--transcript-root", str(args.transcript_root),
                "--provider", args.provider,
                "--max-companies", str(args.max_companies),
                "--output", str(args.output),
                "--min-positive-recall", str(args.min_positive_recall),
                "--max-control-fpr", str(args.max_control_fpr),
                "--min-metric-recall", str(args.min_metric_recall),
            ]
        )
    if code not in {0, None}:
        raise RuntimeError(f"freshness-aware validation failed with exit code {code}: {buffer.getvalue().strip()}")

    payload = json.loads(args.output.read_text(encoding="utf-8"))
    complete = bool(payload.get("full_validation_complete"))
    gates_ok = bool(payload.get("provisional_gate_ok"))
    passed = complete and gates_ok
    payload["status"] = "pass" if passed else "needs_more_validation"
    payload["mode"] = "complete_frozen_manifest"
    payload["validation_policy_id"] = FROZEN_VALIDATION_POLICY_ID
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    print(
        f"status={payload['status']} policy={FROZEN_VALIDATION_POLICY_ID} "
        f"complete={complete} fresh={len(payload.get('ready_case_ids', []))}/{payload.get('total_frozen_cases', '?')} "
        f"strict_positive_recall={_rate(summary.get('positive_recall'))} "
        f"stage_recall={_rate(summary.get('positive_stage_recall'))} "
        f"metric_recall={_rate(summary.get('expected_metric_recall'))} "
        f"control_fpr={_rate(summary.get('control_false_positive_rate'))}"
    )
    print(f"wrote {args.output}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
