from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .causal_graph import FileCausalGraphStore
from .causal_orchestration import run_causal_convergence
from .industry_state import FileIndustryStateRegistry
from .pre_news_replay import (
    build_replay_freeze,
    build_replay_result_artifact,
    replay_spec_from_dict,
    run_pre_news_replay,
    write_replay_artifacts,
)
from .root_demand_shock import FileRootShockStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a frozen look-ahead-safe causal pre-news replay"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--market-trigger-artifact", type=Path, required=True)
    parser.add_argument("--root-shock-registry", type=Path, required=True)
    parser.add_argument("--causal-graph-registry", type=Path, required=True)
    parser.add_argument("--industry-state-registry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-depth", type=int, default=4)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("historical replay input must be an object")
    spec = replay_spec_from_dict(payload)

    root_store = FileRootShockStore(args.root_shock_registry)
    graph_store = FileCausalGraphStore(args.causal_graph_registry)
    state_registry = FileIndustryStateRegistry(args.industry_state_registry)
    approved = {
        item.root_shock_id: item
        for item in root_store.approved_shocks_as_of(as_of=spec.as_of)
    }
    trigger = approved.get(spec.trigger_root_shock_id)
    if trigger is None:
        raise SystemExit("trigger root shock is not approved at replay as_of")
    if trigger.market_trigger_id != spec.market_trigger_id:
        raise SystemExit("market_trigger_id does not match the approved root shock")

    market_payload = json.loads(args.market_trigger_artifact.read_text(encoding="utf-8"))
    if not isinstance(market_payload, dict):
        raise SystemExit("market-trigger artifact must be an object")
    if market_payload.get("schema_version") != "industry-market-trigger-v1":
        raise SystemExit("unsupported market-trigger artifact schema")
    market_as_of = date.fromisoformat(str(market_payload.get("as_of")))
    if market_as_of != trigger.detected_at.date():
        raise SystemExit("market-trigger artifact date does not match trigger detection date")
    trigger_rows = market_payload.get("triggers")
    if not isinstance(trigger_rows, list) or not any(
        isinstance(item, dict)
        and item.get("bucket") == trigger.market_bucket
        and item.get("triggered") is True
        for item in trigger_rows
    ):
        raise SystemExit("approved root bucket is not triggered in the frozen market artifact")

    run = run_causal_convergence(
        root_store=root_store,
        graph_store=graph_store,
        state_registry=state_registry,
        trigger_root_shock_id=spec.trigger_root_shock_id,
        as_of=spec.as_of,
        max_depth=args.max_depth,
    )
    replay = run_pre_news_replay(run, spec)
    freeze = build_replay_freeze(
        spec,
        trigger_detected_at=trigger.detected_at,
        input_paths={
            "replay_input": args.input,
            "market_trigger_artifact": args.market_trigger_artifact,
            "root_shock_registry": args.root_shock_registry,
            "causal_graph_registry": args.causal_graph_registry,
            "industry_state_registry": args.industry_state_registry,
        },
    )
    result = build_replay_result_artifact(replay, run, freeze)
    freeze_path, rankings_path = write_replay_artifacts(
        args.output_dir,
        freeze=freeze,
        result=result,
    )
    print(
        f"replay_id={spec.replay_id} status=full "
        f"promoted_nodes={len(replay.assessments)} "
        f"freeze={freeze_path} rankings={rankings_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
