from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .operating_evidence_batch import build_bucket_operating_evidence


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamp must include a timezone offset")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build provider-free, strict-as-of OperatingSupport artifacts by bucket"
    )
    parser.add_argument("--disclosures-jsonl", type=Path, action="append", required=True)
    parser.add_argument("--expected-companies-csv", type=Path, action="append", required=True)
    parser.add_argument("--collection-diagnostics", type=Path, action="append", required=True)
    parser.add_argument("--as-of", type=_timestamp, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_bucket_operating_evidence(
        disclosure_paths=args.disclosures_jsonl,
        expected_company_paths=args.expected_companies_csv,
        diagnostic_paths=args.collection_diagnostics,
        as_of=args.as_of,
        output_dir=args.output_dir,
    )
    collection = manifest["collection"]
    print(
        f"status={manifest['collection_status']} buckets={manifest['bucket_count']} "
        f"issuers={manifest['expected_company_count']} "
        f"disclosures={collection['unique_disclosure_count']} "
        f"documents={manifest['document_count']} signals={manifest['signal_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
