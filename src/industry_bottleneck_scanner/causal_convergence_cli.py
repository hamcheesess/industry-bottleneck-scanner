from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .causal_graph import FileCausalGraphStore
from .causal_orchestration import run_causal_convergence, write_causal_convergence_artifacts
from .industry_state import FileIndustryStateRegistry
from .root_demand_shock import FileRootShockStore


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timestamp must use ISO-8601") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamp must include a timezone offset")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Traverse approved causal paths and assess pre-shock demand convergence"
    )
    parser.add_argument("--root-shock-registry", type=Path, required=True)
    parser.add_argument("--causal-graph-registry", type=Path, required=True)
    parser.add_argument("--industry-state-registry", type=Path, required=True)
    parser.add_argument("--trigger-root-shock-id", required=True)
    parser.add_argument("--as-of", type=_timestamp, required=True)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_depth < 1:
        raise SystemExit("--max-depth must be at least 1")
    run = run_causal_convergence(
        root_store=FileRootShockStore(args.root_shock_registry),
        graph_store=FileCausalGraphStore(args.causal_graph_registry),
        state_registry=FileIndustryStateRegistry(args.industry_state_registry),
        trigger_root_shock_id=args.trigger_root_shock_id,
        as_of=args.as_of,
        max_depth=args.max_depth,
    )
    write_causal_convergence_artifacts(args.output_dir, run)
    promoted = sum(
        item.stage in {"multi_branch_convergence", "priority_convergence"}
        for item in run.assessments
    )
    print(
        f"roots={len(run.root_shock_ids)} branches={len(run.branches)} "
        f"assessments={len(run.assessments)} promoted={promoted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
