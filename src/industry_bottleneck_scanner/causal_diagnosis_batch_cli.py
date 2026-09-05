from __future__ import annotations

import argparse
from pathlib import Path

from .causal_diagnosis_batch import build_causal_diagnosis_batch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Join dated market triggers to OperatingSupport without approving root shocks"
    )
    parser.add_argument("--market-triggers", type=Path, required=True)
    parser.add_argument("--operating-evidence-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_causal_diagnosis_batch(
        market_trigger_path=args.market_triggers,
        operating_evidence_dir=args.operating_evidence_dir,
        output_dir=args.output_dir,
    )
    counts = manifest["classification_counts"]
    print(
        f"diagnoses={manifest['diagnosis_count']} structural={counts['structural_operating']} "
        f"mixed={counts['mixed_or_early']} unresolved={counts['unresolved']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
