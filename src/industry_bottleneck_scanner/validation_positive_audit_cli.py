from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose why completed frozen positive cases are not recovered. "
            "Reports expected-metric support and stage blockers without changing labels, vocabulary, or gates."
        )
    )
    parser.add_argument("--cases", type=Path, default=Path("experiments/phase1_validation_cases.csv"))
    parser.add_argument("--artifact-root", type=Path, default=Path("var/validation/artifacts"))
    parser.add_argument("--output", type=Path, default=Path("var/validation/positive-audit.json"))
    return parser


def _pipe(value: str | None) -> tuple[str, ...]:
    return tuple(item.strip() for item in (value or "").split("|") if item.strip())


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            item = json.loads(text)
            if isinstance(item, dict):
                rows.append(item)
    return rows


def _stage(item: dict[str, object] | None) -> str:
    if not item:
        return "missing"
    score = item.get("discovery_score")
    if isinstance(score, dict) and isinstance(score.get("stage"), str):
        return str(score["stage"])
    if item.get("confirmed") is True:
        return "confirmed"
    if item.get("triggered") is True:
        return "triggered"
    if item.get("watchlisted") is True:
        return "watchlisted"
    return "observing"


def _active(signal: dict[str, object]) -> bool:
    return (
        signal.get("direction") == "strengthening"
        and not bool(signal.get("negated"))
        and not bool(signal.get("resolved"))
    )


def _bucket(signal: dict[str, object], level: str) -> str:
    classification = signal.get("classification")
    if not isinstance(classification, dict):
        return "unclassified"
    sector = str(classification.get("sector") or "")
    industry = str(classification.get("industry") or "")
    subindustry = str(classification.get("subindustry") or "")
    if level == "sector":
        return sector or industry or subindustry or "unclassified"
    if level == "subindustry":
        return subindustry or industry or sector or "unclassified"
    return industry or subindustry or sector or "unclassified"


def _metric_support(
    signals: list[dict[str, object]], *, metric: str, level: str, expected_bucket: str
) -> dict[str, object]:
    same_metric = [row for row in signals if str(row.get("metric") or "") == metric]
    active = [row for row in same_metric if _active(row)]
    in_bucket = [row for row in active if _bucket(row, level) == expected_bucket]
    weakening = [row for row in same_metric if not _active(row)]

    def companies(rows: list[dict[str, object]]) -> list[str]:
        return sorted({str(row.get("ticker") or row.get("company_id") or "") for row in rows if row.get("ticker") or row.get("company_id")})

    def evidence(rows: list[dict[str, object]]) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for row in rows[:8]:
            result.append(
                {
                    "ticker": row.get("ticker"),
                    "company_id": row.get("company_id"),
                    "direction": row.get("direction"),
                    "negated": row.get("negated"),
                    "resolved": row.get("resolved"),
                    "extraction_method": row.get("extraction_method"),
                    "source_section": row.get("source_section"),
                    "speaker": row.get("speaker"),
                    "speaker_title": row.get("speaker_title"),
                    "evidence_text": row.get("evidence_text"),
                }
            )
        return result

    if in_bucket:
        diagnosis = "active_expected_bucket_support"
    elif active:
        diagnosis = "active_support_wrong_bucket"
    elif weakening:
        diagnosis = "counter_evidence_only"
    else:
        diagnosis = "no_extracted_support"

    return {
        "metric": metric,
        "diagnosis": diagnosis,
        "active_expected_bucket_companies": companies(in_bucket),
        "active_other_bucket_companies": companies([row for row in active if row not in in_bucket]),
        "counter_evidence_companies": companies(weakening),
        "active_expected_bucket_evidence": evidence(in_bucket),
        "counter_evidence": evidence(weakening),
    }


