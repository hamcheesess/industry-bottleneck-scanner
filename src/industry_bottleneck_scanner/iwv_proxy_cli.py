from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

from .iwv_proxy import IWV_HOLDINGS_URL, PROXY_UNIVERSE_ID, candidates_to_csv, parse_iwv_holdings_csv


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download the public iShares IWV holdings file and build a validation-only "
            "broad-U.S. candidate universe. This is not canonical Russell 3000 membership."
        )
    )
    parser.add_argument("--url", default=IWV_HOLDINGS_URL)
    parser.add_argument("--output", type=Path, default=Path("var/cohort/iwv_proxy_candidates.csv"))
    parser.add_argument(
        "--provenance-output",
        type=Path,
        default=Path("var/cohort/iwv_proxy_provenance.json"),
    )
    return parser


def _download(url: str) -> str:
    request = Request(url, headers={"User-Agent": "industry-bottleneck-scanner/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed/explicit user URL
        raw = response.read()
    return raw.decode("utf-8-sig")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    text = _download(args.url)
    snapshot = parse_iwv_holdings_csv(text, source_url=args.url)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(candidates_to_csv(snapshot), encoding="utf-8")

    args.provenance_output.parent.mkdir(parents=True, exist_ok=True)
    args.provenance_output.write_text(
        json.dumps(
            {
                "universe_id": PROXY_UNIVERSE_ID,
                "purpose": "phase1_validation_only",
                "canonical_russell_3000": False,
                "as_of": snapshot.as_of.isoformat(),
                "source_url": snapshot.source_url,
                "candidate_count": len(snapshot.candidates),
                "classification_limit": (
                    "IWV holdings expose sector but not granular industry; candidate industry "
                    "is an explicit proxy-sector label used only for neutral sampling."
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"proxy={PROXY_UNIVERSE_ID} as_of={snapshot.as_of.isoformat()} "
        f"candidates={len(snapshot.candidates)} canonical_russell_3000=false"
    )
    print(f"wrote {args.output}")
    print(f"wrote {args.provenance_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
