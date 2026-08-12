from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from urllib.request import Request, urlopen

from .cohort_sampling import CohortCandidate, select_neutral_cohort
from .iwv_proxy import IWV_HOLDINGS_URL, PROXY_UNIVERSE_ID, parse_iwv_holdings_csv


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic Phase-1 blind validation cohort directly from the "
            "public IWV holdings proxy. The proxy is validation-only and not canonical "
            "Russell 3000 membership."
        )
    )
    parser.add_argument("--url", default=IWV_HOLDINGS_URL)
    parser.add_argument("--target-size", type=int, default=10)
    parser.add_argument("--max-per-sector", type=int, default=2)
    parser.add_argument("--seed", default="phase1-neutral-v1")
    parser.add_argument("--current-quarter", default="2026Q2")
    parser.add_argument("--baseline-quarter", default="2026Q1")
    parser.add_argument(
        "--selection-output",
        type=Path,
        default=Path("var/cohort/neutral_proxy_selection.json"),
    )
    parser.add_argument(
        "--requests-output",
        type=Path,
        default=Path("var/cohort/neutral_proxy_requests.csv"),
    )
    return parser


def _download(url: str) -> str:
    request = Request(url, headers={"User-Agent": "industry-bottleneck-scanner/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - explicit holdings URL
        return response.read().decode("utf-8-sig")


def _quarter(value: str, name: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 6 or normalized[4] != "Q" or normalized[5] not in "1234":
        raise SystemExit(f"{name} must use YYYYQ# format")
    return normalized


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.target_size < 1:
        raise SystemExit("--target-size must be at least 1")
    if args.max_per_sector < 1:
        raise SystemExit("--max-per-sector must be at least 1")
    current_quarter = _quarter(args.current_quarter, "--current-quarter")
    baseline_quarter = _quarter(args.baseline_quarter, "--baseline-quarter")

    snapshot = parse_iwv_holdings_csv(_download(args.url), source_url=args.url)
    candidates = tuple(
        CohortCandidate(
            company_id=item.company_id,
            ticker=item.ticker,
            sector=item.sector,
            industry=item.industry,
            exchange=item.exchange,
        )
        for item in snapshot.candidates
    )
    selection = select_neutral_cohort(
        candidates,
        target_size=args.target_size,
        max_per_industry=args.max_per_sector,
        seed=args.seed,
    )

    args.selection_output.parent.mkdir(parents=True, exist_ok=True)
    args.selection_output.write_text(
        json.dumps(
            {
                "universe_provenance": {
                    "universe_id": PROXY_UNIVERSE_ID,
                    "purpose": "phase1_validation_only",
                    "canonical_russell_3000": False,
                    "as_of": snapshot.as_of.isoformat(),
                    "source_url": snapshot.source_url,
                    "candidate_count": len(snapshot.candidates),
                    "classification_limit": "sector-only public holdings classification",
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
        for item in selection.companies:
            writer.writerow((item.ticker, current_quarter))
            writer.writerow((item.ticker, baseline_quarter))

    print(
        f"proxy={PROXY_UNIVERSE_ID} as_of={snapshot.as_of.isoformat()} "
        f"candidate_count={len(snapshot.candidates)} selected={selection.diagnostics.selected_companies} "
        f"sectors={selection.diagnostics.sectors_selected} requests={2 * len(selection.companies)} "
        "canonical_russell_3000=false"
    )
    print(f"wrote {args.selection_output}")
    print(f"wrote {args.requests_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
