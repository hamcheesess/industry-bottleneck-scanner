from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .artifacts import (
    write_atomic_signals_jsonl,
    write_operating_support,
    write_source_document_manifest,
)
from .disclosure_documents import PublicDisclosure, normalize_disclosures
from .operating_evidence_cli import _disclosure
from .operating_support import build_operating_support
from .source_scan import scan_source_documents


SCHEMA_VERSION = "operating-evidence-batch-v1"


@dataclass(frozen=True)
class ExpectedCompany:
    company_id: str
    bucket: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _slug(bucket: str) -> str:
    readable = re.sub(r"[^a-z0-9]+", "-", bucket.casefold()).strip("-") or "unclassified"
    suffix = hashlib.sha256(bucket.encode("utf-8")).hexdigest()[:8]
    return f"{readable[:64]}-{suffix}"


def load_expected_companies(paths: Iterable[Path]) -> tuple[ExpectedCompany, ...]:
    items: dict[str, ExpectedCompany] = {}
    for path in paths:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or ())
            if "company_id" not in fields or not ({"industry", "bucket"} & fields):
                raise ValueError(f"{path}: expected companies require company_id and industry/bucket")
            for row_number, row in enumerate(reader, start=2):
                company_id = (row.get("company_id") or "").strip()
                bucket = (row.get("industry") or row.get("bucket") or "").strip()
                if not company_id or not bucket:
                    raise ValueError(f"{path}:{row_number}: company_id and bucket are required")
                candidate = ExpectedCompany(company_id=company_id, bucket=bucket)
                previous = items.get(company_id)
                if previous is not None and previous != candidate:
                    raise ValueError(f"company {company_id!r} is assigned to conflicting buckets")
                items[company_id] = candidate
    if not items:
        raise ValueError("expected company inputs must contain at least one company")
    return tuple(sorted(items.values(), key=lambda item: (item.bucket, item.company_id)))


def _canonical_disclosure(disclosure: PublicDisclosure) -> str:
    payload = asdict(disclosure)
    payload["published_at"] = disclosure.published_at.isoformat()
    payload["retrieved_at"] = disclosure.retrieved_at.isoformat()
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def load_disclosures(paths: Iterable[Path]) -> tuple[PublicDisclosure, ...]:
    items: dict[tuple[str, str], tuple[str, PublicDisclosure]] = {}
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError("record must be an object")
                disclosure = _disclosure(payload)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"{path}:{line_number}: invalid disclosure: {exc}") from exc
            key = (disclosure.provider, disclosure.provider_document_id)
            canonical = _canonical_disclosure(disclosure)
            previous = items.get(key)
            if previous is not None and previous[0] != canonical:
                raise ValueError(f"conflicting duplicate disclosure {key!r}")
            items.setdefault(key, (canonical, disclosure))
    return tuple(item[1] for _, item in sorted(items.items()))


def load_collection_diagnostics(paths: Iterable[Path], *, as_of: datetime) -> tuple[dict, ...]:
    diagnostics: list[dict] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "sec-edgar-collection-v1":
            raise ValueError(f"{path}: unsupported collection diagnostics schema")
        if payload.get("status") not in {"complete", "complete_with_gaps"}:
            raise ValueError(f"{path}: collection did not complete")
        if payload.get("as_of") != as_of.isoformat():
            raise ValueError(f"{path}: diagnostics as_of does not match requested as_of")
        diagnostics.append(payload)
    return tuple(diagnostics)


