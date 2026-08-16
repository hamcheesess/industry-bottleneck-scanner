from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

from .batch_cli import main as batch_main
from .company_metadata import load_company_period_metadata_csv
from .pipeline_fingerprint import missing_experiment_transcripts


@dataclass(frozen=True)
class CaseRunSpec:
    case_id: str
    aggregation_level: str
    result_path: Path
    current_metadata_path: Path | None = None
    baseline_metadata_path: Path | None = None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run every Phase-1 validation case whose verified metadata and frozen transcript coverage are complete. "
            "Missing timestamps or transcript cache entries are skipped, never guessed or silently dropped."
        )
    )
    parser.add_argument("--cases", type=Path, default=Path("experiments/phase1_validation_cases.csv"))
    parser.add_argument("--metadata-root", type=Path, default=Path("var/validation/metadata"))
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--provider", default="alpha_vantage")
    parser.add_argument("--max-companies", type=int, default=50)
    parser.add_argument("--artifact-root", type=Path, default=Path("var/validation/artifacts"))
    parser.add_argument("--review-root", type=Path, default=Path("var/validation/review"))
    parser.add_argument("--output", type=Path, default=Path("var/validation/run-status.json"))
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
            current_metadata = (row.get("current_metadata_path") or "").strip()
            baseline_metadata = (row.get("baseline_metadata_path") or "").strip()
            if not case_id or not result_path:
                raise SystemExit(f"{path} row {row_number}: case_id and result_path are required")
            if level not in {"sector", "industry", "subindustry"}:
                raise SystemExit(f"{path} row {row_number}: invalid aggregation_level {level!r}")
            if bool(current_metadata) != bool(baseline_metadata):
                raise SystemExit(
                    f"{path} row {row_number}: current_metadata_path and baseline_metadata_path must be supplied together"
                )
            specs.append(
                CaseRunSpec(
                    case_id=case_id,
                    aggregation_level=level,
                    result_path=Path(result_path),
                    current_metadata_path=Path(current_metadata) if current_metadata else None,
                    baseline_metadata_path=Path(baseline_metadata) if baseline_metadata else None,
                )
            )
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


def _metadata_paths(spec: CaseRunSpec, metadata_root: Path) -> tuple[Path, Path]:
    current = spec.current_metadata_path or metadata_root / f"{spec.case_id}-current.csv"
    baseline = spec.baseline_metadata_path or metadata_root / f"{spec.case_id}-baseline.csv"
    return current, baseline


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.max_companies < 1:
        raise SystemExit("--max-companies must be at least 1")

    specs = _load_cases(args.cases)
    results: list[dict[str, object]] = []
    ran = 0

    for spec in specs:
        current, baseline = _metadata_paths(spec, args.metadata_root)
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

        missing_transcripts = missing_experiment_transcripts(
            current_metadata=current,
            baseline_metadata=baseline,
            provider=args.provider,
            transcript_root=args.transcript_root,
        )
        if missing_transcripts:
            item["status"] = "awaiting_transcripts"
            item["missing_transcripts"] = list(missing_transcripts)
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
                "--max-companies", str(args.max_companies),
                "--output", str(spec.result_path),
                "--artifact-root", str(artifact_root),
            ]
        )
        if code != 0:
            raise RuntimeError(f"batch runner failed for {spec.case_id} with exit code {code}")
        item["status"] = "completed"
        ran += 1
        results.append(item)

    awaiting_metadata = sum(item["status"] == "awaiting_verified_metadata" for item in results)
    awaiting_transcripts = sum(item["status"] == "awaiting_transcripts" for item in results)
    payload = {
        "status": "complete" if awaiting_metadata == 0 and awaiting_transcripts == 0 else "partial",
        "case_count": len(results),
        "completed_cases": ran,
        "awaiting_verified_metadata_cases": awaiting_metadata,
        "awaiting_transcript_cases": awaiting_transcripts,
        "max_companies": args.max_companies,
        "cases": results,
        "timestamp_policy": "no case runs until both metadata files contain timezone-aware published_at values",
        "coverage_policy": "no frozen validation case runs until every metadata ticker-quarter is cached in both windows",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"status={payload['status']} cases={len(results)} completed={ran} "
        f"awaiting_verified_metadata={awaiting_metadata} awaiting_transcripts={awaiting_transcripts}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
