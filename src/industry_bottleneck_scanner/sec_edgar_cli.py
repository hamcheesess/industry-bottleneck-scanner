from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from .disclosure_documents import PublicDisclosure
from .models import Classification
from .sec_edgar import SecEdgarClient, SecIssuer, collect_sec_disclosures


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from exc


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timestamp must use ISO-8601") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamp must include a timezone offset")
    return parsed


def _load_issuers(path: Path) -> tuple[SecIssuer, ...]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        if "cik" not in fields:
            raise ValueError("SEC companies CSV requires cik")
        if not ({"company_id", "issuer_id"} & fields):
            raise ValueError("SEC companies CSV requires company_id or issuer_id")
        issuers: list[SecIssuer] = []
        seen_company_ids: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            company_id = (row.get("company_id") or row.get("issuer_id") or "").strip()
            if company_id in seen_company_ids:
                raise ValueError(f"row {row_number}: duplicate company_id {company_id!r}")
            issuer = SecIssuer(
                company_id=company_id,
                cik=(row.get("cik") or "").strip(),
                ticker=(row.get("ticker") or "").strip() or None,
                classification=Classification(
                    sector=(row.get("sector") or "").strip() or None,
                    industry=(row.get("industry") or row.get("bucket") or "").strip() or None,
                    subindustry=(row.get("subindustry") or "").strip() or None,
                ),
            )
            seen_company_ids.add(issuer.company_id)
            issuers.append(issuer)
    if not issuers:
        raise ValueError("SEC companies CSV must contain at least one issuer")
    return tuple(issuers)


def _disclosure_payload(disclosure: PublicDisclosure) -> dict[str, object]:
    payload = asdict(disclosure)
    payload["published_at"] = disclosure.published_at.isoformat()
    payload["retrieved_at"] = disclosure.retrieved_at.isoformat()
    return payload


def _atomic_jsonl(path: Path, payloads: tuple[dict[str, object], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for payload in payloads:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect trigger-scoped 8-K, 10-Q, and 10-K disclosures from SEC EDGAR"
    )
    parser.add_argument("--companies-csv", type=Path, required=True)
    parser.add_argument("--since", type=_date, required=True)
    parser.add_argument("--as-of", type=_timestamp, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--diagnostics", type=Path, required=True)
    parser.add_argument(
        "--max-issuers",
        type=int,
        default=100,
        help="Explicit safety budget; the command fails rather than silently truncating.",
    )
    parser.add_argument("--request-interval-seconds", type=float, default=0.2)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.since > args.as_of.date():
        raise SystemExit("--since must not be later than --as-of")
    if args.max_issuers < 1:
        raise SystemExit("--max-issuers must be at least 1")
    issuers = _load_issuers(args.companies_csv)
    if len(issuers) > args.max_issuers:
        raise SystemExit(
            f"issuer count {len(issuers)} exceeds --max-issuers {args.max_issuers}; "
            "raise the explicit budget or pass a trigger-scoped company set"
        )
    user_agent = os.environ.get("SEC_USER_AGENT", "").strip()
    if not user_agent:
        raise SystemExit(
            "SEC_USER_AGENT is required (format: organization contact@example.com); "
            "SEC EDGAR does not require an API key"
        )
    client = SecEdgarClient(
        user_agent=user_agent,
        cache_dir=args.cache_dir,
        request_interval_seconds=args.request_interval_seconds,
    )
    collection = collect_sec_disclosures(
        client,
        issuers=issuers,
        since=args.since,
        as_of=args.as_of,
    )
    _atomic_jsonl(
        args.output_jsonl,
        tuple(_disclosure_payload(item) for item in collection.disclosures),
    )
    _atomic_json(
        args.diagnostics,
        {
            "schema_version": "sec-edgar-collection-v1",
            "provider": "sec_edgar",
            "since": args.since.isoformat(),
            "as_of": args.as_of.isoformat(),
            "companies_source": str(args.companies_csv),
            **asdict(collection.diagnostics),
        },
    )
    print(
        f"issuers={collection.diagnostics.issuer_count} "
        f"filings={collection.diagnostics.filing_count} "
        f"disclosures={collection.diagnostics.disclosure_count} "
        f"provider_requests={collection.diagnostics.provider_requests} "
        f"cache_hits={collection.diagnostics.cache_hits}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