def build_bucket_operating_evidence(
    *,
    disclosure_paths: Iterable[Path],
    expected_company_paths: Iterable[Path],
    diagnostic_paths: Iterable[Path],
    as_of: datetime,
    output_dir: Path,
) -> dict[str, object]:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    disclosures_in = tuple(disclosure_paths)
    companies_in = tuple(expected_company_paths)
    diagnostics_in = tuple(diagnostic_paths)
    if not disclosures_in or not companies_in or not diagnostics_in:
        raise ValueError("disclosures, expected companies, and diagnostics are all required")

    expected = load_expected_companies(companies_in)
    expected_by_company = {item.company_id: item.bucket for item in expected}
    buckets: dict[str, list[str]] = defaultdict(list)
    for item in expected:
        buckets[item.bucket].append(item.company_id)

    collection = load_collection_diagnostics(diagnostics_in, as_of=as_of)
    if sum(int(item["issuer_count"]) for item in collection) != len(expected_by_company):
        raise ValueError("collection issuer counts do not match the expected company set")

    disclosures = load_disclosures(disclosures_in)
    unknown = sorted({item.company_id for item in disclosures} - set(expected_by_company))
    if unknown:
        raise ValueError(f"disclosures contain unexpected companies: {unknown[:10]}")
    future = [item.provider_document_id for item in disclosures if item.published_at > as_of]
    if future:
        raise ValueError(f"disclosures later than as_of are forbidden: {future[:10]}")

    by_bucket: dict[str, list[PublicDisclosure]] = defaultdict(list)
    for disclosure in disclosures:
        bucket = expected_by_company[disclosure.company_id]
        classification_bucket = (
            disclosure.classification.industry
            or disclosure.classification.subindustry
            or disclosure.classification.sector
        )
        if classification_bucket != bucket:
            raise ValueError(
                f"disclosure {disclosure.provider_document_id!r} classification does not match "
                f"expected bucket {bucket!r}"
            )
        by_bucket[bucket].append(disclosure)

    failed_issuer_count = sum(int(item.get("failed_issuer_count", 0)) for item in collection)
    failed_document_count = sum(int(item.get("failed_document_count", 0)) for item in collection)
    rows: list[dict[str, object]] = []
    for bucket in sorted(buckets):
        documents = normalize_disclosures(by_bucket.get(bucket, ()), as_of=as_of)
        scan = scan_source_documents(documents)
        support = build_operating_support(
            bucket=bucket,
            as_of=as_of,
            expected_company_ids=buckets[bucket],
            documents=documents,
            signals=scan.signals,
        )
        bucket_dir = output_dir / "buckets" / _slug(bucket)
        write_source_document_manifest(bucket_dir / "source_documents.json", documents)
        write_atomic_signals_jsonl(bucket_dir / "atomic_signals.jsonl", scan.signals)
        write_operating_support(bucket_dir / "operating_support.json", support)
        rows.append(
            {
                "bucket": bucket,
                "path": str(bucket_dir.relative_to(output_dir)),
                "expected_company_count": len(buckets[bucket]),
                "document_company_count": len(support.document_company_ids),
                "fresh_company_count": len(support.fresh_company_ids),
                "document_count": len(documents),
                "signal_count": len(scan.signals),
                "review_count": len(scan.review_candidates),
                "stage": support.stage,
                "fresh_coverage_ratio": round(support.fresh_coverage_ratio, 6),
            }
        )

    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of.isoformat(),
        "provider_specific_code_used": False,
        "strict_as_of": True,
        "collection_status": "complete_with_gaps" if failed_issuer_count or failed_document_count else "complete",
        "collection_gaps_are_negative_evidence": False,
        "input": {
            "disclosures": [{"path": str(path), "sha256": _sha256(path)} for path in disclosures_in],
            "expected_companies": [{"path": str(path), "sha256": _sha256(path)} for path in companies_in],
            "collection_diagnostics": [{"path": str(path), "sha256": _sha256(path)} for path in diagnostics_in],
        },
        "collection": {
            "batch_count": len(collection),
            "issuer_count": sum(int(item["issuer_count"]) for item in collection),
            "filing_count": sum(int(item["filing_count"]) for item in collection),
            "disclosure_count_reported": sum(int(item["disclosure_count"]) for item in collection),
            "unique_disclosure_count": len(disclosures),
            "failed_issuer_count": failed_issuer_count,
            "failed_document_count": failed_document_count,
            "provider_requests": sum(int(item["provider_requests"]) for item in collection),
            "cache_hits": sum(int(item["cache_hits"]) for item in collection),
        },
        "bucket_count": len(rows),
        "expected_company_count": len(expected_by_company),
        "document_count": sum(int(item["document_count"]) for item in rows),
        "signal_count": sum(int(item["signal_count"]) for item in rows),
        "review_count": sum(int(item["review_count"]) for item in rows),
        "buckets": rows,
    }
    _atomic_json(output_dir / "operating_evidence_manifest.json", manifest)
    return manifest
