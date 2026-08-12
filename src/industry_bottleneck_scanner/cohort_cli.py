from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .cohort_sampling import load_cohort_candidates_csv, select_neutral_cohort


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Select a deterministic blind Phase-1 cohort with enough issuers inside each "
            "industry for the unchanged production trigger to be reachable."
        )
    )
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--as-of", required=True, help="Candidate-universe snapshot date in YYYY-MM-DD format")
    parser.add_argument("--source", required=True, help="Human-readable source/provenance for the candidate universe")
    parser.add_argument("--industry-count", type=int, default=3)
    parser.add_argument("--companies-per-industry", type=int, default=4)
    parser.add_argument("--seed", default="phase1-neutral-v2")
    parser.add_argument("--current-quarter", default="2026Q2")
    parser.add_argument("--baseline-quarter", default="2026Q1")
    parser.add_argument("--selection-output", type=Path, default=Path("var/cohort/neutral_selection.json"))
    parser.add_argument("--requests-output", type=Path, default=Path("var/cohort/neutral_requests.csv"))
    return parser


def _validate_quarter(value: str, name: str) -> str:
    quarter = value.strip().upper()
    if len(quarter) != 6 or quarter[4] != "Q" or quarter[5] not in "1234":
        raise SystemExit(f"{name} must use YYYYQ# format")
    return quarter


def _validate_as_of(value: str) -> str:
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError as exc:
        raise SystemExit("--as-of must use YYYY-MM-DD format") from exc


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.industry_count < 1:
        raise SystemExit("--industry-count must be at least 1")
    if args.companies_per_industry < 3:
        raise SystemExit("--companies-per-industry must be at least 3")
    if not args.source.strip():
        raise SystemExit("--source must not be blank")

    as_of = _validate_as_of(args.as_of)
    current_quarter = _validate_quarter(args.current_quarter, "--current-quarter")
    baseline_quarter = _validate_quarter(args.baseline_quarter, "--baseline-quarter")
    candidates = load_cohort_candidates_csv(args.candidates.read_text(encoding="utf-8"))
    selection = select_neutral_cohort(
        candidates,
        industry_count=args.industry_count,
        companies_per_industry=args.companies_per_industry,
        seed=args.seed,
    )

    args.selection_output.parent.mkdir(parents=True, exist_ok=True)
    args.selection_output.write_text(
        json.dumps(
            {
                "universe_provenance": {
                    "as_of": as_of,
                    "source": args.source.strip(),
                },
                "sampling_contract": {
                    "industry_count": args.industry_count,
                    "companies_per_industry": args.companies_per_industry,
                    "seed": args.seed,
                    "selection_uses_scanner_outcomes": False,
                },
                "diagnostics": asdict(selection.diagnostics),
                "companies": [asdict(item) for item in selection.companies],
                "current_quarter": current_quarter,
                "baseline_quarter": baseline_quarter,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    args.requests_output.parent.mkdir(parents=True, exist_ok=True)
    with args.requests_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("ticker", "quarter"))
        for company in selection.companies:
            writer.writerow((company.ticker, current_quarter))
            writer.writerow((company.ticker, baseline_quarter))

    print(
        f"selected={selection.diagnostics.selected_companies} "
        f"sectors={selection.diagnostics.sectors_selected} "
        f"industries={selection.diagnostics.industries_selected} "
        f"companies_per_industry={selection.diagnostics.companies_per_industry} "
        f"requests={2 * selection.diagnostics.selected_companies} "
        f"as_of={as_of}"
    )
    print(f"wrote {args.selection_output}")
    print(f"wrote {args.requests_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
