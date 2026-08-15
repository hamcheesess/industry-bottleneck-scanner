from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

from .batch_cli import main as batch_main
from .company_metadata import load_company_period_metadata_csv


@dataclass(frozen=True)
class CaseRunSpec:
    case_id: str
    aggregation_level: str
    result_path: Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run every Phase-1 validation case whose metadata drafts have been fully verified. "
            "Cases with blank or invalid published_at timestamps are skipped, never guessed."
        )
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("experiments/phase1_validation_cases.csv"),
    )
    parser.add_argument(
        "--metadata-root",
        type=Path,
        default=Path("var/validation/metadata"),
    )
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--provider", default="alpha_vantage")
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("var/validation/artifacts"),
    )
    parser.add_argument(
        "--review-root",
        type=Path,
        default=Path("var/validation/review"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("var/validation/run-status.json"),
    )
    return parser


def _load_cases(path: Path) -> tuple[CaseRunSpec, ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"case_id", "aggregation_level", "result_path"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise SystemExit(f"{path}: missing required columns {sorted(missing)}")
        specs: list[CaseRunSpec] = []
        for row_number, row in enumerate(reader, start=2):
            case_id = (row.get("case_id") or "").strip()
            level = (row.get("aggregation_level") or "").strip()
            result_path = (row.get("result_path") or "").strip()
            if not case_id or not result_path:
                raise SystemExit(f"{path} row {row_number}: case_id and result_path are required")
            if level not in {"sector", "industry", "subindustry"}:
                raise SystemExit(f"{path} row {row_number}: invalid aggregation_level {level!r}")
            specs.append(CaseRunSpec(case_id=case_id, aggregation_level=level, result_path=Path(result_path)))
    return tuple(specs)


def _metadata_state(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "metadata_missing"
    try:
        records = load_company_period_metadata_csv(path.read_text(encoding="utf-8"))
    except (ValueError, KeyError, TypeError) as exc:
        message = str(exc)
        if "published_at" in message:
            return False, "needs_verified_timestamp"
        return False, f"invalid_metadata:{message}"
    if not records:
        return False, "metadata_empty"
    return True, "ready"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    specs = _load_cases(args.cases)
    results: list[dict[str, object]] = []
    ran = 0

    for spec in specs:
        current = args.metadata_root / f"{spec.case_id}-current.csv"
        baseline = args.metadata_root / f"{spec.case_id}-baseline.csv"
        current_ready, current_status = _metadata_state(current)
        baseline_ready, baseline_status = _metadata_state(baseline)
        item: dict[str, object] = {
            "case_id": spec.case_id,
            "aggregation_level": spec.aggregation_level,
            "current_metadata": str(current),
            "baseline_metadata": str(baseline),
            "result_path": str(spec.result_path),
            "current_status": current_status,
            "baseline_status": baseline_status,
        }
        if not (current_ready and baseline_ready):
            item["status"] = "awaiting_verified_metadata"
            results.append(item)
            continue

        artifact_root = args.artifact_root / spec.case_id
        review_queue = args.review_root / f"{spec.case_id}.json"
        code = batch_main(
            [
                "--current", str(current),
                "--baseline", str(baseline),
                "--provider", args.provider,
                "--transcript-root", str(args.transcript_root),
                "--review-queue", str(review_queue),
                "--aggregation-level", spec.aggregation_level,
                "--output", str(spec.result_path),
                "--artifact-root", str(artifact_root),
            ]
        )
        if code != 0:
            raise RuntimeError(f"batch runner failed for {spec.case_id} with exit code {code}")
        item["status"] = "completed"
        ran += 1
        results.append(item)

    awaiting = sum(item["status"] == "awaiting_verified_metadata" for item in results)
    payload = {
        "status": "complete" if awaiting == 0 else "partial",
        "case_count": len(results),
        "completed_cases": ran,
        "awaiting_verified_metadata_cases": awaiting,
        "cases": results,
        "timestamp_policy": "no case runs until both metadata files contain timezone-aware published_at values",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"status={payload['status']} cases={len(results)} completed={ran} "
        f"awaiting_verified_metadata={awaiting}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