def _stage_blockers(acceleration: dict[str, object] | None) -> list[str]:
    if not acceleration:
        return ["expected_bucket_missing"]
    if _stage(acceleration) != "observing":
        return []
    blockers = acceleration.get("watch_blockers")
    if isinstance(blockers, list):
        values = [str(item) for item in blockers if str(item)]
        if values:
            return values
    derived: list[str] = []
    if int(acceleration.get("breadth_current") or 0) < 3:
        derived.append("min_company_breadth")
    if int(acceleration.get("category_breadth") or 0) < 2:
        derived.append("min_category_breadth")
    if float(acceleration.get("confidence_mean") or 0.0) < 0.65:
        derived.append("min_confidence")
    if acceleration.get("core_pair_present") is not True:
        derived.append("demand_scarcity_core_pair")
    changes = acceleration.get("change_reasons")
    if not derived and not changes:
        derived.append("no_acceleration_change")
    return derived


def audit_case(row: dict[str, str], *, artifact_root: Path) -> dict[str, object] | None:
    if (row.get("role") or "").strip() != "positive":
        return None
    result_path = Path((row.get("result_path") or "").strip())
    if not result_path.exists():
        return None
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None

    case_id = (row.get("case_id") or "").strip()
    level = (row.get("aggregation_level") or "").strip()
    expected_bucket = (row.get("expected_bucket") or "").strip()
    expected_metrics = _pipe(row.get("expected_metrics"))
    current_signal_path = artifact_root / case_id / "current_signals.jsonl"
    signals = _read_jsonl(current_signal_path)

    acceleration_rows = payload.get("acceleration")
    acceleration = None
    if isinstance(acceleration_rows, list):
        acceleration = next(
            (
                item
                for item in acceleration_rows
                if isinstance(item, dict) and str(item.get("bucket") or "") == expected_bucket
            ),
            None,
        )

    metric_support = [
        _metric_support(signals, metric=metric, level=level, expected_bucket=expected_bucket)
        for metric in expected_metrics
    ]
    missing_metrics = [
        item["metric"]
        for item in metric_support
        if item["diagnosis"] != "active_expected_bucket_support"
    ]
    stage = _stage(acceleration)
    recovered = stage in {"watchlisted", "triggered", "confirmed"} and not missing_metrics
    return {
        "case_id": case_id,
        "result_path": str(result_path),
        "expected_bucket": expected_bucket,
        "aggregation_level": level,
        "stage": stage,
        "recovered": recovered,
        "missing_expected_metrics": missing_metrics,
        "stage_blockers": _stage_blockers(acceleration),
        "change_reasons": list(acceleration.get("change_reasons", [])) if isinstance(acceleration, dict) else [],
        "watch_blockers": list(acceleration.get("watch_blockers", [])) if isinstance(acceleration, dict) else [],
        "metric_support": metric_support,
        "current_signal_artifact": str(current_signal_path),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    with args.cases.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    cases = [item for row in rows if (item := audit_case(row, artifact_root=args.artifact_root)) is not None]
    failed = [item for item in cases if not item["recovered"]]
    output = {
        "status": "audited",
        "completed_positive_cases": len(cases),
        "failed_positive_cases": len(failed),
        "cases": cases,
        "policy": "diagnostic only; frozen labels, scanner vocabulary, and gates are unchanged",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"status=positive_audited completed={len(cases)} failed={len(failed)}")
    for item in failed:
        print(
            f"positive_failure case={item['case_id']} stage={item['stage']} "
            f"missing_metrics={','.join(item['missing_expected_metrics']) or 'none'} "
            f"stage_blockers={','.join(item['stage_blockers']) or 'none'}"
        )
        for metric in item["metric_support"]:
            if metric["diagnosis"] == "active_expected_bucket_support":
                continue
            print(
                f"metric_failure case={item['case_id']} metric={metric['metric']} "
                f"diagnosis={metric['diagnosis']} "
                f"active_other={','.join(metric['active_other_bucket_companies']) or 'none'} "
                f"counter={','.join(metric['counter_evidence_companies']) or 'none'}"
            )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
