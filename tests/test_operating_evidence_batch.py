from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import pytest

from industry_bottleneck_scanner.operating_evidence_batch import build_bucket_operating_evidence


AS_OF = datetime.fromisoformat("2026-08-21T23:59:59+00:00")


def _companies(path: Path, rows: list[tuple[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("company_id", "industry"))
        writer.writeheader()
        for company_id, industry in rows:
            writer.writerow({"company_id": company_id, "industry": industry})


def _disclosure(company_id: str, bucket: str, *, document_id: str | None = None, published_at: str = "2026-08-10T20:00:00+00:00") -> dict:
    return {
        "provider": "sec_edgar",
        "provider_document_id": document_id or f"accession-{company_id}",
        "company_id": company_id,
        "ticker": company_id.upper(),
        "document_type": "sec_8k_exhibit",
        "published_at": published_at,
        "retrieved_at": "2026-08-21T10:00:00+00:00",
        "source_url": f"https://www.sec.gov/Archives/{company_id}.htm",
        "classification": {"industry": bucket},
        "sections": [{"section_id": "release", "text": "Backlog reached a record level and capacity remains constrained."}],
    }


def _write_jsonl(path: Path, items: list[dict]) -> None:
    path.write_text("".join(json.dumps(item) + "\n" for item in items), encoding="utf-8")


def _diagnostics(path: Path, issuer_count: int, disclosure_count: int, *, failed_issuer_count: int = 0) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "sec-edgar-collection-v1",
                "status": "complete_with_gaps" if failed_issuer_count else "complete",
                "provider": "sec_edgar",
                "since": "2024-11-01",
                "as_of": AS_OF.isoformat(),
                "issuer_count": issuer_count,
                "filing_count": disclosure_count,
                "disclosure_count": disclosure_count,
                "failed_issuer_count": failed_issuer_count,
                "failed_document_count": 0,
                "provider_requests": 4,
                "cache_hits": 2,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_builds_dated_support_for_multiple_buckets_and_preserves_gaps(tmp_path: Path) -> None:
    companies_a = tmp_path / "companies-a.csv"
    companies_b = tmp_path / "companies-b.csv"
    _companies(companies_a, [("issuer-a", "Electrical Equipment"), ("issuer-b", "Electrical Equipment")])
    _companies(companies_b, [("issuer-c", "Semiconductors")])
    disclosures_a = tmp_path / "disclosures-a.jsonl"
    disclosures_b = tmp_path / "disclosures-b.jsonl"
    _write_jsonl(disclosures_a, [_disclosure("issuer-a", "Electrical Equipment")])
    _write_jsonl(disclosures_b, [_disclosure("issuer-c", "Semiconductors")])
    diagnostics_a = tmp_path / "diagnostics-a.json"
    diagnostics_b = tmp_path / "diagnostics-b.json"
    _diagnostics(diagnostics_a, 2, 1, failed_issuer_count=1)
    _diagnostics(diagnostics_b, 1, 1)

    output = tmp_path / "output"
    manifest = build_bucket_operating_evidence(
        disclosure_paths=[disclosures_a, disclosures_b],
        expected_company_paths=[companies_a, companies_b],
        diagnostic_paths=[diagnostics_a, diagnostics_b],
        as_of=AS_OF,
        output_dir=output,
    )

    assert manifest["strict_as_of"] is True
    assert manifest["provider_specific_code_used"] is False
    assert manifest["collection_status"] == "complete_with_gaps"
    assert manifest["collection_gaps_are_negative_evidence"] is False
    assert manifest["bucket_count"] == 2
    assert manifest["expected_company_count"] == 3
    rows = {row["bucket"]: row for row in manifest["buckets"]}
    assert rows["Electrical Equipment"]["fresh_coverage_ratio"] == 0.5
    assert rows["Electrical Equipment"]["stage"] == "observing"
    assert rows["Semiconductors"]["fresh_coverage_ratio"] == 1.0
    for row in rows.values():
        bucket_dir = output / row["path"]
        assert (bucket_dir / "source_documents.json").exists()
        assert (bucket_dir / "atomic_signals.jsonl").exists()
        assert (bucket_dir / "operating_support.json").exists()


def test_deduplicates_identical_disclosures_across_batches(tmp_path: Path) -> None:
    companies = tmp_path / "companies.csv"
    _companies(companies, [("issuer-a", "Electrical Equipment")])
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    item = _disclosure("issuer-a", "Electrical Equipment")
    _write_jsonl(first, [item])
    _write_jsonl(second, [item])
    diagnostics = tmp_path / "diagnostics.json"
    _diagnostics(diagnostics, 1, 2)

    manifest = build_bucket_operating_evidence(
        disclosure_paths=[first, second],
        expected_company_paths=[companies],
        diagnostic_paths=[diagnostics],
        as_of=AS_OF,
        output_dir=tmp_path / "output",
    )
    assert manifest["collection"]["disclosure_count_reported"] == 2
    assert manifest["collection"]["unique_disclosure_count"] == 1


def test_rejects_conflicting_duplicate_provenance(tmp_path: Path) -> None:
    companies = tmp_path / "companies.csv"
    _companies(companies, [("issuer-a", "Electrical Equipment")])
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    one = _disclosure("issuer-a", "Electrical Equipment", document_id="same")
    two = _disclosure("issuer-a", "Electrical Equipment", document_id="same")
    two["source_url"] = "https://www.sec.gov/Archives/conflict.htm"
    _write_jsonl(first, [one])
    _write_jsonl(second, [two])
    diagnostics = tmp_path / "diagnostics.json"
    _diagnostics(diagnostics, 1, 2)

    with pytest.raises(ValueError, match="conflicting duplicate"):
        build_bucket_operating_evidence(
            disclosure_paths=[first, second],
            expected_company_paths=[companies],
            diagnostic_paths=[diagnostics],
            as_of=AS_OF,
            output_dir=tmp_path / "output",
        )


def test_rejects_post_cutoff_disclosure(tmp_path: Path) -> None:
    companies = tmp_path / "companies.csv"
    _companies(companies, [("issuer-a", "Electrical Equipment")])
    disclosures = tmp_path / "disclosures.jsonl"
    _write_jsonl(disclosures, [_disclosure("issuer-a", "Electrical Equipment", published_at="2026-08-22T00:00:00+00:00")])
    diagnostics = tmp_path / "diagnostics.json"
    _diagnostics(diagnostics, 1, 1)

    with pytest.raises(ValueError, match="later than as_of"):
        build_bucket_operating_evidence(
            disclosure_paths=[disclosures],
            expected_company_paths=[companies],
            diagnostic_paths=[diagnostics],
            as_of=AS_OF,
            output_dir=tmp_path / "output",
        )
