from __future__ import annotations

import argparse
import json
from pathlib import Path

from .validation_evidence_audit_cli import audit_result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print the exact evidence supporting prevalence gains in one residual control result."
    )
    parser.add_argument(
        "--result",
        type=Path,
        default=Path("var/validation/semiconductor-2019q2-control.json"),
    )
    parser.add_argument("--max-evidence-per-metric", type=int, default=12)
    return parser


def _compact(text: object, limit: int = 360) -> str:
    value = " ".join(str(text or "").split())
    return value if len(value) <= limit else value[: limit - 3] + "..."


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    payload = json.loads(args.result.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("result JSON must be an object")
    report = audit_result(payload, limit=args.max_evidence_per_metric)
    clusters = report.get("clusters")
    if not isinstance(clusters, list):
        raise SystemExit("audit report missing clusters")

    printed = 0
    for cluster in clusters:
        if not isinstance(cluster, dict) or not cluster.get("triggered"):
            continue
        bucket = str(cluster.get("bucket") or "")
        metrics = cluster.get("metrics")
        if not isinstance(metrics, list):
            continue
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            name = str(metric.get("metric") or "")
            new_companies = set(str(item) for item in metric.get("new_supporting_companies", []))
            current_evidence = metric.get("current_evidence")
            if not isinstance(current_evidence, list):
                continue
            for row in current_evidence:
                if not isinstance(row, dict):
                    continue
                company = str(row.get("company_id") or "")
                if new_companies and company not in new_companies:
                    continue
                print(
                    f"evidence bucket={bucket!r} metric={name} ticker={row.get('ticker') or 'n/a'} "
                    f"company={company or 'n/a'} method={row.get('extraction_method') or 'n/a'} "
                    f"section={row.get('source_section') or 'n/a'} confidence={row.get('confidence')} "
                    f"matched={_compact(row.get('matched_phrase'), 90)!r} text={_compact(row.get('evidence_text'))!r}"
                )
                printed += 1
    print(f"status=control_evidence_reported rows={printed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
