from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit evidence behind prevalence-gaining metrics in completed Phase-1 validation results. "
            "This is diagnostic only and never changes scanner vocabulary or trigger thresholds."
        )
    )
    parser.add_argument("--cases", type=Path, default=Path("experiments/phase1_validation_cases.csv"))
    parser.add_argument("--output", type=Path, default=Path("var/validation/evidence-audit.json"))
    parser.add_argument("--max-evidence-per-metric", type=int, default=12)
    return parser


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


def _support_rows(
    signals: list[dict[str, object]],
    *,
    level: str,
    bucket: str,
    metric: str,
    limit: int,
) -> list[dict[str, object]]:
    selected = [
        item
        for item in signals
        if _active(item)
        and str(item.get("metric") or "") == metric
        and _bucket(item, level) == bucket
    ]
    selected.sort(
        key=lambda item: (
            str(item.get("company_id") or ""),
            str(item.get("published_at") or ""),
            str(item.get("document_id") or ""),
        )
    )
    result: list[dict[str, object]] = []
    for item in selected[:limit]:
        result.append(
            {
                "company_id": item.get("company_id"),
                "ticker": item.get("ticker"),
                "scanner": item.get("scanner"),
                "metric": item.get("metric"),
                "evidence_text": item.get("evidence_text"),
                "extraction_method": item.get("extraction_method"),
                "matched_phrase": item.get("matched_phrase"),
                "confidence": item.get("confidence"),
                "source_section": item.get("source_section"),
                "speaker": item.get("speaker"),
                "speaker_title": item.get("speaker_title"),
                "document_id": item.get("document_id"),
                "published_at": item.get("published_at"),
                "source_url": item.get("source_url"),
            }
        )
    return result


def _company_set(rows: list[dict[str, object]]) -> list[str]:
    return sorted({str(item.get("company_id") or "") for item in rows if item.get("company_id")})


def audit_result(payload: dict[str, object], *, limit: int) -> dict[str, object]:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        return {"status": "artifacts_missing", "clusters": []}
    current_path = Path(str(artifacts.get("current_signals_jsonl") or ""))
    baseline_path = Path(str(artifacts.get("baseline_signals_jsonl") or ""))
    current_signals = _read_jsonl(current_path)
    baseline_signals = _read_jsonl(baseline_path)
    level = str(payload.get("aggregation_level") or "industry")
    acceleration = payload.get("acceleration")
    if not isinstance(acceleration, list):
        return {"status": "acceleration_missing", "clusters": []}

    clusters: list[dict[str, object]] = []
    for raw in acceleration:
        if not isinstance(raw, dict):
            continue
        if not (bool(raw.get("triggered")) or bool(raw.get("watchlisted"))):
            continue
        bucket = str(raw.get("bucket") or "")
        gains = [str(item) for item in raw.get("metric_prevalence_gains", [])]
        metric_rows: list[dict[str, object]] = []
        for metric in gains:
            current_support = _support_rows(
                current_signals,
                level=level,
                bucket=bucket,
                metric=metric,
                limit=limit,
            )
            baseline_support = _support_rows(
                baseline_signals,
                level=level,
                bucket=bucket,
                metric=metric,
                limit=limit,
            )
            metric_rows.append(
                {
                    "metric": metric,
                    "current_companies": _company_set(current_support),
                    "baseline_companies": _company_set(baseline_support),
                    "new_supporting_companies": sorted(
                        set(_company_set(current_support)) - set(_company_set(baseline_support))
                    ),
                    "current_evidence": current_support,
                    "baseline_evidence": baseline_support,
                }
            )
        clusters.append(
            {
                "bucket": bucket,
                "triggered": bool(raw.get("triggered")),
                "confirmed": bool(raw.get("confirmed")),
                "watchlisted": bool(raw.get("watchlisted")),
                "metric_prevalence_gains": gains,
                "metrics": metric_rows,
            }
        )
    return {
        "status": "audited",
        "current_signals_path": str(current_path),
        "baseline_signals_path": str(baseline_path),
        "clusters": clusters,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.max_evidence_per_metric < 1:
        raise SystemExit("--max-evidence-per-metric must be at least 1")

    with args.cases.open("r", encoding="utf-8", newline="") as handle:
        cases = list(csv.DictReader(handle))

    reports: list[dict[str, object]] = []
    audited = 0
    for case in cases:
        result_path = Path((case.get("result_path") or "").strip())
        if not result_path.exists():
            continue
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        report = audit_result(payload, limit=args.max_evidence_per_metric)
        item = {
            "case_id": (case.get("case_id") or "").strip(),
            "role": (case.get("role") or "").strip(),
            "result_path": str(result_path),
            "audit": report,
        }
        reports.append(item)
        if report.get("status") == "audited":
            audited += 1

    output = {
        "status": "audited",
        "audited_cases": audited,
        "cases": reports,
        "policy": "evidence audit only; no vocabulary or trigger mutation",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"status=evidence_audited cases={audited}")
    for case in reports:
        if case["role"] != "control":
            continue
        audit = case["audit"]
        if not isinstance(audit, dict):
            continue
        for cluster in audit.get("clusters", []):
            if not isinstance(cluster, dict) or not cluster.get("triggered"):
                continue
            for metric in cluster.get("metrics", []):
                if not isinstance(metric, dict):
                    continue
                evidence = metric.get("current_evidence")
                methods: set[str] = set()
                if isinstance(evidence, list):
                    for row in evidence:
                        if isinstance(row, dict) and row.get("extraction_method"):
                            methods.add(str(row["extraction_method"]))
                print(
                    f"control_evidence case={case['case_id']} bucket={cluster['bucket']!r} "
                    f"metric={metric['metric']} new_companies={','.join(metric['new_supporting_companies']) or 'none'} "
                    f"methods={','.join(sorted(methods)) or 'none'}"
                )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
