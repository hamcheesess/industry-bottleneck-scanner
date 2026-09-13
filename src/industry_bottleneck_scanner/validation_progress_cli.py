from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .transcript_store import FileTranscriptStore
from .validation_collection_cli import _coverage_for_file
from .validation_metadata_cli import main as metadata_draft_main


@dataclass(frozen=True)
class ValidationCaseSpec:
    case_id: str
    requests: Path
    current_quarter: str
    baseline_quarter: str
    sector: str | None = None
    industry: str | None = None
    selection: Path | None = None


STATIC_CASES: tuple[ValidationCaseSpec, ...] = (
    ValidationCaseSpec(
        case_id="semiconductor-shortage-2021",
        requests=Path("experiments/validation_semiconductor_2021_requests.csv"),
        current_quarter="2021Q2",
        baseline_quarter="2021Q1",
        sector="Information Technology",
    ),
    ValidationCaseSpec(
        case_id="auto-chip-shortage-2021",
        requests=Path("experiments/validation_auto_2021_requests.csv"),
        current_quarter="2021Q2",
        baseline_quarter="2021Q1",
        sector="Consumer Discretionary",
    ),
    ValidationCaseSpec(
        case_id="semiconductor-2019q2-control",
        requests=Path("experiments/validation_semiconductor_2019q2_control_requests.csv"),
        current_quarter="2019Q2",
        baseline_quarter="2019Q1",
        sector="Information Technology",
    ),
    ValidationCaseSpec(
        case_id="semiconductor-2019q3-control",
        requests=Path("experiments/validation_semiconductor_2019q3_control_requests.csv"),
        current_quarter="2019Q3",
        baseline_quarter="2019Q2",
        sector="Information Technology",
    ),
    ValidationCaseSpec(
        case_id="auto-2019q2-control",
        requests=Path("experiments/validation_auto_2019q2_control_requests.csv"),
        current_quarter="2019Q2",
        baseline_quarter="2019Q1",
        sector="Consumer Discretionary",
    ),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Advance any fully cached Phase-1 validation case into timestamp-safe metadata "
            "drafting while other cases remain blocked by provider quota."
        )
    )
    parser.add_argument("--provider", default="alpha_vantage")
    parser.add_argument("--transcript-root", type=Path, default=Path("var/transcripts"))
    parser.add_argument(
        "--blind-requests",
        type=Path,
        default=Path("var/cohort/neutral_proxy_requests.csv"),
    )
    parser.add_argument(
        "--blind-selection",
        type=Path,
        default=Path("var/cohort/neutral_proxy_selection.json"),
    )
    parser.add_argument(
        "--metadata-root",
        type=Path,
        default=Path("var/validation/metadata"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("var/validation/progress.json"),
    )
    return parser


def _blind_case(requests: Path, selection: Path) -> ValidationCaseSpec | None:
    if not requests.exists() or not selection.exists():
        return None
    payload = json.loads(selection.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{selection}: selection JSON must be an object")
    current = str(payload.get("current_quarter") or "").strip().upper()
    baseline = str(payload.get("baseline_quarter") or "").strip().upper()
    if not current or not baseline:
        raise SystemExit(f"{selection}: current_quarter and baseline_quarter are required")
    return ValidationCaseSpec(
        case_id="blind-proxy-2026",
        requests=requests,
        current_quarter=current,
        baseline_quarter=baseline,
        selection=selection,
    )


def _draft_case(
    spec: ValidationCaseSpec,
    *,
    provider: str,
    transcript_root: Path,
    metadata_root: Path,
) -> dict[str, object]:
    current_output = metadata_root / f"{spec.case_id}-current.csv"
    baseline_output = metadata_root / f"{spec.case_id}-baseline.csv"
    checklist_output = metadata_root / f"{spec.case_id}-checklist.csv"
    argv = [
        "--requests", str(spec.requests),
        "--current-quarter", spec.current_quarter,
        "--baseline-quarter", spec.baseline_quarter,
        "--provider", provider,
        "--transcript-root", str(transcript_root),
        "--current-output", str(current_output),
        "--baseline-output", str(baseline_output),
        "--checklist-output", str(checklist_output),
    ]
    if spec.sector:
        argv.extend(("--sector", spec.sector))
    if spec.industry:
        argv.extend(("--industry", spec.industry))
    if spec.selection:
        argv.extend(("--selection", str(spec.selection)))
    code = metadata_draft_main(argv)
    if code != 0:
        raise RuntimeError(f"metadata drafting failed for {spec.case_id} with exit code {code}")
    return {
        "current_metadata": str(current_output),
        "baseline_metadata": str(baseline_output),
        "timestamp_checklist": str(checklist_output),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    specs = list(STATIC_CASES)
    blind = _blind_case(args.blind_requests, args.blind_selection)
    if blind is not None:
        specs.append(blind)

    store = FileTranscriptStore(args.transcript_root)
    results: list[dict[str, object]] = []
    drafted = 0
    for spec in specs:
        if not spec.requests.exists():
            results.append(
                {
                    "case_id": spec.case_id,
                    "requests": str(spec.requests),
                    "status": "request_file_missing",
                }
            )
            continue
        coverage = _coverage_for_file(
            spec.requests,
            store=store,
            provider=args.provider,
        )
        item: dict[str, object] = {
            "case_id": spec.case_id,
            "requests": str(spec.requests),
            "current_quarter": spec.current_quarter,
            "baseline_quarter": spec.baseline_quarter,
            "coverage": coverage,
        }
        if bool(coverage["complete"]):
            item["status"] = "metadata_drafted"
            item["metadata"] = _draft_case(
                spec,
                provider=args.provider,
                transcript_root=args.transcript_root,
                metadata_root=args.metadata_root,
            )
            drafted += 1
        else:
            item["status"] = "awaiting_transcripts"
        results.append(item)

    payload = {
        "provider": args.provider,
        "cases": results,
        "case_count": len(results),
        "metadata_drafted_cases": drafted,
        "awaiting_transcript_cases": sum(item.get("status") == "awaiting_transcripts" for item in results),
        "timestamp_policy": (
            "published_at remains blank until independently verified; transcript date hints are research-only"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"status=progressed cases={len(results)} metadata_drafted={drafted} "
        f"awaiting_transcripts={payload['awaiting_transcript_cases']}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
