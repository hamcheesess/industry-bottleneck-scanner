from __future__ import annotations

import argparse
import json
from pathlib import Path

from .causal_graph import FileCausalGraphStore, edge_input_from_dict, evaluate_edge


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate and append one evidence-backed value-chain edge revision"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("causal-edge input must be an object")
    try:
        edge_id, as_of, edge = edge_input_from_dict(payload)
        approval = evaluate_edge(edge_id, edge, as_of=as_of)
        FileCausalGraphStore(args.registry).append(approval)
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        f"edge_id={edge_id} approved={str(approval.approved).lower()} "
        f"evidence_classes={len(approval.evidence_classes)} "
        f"reasons={','.join(approval.reasons) or 'none'}"
    )
    return 0 if approval.approved else 2


if __name__ == "__main__":
    raise SystemExit(main())
