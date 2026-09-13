from __future__ import annotations

import argparse
from pathlib import Path

from .root_shock_research_packet import build_root_shock_research_packets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build bounded strict-as-of research packets without approving root shocks"
    )
    parser.add_argument("--causal-diagnosis-dir", type=Path, required=True)
    parser.add_argument("--operating-evidence-dir", type=Path, required=True)
    parser.add_argument("--quality-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-evidence-per-candidate", type=int, default=12)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_root_shock_research_packets(
        causal_diagnosis_dir=args.causal_diagnosis_dir,
        operating_evidence_dir=args.operating_evidence_dir,
        quality_audit_path=args.quality_audit,
        output_dir=args.output_dir,
        max_evidence_per_candidate=args.max_evidence_per_candidate,
    )
    print(
        f"candidates={manifest['candidate_count']} approval_ready=0 "
        f"automatic_root_shock_approvals=0 strict_as_of=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
