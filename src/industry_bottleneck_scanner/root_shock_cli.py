from __future__ import annotations

import argparse
import json
from pathlib import Path

from .root_demand_shock import (
    FileRootShockStore,
    evaluate_root_demand_shock,
    root_shock_from_dict,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate and append one evidence-backed root demand shock revision"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("root-shock input must be an object")
    if payload.pop("schema_version", None) != "root-demand-shock-input-v1":
        raise SystemExit("unsupported root-shock input schema")
    shock = root_shock_from_dict(payload)
    approval = evaluate_root_demand_shock(shock)
    FileRootShockStore(args.registry).append(approval)
    print(
        f"root_shock_id={shock.root_shock_id} approved={str(approval.approved).lower()} "
        f"evidence_classes={len(approval.evidence_classes)} "
        f"reasons={','.join(approval.reasons) or 'none'}"
    )
    return 0 if approval.approved else 2


if __name__ == "__main__":
    raise SystemExit(main())
