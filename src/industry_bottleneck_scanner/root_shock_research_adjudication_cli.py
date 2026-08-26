from __future__ import annotations

import argparse
from pathlib import Path

from .root_shock_research_adjudication import adjudicate_root_shock_research


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate one root-shock research result without appending it"
    )
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--research-result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = adjudicate_root_shock_research(
        packet_path=args.packet,
        research_result_path=args.research_result,
        output_dir=args.output_dir,
    )
    print(
        f"packet_id={result['packet_id']} approval_eligible="
        f"{str(result['approval_eligible']).lower()} append_performed=false "
        f"reasons={','.join(result['reasons']) or 'none'}"
    )
    return 0 if result["approval_eligible"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
