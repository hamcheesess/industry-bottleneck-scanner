from __future__ import annotations

import argparse
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable

from .validation_advance_cli import main as advance_main
from .validation_collection_cli import main as collection_main
from .validation_cycle_cli import main as cycle_main
from .validation_progress_cli import main as progress_main


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Resume the frozen Phase-1 validation workflow in one bounded pass: collect cache-first, "
            "draft metadata for newly complete cases, apply committed timestamp provenance where available, "
            "then run the cache-only validation cycle. A provider rate limit is recorded, not retried in a loop."
        )
    )
    parser.add_argument("--provider", default="alpha_vantage")
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--metadata-root", type=Path, default=Path("var/validation/metadata"))
    parser.add_argument("--cases", type=Path, default=Path("experiments/phase1_validation_cases.csv"))
    parser.add_argument("--blind-requests", type=Path, default=Path("var/cohort/neutral_proxy_requests.csv"))
    parser.add_argument("--blind-selection", type=Path, default=Path("var/cohort/neutral_proxy_selection.json"))
    parser.add_argument("--max-provider-requests", type=int, default=24)
    parser.add_argument("--interval-seconds", type=float, default=1.1)
    parser.add_argument("--max-companies", type=int, default=50)
    parser.add_argument("--collection-output", type=Path, default=Path("var/validation/collection-status.json"))
    parser.add_argument("--progress-output", type=Path, default=Path("var/validation/progress.json"))
    parser.add_argument("--advance-output", type=Path, default=Path("var/validation/advance-status.json"))
    parser.add_argument("--cycle-output", type=Path, default=Path("var/validation/cycle-status.json"))
    parser.add_argument("--output", type=Path, default=Path("var/validation/resume-status.json"))
    return parser


def _run_quietly(
    function: Callable[[list[str] | None], int | None],
    argv: list[str],
    *,
    accepted_codes: set[int],
) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = function(argv)
    normalized = 0 if code is None else int(code)
    if normalized not in accepted_codes:
        raise RuntimeError(
            f"validation resume subcommand failed with exit code {normalized}: {buffer.getvalue().strip()}"
        )
    return normalized, buffer.getvalue()


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return payload


def _list_text(value: object) -> str:
    if not isinstance(value, list):
        return "none"
    items = [str(item) for item in value]
    return ",".join(items) or "none"


def _rate(value: object) -> str:
    return "n/a" if not isinstance(value, (int, float)) else f"{float(value):.1%}"


def _next_action(collection: dict[str, object], cycle: dict[str, object]) -> str:
    next_gate = str(cycle.get("next_gate") or "unknown")
    if next_gate != "data_completion":
        return next_gate

    freshness = cycle.get("freshness_and_validation")
    if isinstance(freshness, dict):
        states = freshness.get("case_freshness")
        if isinstance(states, dict):
            blind = states.get("blind-proxy-2026")
            if isinstance(blind, dict):
                detail = str(blind.get("detail") or "")
                if blind.get("state") == "blocked_inputs" and "published_at" in detail:
                    return "blind_timestamp_provenance"

    run = collection.get("run")
    if isinstance(run, dict) and bool(run.get("rate_limited")):
        return "provider_quota_resume_later"
    if int(collection.get("remaining_after_run") or 0) > 0:
        return "provider_data_completion"
    return "metadata_completion"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.max_provider_requests < 1:
        raise SystemExit("--max-provider-requests must be at least 1")
    if args.interval_seconds < 0:
        raise SystemExit("--interval-seconds must be non-negative")
    if args.max_companies < 1:
        raise SystemExit("--max-companies must be at least 1")

    collection_code, _ = _run_quietly(
        collection_main,
        [
            "--transcript-root", str(args.transcript_root),
            "--max-provider-requests", str(args.max_provider_requests),
            "--interval-seconds", str(args.interval_seconds),
            "--blind-requests", str(args.blind_requests),
            "--output", str(args.collection_output),
        ],
        accepted_codes={0, 2},
    )

    _run_quietly(
        progress_main,
        [
            "--provider", args.provider,
            "--transcript-root", str(args.transcript_root),
            "--blind-requests", str(args.blind_requests),
            "--blind-selection", str(args.blind_selection),
            "--metadata-root", str(args.metadata_root),
            "--output", str(args.progress_output),
        ],
        accepted_codes={0},
    )

    _run_quietly(
        advance_main,
        [
            "--metadata-root", str(args.metadata_root),
            "--transcript-root", str(args.transcript_root),
            "--cases", str(args.cases),
            "--output", str(args.advance_output),
            "--skip-run",
        ],
        accepted_codes={0},
    )

    _run_quietly(
        cycle_main,
        [
            "--cases", str(args.cases),
            "--metadata-root", str(args.metadata_root),
            "--transcript-root", str(args.transcript_root),
            "--provider", args.provider,
            "--max-companies", str(args.max_companies),
            "--output", str(args.cycle_output),
        ],
        accepted_codes={0},
    )

    collection = _load(args.collection_output)
    progress = _load(args.progress_output)
    advance = _load(args.advance_output)
    cycle = _load(args.cycle_output)
    freshness = cycle.get("freshness_and_validation")
    if not isinstance(freshness, dict):
        freshness = {}
    summary = freshness.get("summary")
    if not isinstance(summary, dict):
        summary = {}

    next_action = _next_action(collection, cycle)
    payload = {
        "status": cycle.get("status", "unknown"),
        "next_gate": cycle.get("next_gate", "unknown"),
        "next_action": next_action,
        "collection_exit_code": collection_code,
        "collection": collection,
        "progress": progress,
        "advance": advance,
        "cycle": cycle,
        "policy": (
            "one bounded provider pass per invocation; provider rate limits are never retried in a loop; "
            "scanner vocabulary and trigger thresholds are not mutated"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    ready_ids = freshness.get("ready_case_ids", [])
    print(
        f"status={payload['status']} next_gate={payload['next_gate']} next_action={next_action} "
        f"collection_available={collection.get('available_after_run', '?')}/"
        f"{collection.get('planned_unique_requests', '?')} "
        f"fresh={len(ready_ids) if isinstance(ready_ids, list) else 0}/"
        f"{freshness.get('total_frozen_cases', '?')} "
        f"stage_recall={_rate(summary.get('positive_stage_recall'))} "
        f"metric_recall={_rate(summary.get('expected_metric_recall'))} "
        f"control_fpr={_rate(summary.get('control_false_positive_rate'))} "
        f"blocked_inputs={_list_text(freshness.get('blocked_input_case_ids'))} "
        f"blocked_coverage={_list_text(freshness.get('blocked_coverage_case_ids'))}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
