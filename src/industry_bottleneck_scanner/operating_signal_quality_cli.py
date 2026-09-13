from __future__ import annotations

import argparse
from pathlib import Path

from .operating_signal_quality import audit_operating_signal_quality


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit root-shock candidate signals for repeated and speculative risk language"
    )
    parser.add_argument("--causal-diagnosis-dir", type=Path, required=True)
    parser.add_argument("--operating-evidence-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = audit_operating_signal_quality(
        causal_diagnosis_dir=args.causal_diagnosis_dir,
        operating_evidence_dir=args.operating_evidence_dir,
        output_path=args.output,
    )
    counts = payload["quality_status_counts"]
    print(
        f"candidates={payload['candidate_count']} direct_multi_company={counts['direct_multi_company']} "
        f"sparse_direct={counts['sparse_direct']} boilerplate={counts['boilerplate_dominated']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
