from __future__ import annotations

import argparse
import json
from pathlib import Path

POLICY_ID = "frozen-v1-alpha-vantage-only"


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return value


def _req(item: object) -> str | None:
    if not isinstance(item, dict):
        return None
    ticker = str(item.get("ticker") or "").strip().upper()
    quarter = str(item.get("quarter") or "").strip().upper()
    return f"{ticker}:{quarter}" if ticker and quarter else None


def _terminal_missing(collection: dict[str, object]) -> tuple[bool, list[str]]:
    remaining = {_req(item) for item in collection.get("missing_requests", [])}
    remaining.discard(None)
    run = collection.get("run") if isinstance(collection.get("run"), dict) else {}
    items = run.get("items") if isinstance(run.get("items"), list) else []
    missing = {_req(item) for item in items if isinstance(item, dict) and item.get("status") == "missing"}
    missing.discard(None)
    blocked = any(
        isinstance(item, dict) and item.get("status") == "budget_exhausted"
        for item in items
    )
    terminal = bool(
        remaining
        and remaining == missing
        and int(run.get("rate_limited") or 0) == 0
        and int(run.get("errors") or 0) == 0
        and not blocked
    )
    return terminal, sorted(str(item) for item in missing)


def _false_positive_controls(calibration: dict[str, object]) -> list[str]:
    result: list[str] = []
    cases = calibration.get("cases") if isinstance(calibration.get("cases"), list) else []
    for item in cases:
        if not isinstance(item, dict) or item.get("role") != "control":
            continue
        if isinstance(item.get("triggered_clusters"), list) and item["triggered_clusters"]:
            case_id = str(item.get("case_id") or "").strip()
            if case_id:
                result.append(case_id)
    return sorted(set(result))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Close frozen v1 under its Alpha-Vantage-only source contract.")
    parser.add_argument("--collection", type=Path, default=Path("var/validation/collection-status.json"))
    parser.add_argument("--ready", type=Path, default=Path("var/validation/ready-validation.json"))
    parser.add_argument("--calibration", type=Path, default=Path("var/validation/calibration-diagnostics.json"))
    parser.add_argument("--policy", type=Path, default=Path("experiments/frozen_v1_source_policy.json"))
    parser.add_argument("--output", type=Path, default=Path("var/validation/frozen-v1-review.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    collection = _load(args.collection)
    ready = _load(args.ready)
    calibration = _load(args.calibration)
    policy = _load(args.policy)
    if policy.get("policy_id") != POLICY_ID or policy.get("provider") != "alpha_vantage":
        raise SystemExit("frozen v1 source policy mismatch")
    if bool(policy.get("fallback_provider_allowed")):
        raise SystemExit("frozen v1 fallback provider must remain disabled")

    terminal, missing = _terminal_missing(collection)
    full = bool(ready.get("full_validation_complete"))
    if full:
        status = "closed_complete"
        next_gate = "frozen_v1_review"
    elif terminal:
        status = "closed_source_coverage_limited"
        next_gate = "v2_validation_contract_design"
    else:
        status = "not_closable_data_incomplete"
        next_gate = "data_completion"

    summary = ready.get("summary") if isinstance(ready.get("summary"), dict) else {}
    false_positives = _false_positive_controls(calibration)
    fresh = ready.get("ready_case_ids") if isinstance(ready.get("ready_case_ids"), list) else []
    payload = {
        "status": status,
        "source_policy_id": POLICY_ID,
        "full_manifest_scored": full,
        "phase2_ready": bool(full and ready.get("status") == "complete_pass"),
        "next_gate": next_gate,
        "fresh_case_ids": fresh,
        "total_frozen_cases": ready.get("total_frozen_cases"),
        "provider_missing_requests": missing,
        "terminal_provider_missing": terminal,
        "diagnostics": summary,
        "false_positive_control_case_ids": false_positives,
        "policy": "No fallback provider, blind-cohort mutation, or scanner tuning is allowed to manufacture a complete frozen-v1 result.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"status={status} phase2_ready={str(payload['phase2_ready']).lower()} next_gate={next_gate} "
        f"fresh={len(fresh)}/{ready.get('total_frozen_cases', '?')} "
        f"provider_missing={','.join(missing) or 'none'} "
        f"false_positive_controls={','.join(false_positives) or 'none'}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
