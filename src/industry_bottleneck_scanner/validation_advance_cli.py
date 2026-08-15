from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

from .validation_metadata_finalize_cli import main as finalize_main
from .validation_run_cli import main as run_main


@dataclass(frozen=True)
class VerifiedCase:
    case_id: str
    verified: Path


VERIFIED_CASES: tuple[VerifiedCase, ...] = (
    VerifiedCase(
        case_id="semiconductor-shortage-2021",
        verified=Path("experiments/verified_timestamps_semiconductor_2021.csv"),
    ),
    VerifiedCase(
        case_id="auto-chip-shortage-2021",
        verified=Path("experiments/verified_timestamps_auto_2021.csv"),
    ),
    VerifiedCase(
        case_id="semiconductor-2019q2-control",
        verified=Path("experiments/verified_timestamps_semiconductor_2019q2_control.csv"),
    ),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Apply committed source-backed event timestamps to any existing Phase-1 metadata "
            "drafts, then run every validation case that becomes ready."
        )
    )
    parser.add_argument("--metadata-root", type=Path, default=Path("var/validation/metadata"))
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument("--subset-root", type=Path, default=Path("var/validation/verified-subsets"))
    parser.add_argument("--cases", type=Path, default=Path("experiments/phase1_validation_cases.csv"))
    parser.add_argument("--run-output", type=Path, default=Path("var/validation/run-status.json"))
    parser.add_argument("--output", type=Path, default=Path("var/validation/advance-status.json"))
    return parser


def _keys(path: Path) -> tuple[tuple[str, str], ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"ticker", "quarter"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise SystemExit(f"{path}: missing required columns {sorted(missing)}")
        result: list[tuple[str, str]] = []
        for row in reader:
            result.append(
                (
                    (row.get("ticker") or "").strip().upper().replace(".", "-"),
                    (row.get("quarter") or "").strip().upper(),
                )
            )
    return tuple(result)


def _verified_rows(path: Path) -> tuple[list[str], dict[tuple[str, str], dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or ())
        required = {"ticker", "quarter", "published_at", "published_at_source_url"}
        missing = required - set(fieldnames)
        if missing:
            raise SystemExit(f"{path}: missing required columns {sorted(missing)}")
        result: dict[tuple[str, str], dict[str, str]] = {}
        for row_number, row in enumerate(reader, start=2):
            key = (
                (row.get("ticker") or "").strip().upper().replace(".", "-"),
                (row.get("quarter") or "").strip().upper(),
            )
            if key in result:
                raise SystemExit(f"{path} row {row_number}: duplicate ticker/quarter {key}")
            result[key] = row
    return fieldnames, result


def _write_subset(
    *,
    draft: Path,
    verified: Path,
    output: Path,
) -> None:
    keys = _keys(draft)
    fieldnames, available = _verified_rows(verified)
    missing = [key for key in keys if key not in available]
    if missing:
        raise SystemExit(f"{verified}: verified timestamps missing draft rows {missing}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for key in keys:
            writer.writerow(available[key])


def _finalize_case(spec: VerifiedCase, *, metadata_root: Path, subset_root: Path) -> str:
    current = metadata_root / f"{spec.case_id}-current.csv"
    baseline = metadata_root / f"{spec.case_id}-baseline.csv"
    if not current.exists() or not baseline.exists():
        return "draft_missing"
    if not spec.verified.exists():
        return "verified_source_missing"

    for period, draft in (("current", current), ("baseline", baseline)):
        subset = subset_root / f"{spec.case_id}-{period}.csv"
        _write_subset(draft=draft, verified=spec.verified, output=subset)
        code = finalize_main(
            [
                "--draft", str(draft),
                "--verified", str(subset),
                "--output", str(draft),
            ]
        )
        if code != 0:
            raise RuntimeError(f"metadata finalize failed for {spec.case_id} {period}")
    return "finalized"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    finalized: list[str] = []
    skipped: list[dict[str, str]] = []
    for spec in VERIFIED_CASES:
        status = _finalize_case(spec, metadata_root=args.metadata_root, subset_root=args.subset_root)
        if status == "finalized":
            finalized.append(spec.case_id)
        else:
            skipped.append({"case_id": spec.case_id, "status": status})

    run_code = run_main(
        [
            "--cases", str(args.cases),
            "--metadata-root", str(args.metadata_root),
            "--transcript-root", str(args.transcript_root),
            "--output", str(args.run_output),
        ]
    )
    if run_code != 0:
        raise RuntimeError(f"validation run failed with exit code {run_code}")

    run_payload = json.loads(args.run_output.read_text(encoding="utf-8"))
    payload = {
        "status": "advanced",
        "finalized_cases": finalized,
        "skipped_verified_cases": skipped,
        "run_status": run_payload,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"status=advanced finalized={len(finalized)} "
        f"completed={run_payload.get('completed_cases', 0)} "
        f"awaiting_verified_metadata={run_payload.get('awaiting_verified_metadata_cases', 0)}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
