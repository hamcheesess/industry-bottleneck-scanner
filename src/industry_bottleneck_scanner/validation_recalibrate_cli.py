from __future__ import annotations

import argparse
from pathlib import Path

from .validation_calibration_cli import main as calibration_main
from .validation_run_cli import main as validation_run_main


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Re-run every validation case whose verified metadata is available, then regenerate "
            "calibration diagnostics. This is intended for correctness fixes, not threshold tuning."
        )
    )
    parser.add_argument("--cases", type=Path, default=Path("experiments/phase1_validation_cases.csv"))
    parser.add_argument("--metadata-root", type=Path, default=Path("var/validation/metadata"))
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--provider", default="alpha_vantage")
    parser.add_argument("--artifact-root", type=Path, default=Path("var/validation/artifacts"))
    parser.add_argument("--review-root", type=Path, default=Path("var/validation/review"))
    parser.add_argument("--run-status", type=Path, default=Path("var/validation/run-status.json"))
    parser.add_argument(
        "--diagnostics-output",
        type=Path,
        default=Path("var/validation/calibration-diagnostics.json"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    run_code = validation_run_main(
        [
            "--cases", str(args.cases),
            "--metadata-root", str(args.metadata_root),
            "--transcript-root", str(args.transcript_root),
            "--provider", args.provider,
            "--artifact-root", str(args.artifact_root),
            "--review-root", str(args.review_root),
            "--output", str(args.run_status),
        ]
    )
    if run_code != 0:
        raise RuntimeError(f"validation rerun failed with exit code {run_code}")

    diagnose_code = calibration_main(
        [
            "--cases", str(args.cases),
            "--output", str(args.diagnostics_output),
        ]
    )
    if diagnose_code != 0:
        raise RuntimeError(f"calibration diagnosis failed with exit code {diagnose_code}")

    print("status=recalibrated policy=correctness_fix_no_threshold_tuning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
