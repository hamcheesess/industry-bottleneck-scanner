from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from .artifacts import (
    write_atomic_signals_jsonl,
    write_operating_support,
    write_source_document_manifest,
)
from .disclosure_documents import (
    DisclosureSection,
    PublicDisclosure,
    normalize_disclosures,
)
from .models import Classification
from .operating_support import build_operating_support
from .review_queue import FileReviewQueue
from .source_scan import scan_source_documents


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamp must include a timezone offset")
    return parsed


def _disclosure(payload: dict[str, object]) -> PublicDisclosure:
    sections_payload = payload.get("sections")
    if not isinstance(sections_payload, list):
        raise ValueError("public disclosure sections must be a list")
    classification_payload = payload.get("classification") or {}
    if not isinstance(classification_payload, dict):
        raise ValueError("public disclosure classification must be an object")
    return PublicDisclosure(
        provider=str(payload["provider"]),
        provider_document_id=str(payload["provider_document_id"]),
        company_id=str(payload["company_id"]),
        ticker=str(payload["ticker"]) if payload.get("ticker") is not None else None,
        document_type=str(payload["document_type"]),
        published_at=_timestamp(str(payload["published_at"])),
        retrieved_at=_timestamp(str(payload["retrieved_at"])),
        source_url=str(payload["source_url"]),
        classification=Classification(
            sector=classification_payload.get("sector"),
            industry=classification_payload.get("industry"),
            subindustry=classification_payload.get("subindustry"),
        ),
        sections=tuple(
            DisclosureSection(
                section_id=str(section["section_id"]),
                text=str(section["text"]),
                source_section=section.get("source_section"),
                speaker=section.get("speaker"),
                speaker_title=section.get("speaker_title"),
            )
            for section in sections_payload
            if isinstance(section, dict)
        ),
    )


def _load_disclosures(path: Path) -> tuple[PublicDisclosure, ...]:
    disclosures: list[PublicDisclosure] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("record must be an object")
            disclosures.append(_disclosure(payload))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid disclosure JSONL line {line_number}: {exc}") from exc
    if not disclosures:
        raise ValueError("disclosure JSONL must contain at least one record")
    return tuple(disclosures)


def _expected_company_ids(path: Path) -> tuple[str, ...]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if "company_id" not in set(reader.fieldnames or ()):
            raise ValueError("expected companies CSV requires company_id")
        company_ids = tuple(sorted({(row.get("company_id") or "").strip() for row in reader} - {""}))
    if not company_ids:
        raise ValueError("expected companies CSV must contain at least one company_id")
    return company_ids


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize and scan source-agnostic operating disclosures"
    )
    parser.add_argument("--disclosures-jsonl", type=Path, required=True)
    parser.add_argument("--expected-companies-csv", type=Path, required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--as-of", type=_timestamp, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--review-queue", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    disclosures = _load_disclosures(args.disclosures_jsonl)
    documents = normalize_disclosures(disclosures, as_of=args.as_of)
    review_queue = FileReviewQueue(args.review_queue) if args.review_queue else None
    scan = scan_source_documents(documents, review_queue=review_queue)
    support = build_operating_support(
        bucket=args.bucket,
        as_of=args.as_of,
        expected_company_ids=_expected_company_ids(args.expected_companies_csv),
        documents=documents,
        signals=scan.signals,
    )

    write_source_document_manifest(args.output_dir / "source_documents.json", documents)
    write_atomic_signals_jsonl(args.output_dir / "atomic_signals.jsonl", scan.signals)
    write_operating_support(args.output_dir / "operating_support.json", support)
    print(
        f"documents={scan.document_count} signals={len(scan.signals)} "
        f"reviews={len(scan.review_candidates)} excluded_analyst={scan.excluded_analyst_documents} "
        f"coverage={support.fresh_coverage_ratio:.4f} stage={support.stage}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
