from __future__ import annotations

import argparse
import json
from pathlib import Path

from .vocabulary import DEFAULT_PATTERNS


CORE_SCANNERS = {"demand", "scarcity"}
CONFIRMERS = {"capex", "pricing"}
_DIRECTION_BY_METRIC = {item.metric: item.direction for item in DEFAULT_PATTERNS}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose why a frozen Phase-1 result reached its stage without changing any "
            "production threshold. Emits prevalence deltas and core-vs-confirmer acceleration."
        )
    )
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser


def _cluster_metrics(payload: dict[str, object], bucket: str, window: str) -> set[str]:
    section = payload.get(window)
    if not isinstance(section, dict):
        return set()
    clusters = section.get("clusters")
    if not isinstance(clusters, list):
        return set()
    for item in clusters:
        if isinstance(item, dict) and item.get("bucket") == bucket:
            metrics = item.get("active_metrics")
            if isinstance(metrics, list):
                return {str(value) for value in metrics}
    return set()


def _scanner_for_metric(metric: str) -> str:
    for pattern in DEFAULT_PATTERNS:
        if pattern.metric == metric:
            return pattern.scanner
    return "unknown"


def diagnose_result(payload: dict[str, object]) -> dict[str, object]:
    acceleration = payload.get("acceleration")
    if not isinstance(acceleration, list) or not acceleration:
        return {"status": "no_acceleration", "clusters": []}

    diagnostics: list[dict[str, object]] = []
    for raw in acceleration:
        if not isinstance(raw, dict):
            continue
        bucket = str(raw.get("bucket") or "")
        gains = [str(value) for value in raw.get("metric_prevalence_gains", [])]
        deltas = raw.get("metric_prevalence_deltas")
        delta_rows = [item for item in deltas if isinstance(item, dict)] if isinstance(deltas, list) else []
        positive_core = [metric for metric in gains if _scanner_for_metric(metric) in CORE_SCANNERS]
        positive_demand = [metric for metric in gains if _scanner_for_metric(metric) == "demand"]
        positive_scarcity = [metric for metric in gains if _scanner_for_metric(metric) == "scarcity"]
        positive_confirmers = [metric for metric in gains if _scanner_for_metric(metric) in CONFIRMERS]
        directional_inconsistencies = [
            metric for metric in gains if _DIRECTION_BY_METRIC.get(metric) == "weakening"
        ]
        active_current = _cluster_metrics(payload, bucket, "current")
        active_baseline = _cluster_metrics(payload, bucket, "baseline")
        diagnostics.append(
            {
                "bucket": bucket,
                "triggered": bool(raw.get("triggered")),
                "confirmed": bool(raw.get("confirmed")),
                "watchlisted": bool(raw.get("watchlisted")),
                "core_pair_present_current": bool(raw.get("core_pair_present")),
                "breadth_change": raw.get("breadth_change"),
                "company_metric_intensity_change": raw.get("company_metric_intensity_change"),
                "metric_prevalence_gain_count": raw.get("metric_prevalence_gain_count"),
                "positive_core_metric_gains": positive_core,
                "positive_demand_metric_gains": positive_demand,
                "positive_scarcity_metric_gains": positive_scarcity,
                "positive_confirmer_metric_gains": positive_confirmers,
                "both_core_dimensions_accelerating": bool(positive_demand and positive_scarcity),
                "any_core_dimension_accelerating": bool(positive_core),
                "directional_inconsistencies": directional_inconsistencies,
                "active_metrics_current": sorted(active_current),
                "active_metrics_baseline": sorted(active_baseline),
                "new_active_metrics": sorted(active_current - active_baseline),
                "lost_active_metrics": sorted(active_baseline - active_current),
                "metric_prevalence_deltas": delta_rows,
            }
        )

    return {"status": "diagnosed", "clusters": diagnostics}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    payload = json.loads(args.result.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("result JSON must be an object")
    report = diagnose_result(payload)
    clusters = report["clusters"]
    triggered = [item for item in clusters if item.get("triggered")]
    for item in triggered:
        print(
            f"bucket={item['bucket']!r} triggered={item['triggered']} confirmed={item['confirmed']} "
            f"core_pair_current={item['core_pair_present_current']} "
            f"core_gain={item['any_core_dimension_accelerating']} "
            f"both_core_gain={item['both_core_dimensions_accelerating']} "
            f"demand_gains={','.join(item['positive_demand_metric_gains']) or 'none'} "
            f"scarcity_gains={','.join(item['positive_scarcity_metric_gains']) or 'none'} "
            f"confirmer_gains={','.join(item['positive_confirmer_metric_gains']) or 'none'} "
            f"directional_inconsistencies={','.join(item['directional_inconsistencies']) or 'none'}"
        )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
