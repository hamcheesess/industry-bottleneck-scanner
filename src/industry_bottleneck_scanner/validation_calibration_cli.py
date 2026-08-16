from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .validation_diagnose_cli import diagnose_result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Diagnose completed Phase-1 validation cases, especially control false positives, without tuning gates."
    )
    parser.add_argument("--cases", type=Path, default=Path("experiments/phase1_validation_cases.csv"))
    parser.add_argument("--output", type=Path, default=Path("var/validation/calibration-diagnostics.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    with args.cases.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    cases: list[dict[str, object]] = []
    for row in rows:
        result_path = Path((row.get("result_path") or "").strip())
        if not result_path.exists():
            continue
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        diagnosis = diagnose_result(payload)
        clusters = diagnosis["clusters"]
        triggered = [item for item in clusters if item.get("triggered")]
        watch_or_trigger = [item for item in clusters if item.get("triggered") or item.get("watchlisted")]
        cases.append(
            {
                "case_id": (row.get("case_id") or "").strip(),
                "role": (row.get("role") or "").strip(),
                "result_path": str(result_path),
                "triggered_clusters": triggered,
                "watch_or_trigger_clusters": watch_or_trigger,
            }
        )

    completed_controls = [item for item in cases if item["role"] == "control"]
    false_positive_controls = [item for item in completed_controls if item["triggered_clusters"]]
    completed_positives = [item for item in cases if item["role"] == "positive"]
    triggered_positives = [item for item in completed_positives if item["triggered_clusters"]]
    stage_recovered_positives = [item for item in completed_positives if item["watch_or_trigger_clusters"]]
    payload = {
        "status": "diagnosed",
        "completed_cases": len(cases),
        "completed_positive_cases": len(completed_positives),
        "triggered_positive_cases": len(triggered_positives),
        "watch_or_trigger_positive_cases": len(stage_recovered_positives),
        "completed_control_cases": len(completed_controls),
        "false_positive_control_cases": len(false_positive_controls),
        "provisional_control_fpr": (
            len(false_positive_controls) / len(completed_controls) if completed_controls else None
        ),
        "cases": cases,
        "policy": "diagnostic only; no production threshold or vocabulary mutation",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    fpr = payload["provisional_control_fpr"]
    fpr_text = "n/a" if fpr is None else f"{fpr:.1%}"
    print(
        f"status=diagnosed completed={len(cases)} "
        f"positives_triggered={len(triggered_positives)}/{len(completed_positives)} "
        f"positives_watch_or_trigger={len(stage_recovered_positives)}/{len(completed_positives)} "
        f"control_false_positives={len(false_positive_controls)}/{len(completed_controls)} "
        f"provisional_control_fpr={fpr_text}"
    )
    for item in false_positive_controls:
        for cluster in item["triggered_clusters"]:
            print(
                f"false_positive_case={item['case_id']} bucket={cluster['bucket']!r} "
                f"core_gain={cluster['any_core_dimension_accelerating']} "
                f"both_core_gain={cluster['both_core_dimensions_accelerating']} "
                f"demand_gains={','.join(cluster['positive_demand_metric_gains']) or 'none'} "
                f"scarcity_gains={','.join(cluster['positive_scarcity_metric_gains']) or 'none'} "
                f"confirmer_gains={','.join(cluster['positive_confirmer_metric_gains']) or 'none'}"
            )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
