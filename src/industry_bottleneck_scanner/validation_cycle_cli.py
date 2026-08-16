from __future__ import annotations

import argparse
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from .validation_calibration_cli import main as calibration_main
from .validation_ready_cli import main as ready_main
from .validation_run_cli import main as validation_run_main


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete cache-only Phase-1 validation cycle for all metadata-and-cache-ready frozen cases, "
            "then evaluate only fresh complete-cohort results and regenerate calibration diagnostics from that same fresh set. "
            "No provider calls or tuning occur."
        )
    )
    parser.add_argument("--cases", type=Path, default=Path("experiments/phase1_validation_cases.csv"))
    parser.add_argument("--metadata-root", type=Path, default=Path("var/validation/metadata"))
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--provider", default="alpha_vantage")
    parser.add_argument("--max-companies", type=int, default=50)
    parser.add_argument("--artifact-root", type=Path, default=Path("var/validation/artifacts"))
    parser.add_argument("--review-root", type=Path, default=Path("var/validation/review"))
    parser.add_argument("--run-status", type=Path, default=Path("var/validation/run-status.json"))
    parser.add_argument("--ready-output", type=Path, default=Path("var/validation/ready-validation.json"))
    parser.add_argument(
        "--calibration-output",
        type=Path,
        default=Path("var/validation/calibration-diagnostics.json"),
    )
    parser.add_argument("--output", type=Path, default=Path("var/validation/cycle-status.json"))
    return parser


def _run_quietly(function, argv: list[str]) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = function(argv)
    if code not in {0, None}:
        detail = buffer.getvalue().strip()
        raise RuntimeError(f"validation cycle subcommand failed with exit code {code}: {detail}")
    return buffer.getvalue()


def _rate(value: object) -> str:
    return "n/a" if not isinstance(value, (int, float)) else f"{float(value):.1%}"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.max_companies < 1:
        raise SystemExit("--max-companies must be at least 1")

    _run_quietly(
        validation_run_main,
        [
            "--cases", str(args.cases),
            "--metadata-root", str(args.metadata_root),
            "--transcript-root", str(args.transcript_root),
            "--provider", args.provider,
            "--max-companies", str(args.max_companies),
            "--artifact-root", str(args.artifact_root),
            "--review-root", str(args.review_root),
            "--output", str(args.run_status),
        ],
    )
    _run_quietly(
        ready_main,
        [
            "--manifest", str(args.cases),
            "--metadata-root", str(args.metadata_root),
            "--transcript-root", str(args.transcript_root),
            "--provider", args.provider,
            "--max-companies", str(args.max_companies),
            "--output", str(args.ready_output),
        ],
    )
    _run_quietly(
        calibration_main,
        [
            "--cases", str(args.cases),
            "--ready-state", str(args.ready_output),
            "--output", str(args.calibration_output),
        ],
    )

    run_status = json.loads(args.run_status.read_text(encoding="utf-8"))
    ready = json.loads(args.ready_output.read_text(encoding="utf-8"))
    calibration = json.loads(args.calibration_output.read_text(encoding="utf-8"))
    summary = ready.get("summary") if isinstance(ready, dict) else {}
    if not isinstance(summary, dict):
        summary = {}

    output = {
        "status": ready.get("status", "unknown"),
        "run": run_status,
        "freshness_and_validation": ready,
        "calibration": calibration,
        "max_companies": args.max_companies,
        "policy": (
            "cache-only validation cycle; no provider collection, label mutation, vocabulary tuning, "
            "or trigger-threshold mutation; incomplete frozen transcript coverage is never scored; "
            "calibration diagnostics use exactly the freshness-approved case set"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    ready_ids = ready.get("ready_case_ids", []) if isinstance(ready, dict) else []
    missing = ready.get("missing_case_ids", []) if isinstance(ready, dict) else []
    stale = ready.get("stale_case_ids", []) if isinstance(ready, dict) else []
    blocked = ready.get("blocked_input_case_ids", []) if isinstance(ready, dict) else []
    blocked_coverage = ready.get("blocked_coverage_case_ids", []) if isinstance(ready, dict) else []
    print(
        f"status={ready.get('status', 'unknown')} fresh={len(ready_ids)}/{ready.get('total_frozen_cases', '?')} "
        f"strict_positive_recall={_rate(summary.get('positive_recall'))} "
        f"stage_recall={_rate(summary.get('positive_stage_recall'))} "
        f"metric_recall={_rate(summary.get('expected_metric_recall'))} "
        f"control_fpr={_rate(summary.get('control_false_positive_rate'))} "
        f"missing={','.join(missing) or 'none'} stale={','.join(stale) or 'none'} "
        f"blocked_inputs={','.join(blocked) or 'none'} "
        f"blocked_coverage={','.join(blocked_coverage) or 'none'}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
