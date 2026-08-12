from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from .cohort_sampling import load_cohort_candidates_csv, select_neutral_cohort


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select a deterministic industry-neutral Phase-1 cohort and emit paired transcript requests."
    )
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--target-size", type=int, default=10)
    parser.add_argument("--max-per-industry", type=int, default=2)
    parser.add_argument("--seed", default="phase1-neutral-v1")
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


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.target_size < 1:
        raise SystemExit("--target-size must be at least 1")
    if args.max_per_industry < 1:
        raise SystemExit("--max-per-industry must be at least 1")

    current_quarter = _validate_quarter(args.current_quarter, "--current-quarter")
    baseline_quarter = _validate_quarter(args.baseline_quarter, "--baseline-quarter")
    candidates = load_cohort_candidates_csv(args.candidates.read_text(encoding="utf-8"))
    selection = select_neutral_cohort(
        candidates,
        target_size=args.target_size,
        max_per_industry=args.max_per_industry,
        seed=args.seed,
    )

    args.selection_output.parent.mkdir(parents=True, exist_ok=True)
    args.selection_output.write_text(
        json.dumps(
            {
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
        f"requests={2 * selection.diagnostics.selected_companies}"
    )
    print(f"wrote {args.selection_output}")
    print(f"wrote {args.requests_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
